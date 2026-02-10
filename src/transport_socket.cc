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

#include <filesystem>
#include <streambuf>
#include <string>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

/* TODO: env variable or something, socket path */
static char const *SOCK_PATH = "/tmp/accel_2048.sock";

/* custom socketbuf to readline on the socket */
class socketbuf : public std::streambuf
{
    static constexpr size_t buf_size = 1024;

  private:
    char buffer[buf_size];
    int sockfd;

  protected:
    /* refill buffer when empty */
    int underflow(void) override
    {
        ssize_t n = read(sockfd, buffer, buf_size);
        if (n <= 0)
            return traits_type::eof();
        setg(buffer, buffer, buffer + n);
        return traits_type::to_int_type(*gptr());
    }

  public:
    explicit socketbuf(int fd)
            : sockfd(fd)
    {
        setg(buffer, buffer, buffer);
    }
};

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

        LOGGER_INFO("Connected to socket %s, reading lines...", SOCK_PATH);

        socketbuf sb(sockfd);
        std::istream sockstream(&sb);
        std::string line;

        /* read lines from the socket */
        while (std::getline(sockstream, line)) {
            //            LOGGER_DEBUG("Got: %s", line.c_str());

            /* spawn a task for each line */
            drava->runtime.team_task_spawn(team, [=](task_t *task) {
                drava_parse_line(drava, device_global_id, line);
            });
        }
        close(sockfd);
    }

    /* other threads worksteal */
    drava->runtime.team_barrier<true>(team, thread);

    return DRAVA_SUCCESS;
}
