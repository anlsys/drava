/*******************************************************************************
* Copyright 2025 UChicago Argonne, LLC.
* (c.f. AUTHORS, LICENSE)
*
* This file is part of the drava project.
* For more info, see https://github.com/anlsys/drava
*
* SPDX-License-Identifier: BSD-3-Clause
*****************************************************************************/

#include <drava/drava.h>

#include <arpa/inet.h>
#include <filesystem>
#include <string>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <vector>

/* TODO: env variable or something, socket path */
static char const *SOCK_PATH = "/tmp/accel_2048.sock";

static bool read_exact(int fd, void *buf, size_t len)
{
   char *p = static_cast<char *>(buf);
   size_t done = 0;
   while (done < len) {
       ssize_t n = read(fd, p + done, len - done);
       if (n <= 0)
           return false;
       done += (size_t)n;
   }
   return true;
}

int drava_transport_socket_main(drava_t *drava,
                               device_global_id_t device_global_id,
                               thread_t *thread)
{
   drava_device_t *drava_device = drava->devices + device_global_id;
   team_t *team = &drava_device->team;

   /* the thread 0 reads from the socket and spawns task */
   if (thread->tid == 0) {
       /* setup unix socket */
       if (!std::filesystem::exists(SOCK_PATH))
           LOGGER_FATAL("Socket %s does not exists", SOCK_PATH);

       int sockfd = socket(AF_UNIX, SOCK_STREAM, 0);
       if (sockfd < 0)
           LOGGER_FATAL("Could not open socket %s: %s", SOCK_PATH,
                        strerror(errno));

       sockaddr_un addr{};
       addr.sun_family = AF_UNIX;
       std::strncpy(addr.sun_path, SOCK_PATH, sizeof(addr.sun_path) - 1);

       if (connect(sockfd, reinterpret_cast<sockaddr *>(&addr),
                   sizeof(addr)) == -1)
           LOGGER_FATAL("Could not connect socket %s: %s", SOCK_PATH,
                        strerror(errno));

       LOGGER_INFO("Connected to socket %s, reading framed binary payloads...",
                   SOCK_PATH);

       std::vector<std::string> pending;
       pending.reserve(drava->callback_batch_size);

       /* each frame is: [4-byte big-endian length][payload bytes] */
       while (true) {
           uint32_t be_len = 0;
           if (!read_exact(sockfd, &be_len, sizeof(be_len)))
               break;

           const uint32_t payload_len = ntohl(be_len);
           if (payload_len == 0)
               continue;

           std::string payload((size_t)payload_len, '\0');
           if (!read_exact(sockfd, payload.data(), payload.size()))
               break;

           pending.push_back(std::move(payload));

           if (pending.size() < drava->callback_batch_size)
               continue;

           std::vector<std::string> batch_payloads = std::move(pending);
           pending.clear();
           pending.reserve(drava->callback_batch_size);

           drava->runtime.team_task_spawn(team,
                                          [drava, device_global_id,
                                           batch_payloads = std::move(batch_payloads)](task_t *task) {
                                              (void)task;
                                              drava_dispatch_payload_batch(
                                                      drava, device_global_id,
                                                      batch_payloads);
                                          });
       }

       if (!pending.empty()) {
           std::vector<std::string> batch_payloads = std::move(pending);
           drava->runtime.team_task_spawn(team,
                                          [drava, device_global_id,
                                           batch_payloads = std::move(batch_payloads)](task_t *task) {
                                              (void)task;
                                              drava_dispatch_payload_batch(
                                                      drava, device_global_id,
                                                      batch_payloads);
                                          });
       }
       close(sockfd);
   }

   /* other threads worksteal */
   drava->runtime.team_barrier<true>(team, thread);

   return DRAVA_SUCCESS;
}
