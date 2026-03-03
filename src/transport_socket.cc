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
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <mutex>
#include <string>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <vector>

const char *sock_path =
        drava_env_get_str_default("DRAVA_SOCKET_PATH", "/tmp/accel_2048.sock");

const char *fifo_path = drava_env_get_str_default("DRAVA_OUTPUT_FIFO_PATH",
                                                  "/tmp/drava_stage2_in");

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

int drava_transport_socket_publish(drava_t *drava,
                                   const void *data,
                                   size_t data_len)
{
    (void)drava;
    if (data == NULL || data_len == 0)
        return DRAVA_EINVAL;

    static std::mutex out_mu;
    static FILE *out = NULL;

    std::lock_guard<std::mutex> lock(out_mu);
    if (out == NULL) {
        if (!std::filesystem::exists(fifo_path)) {
            LOGGER_ERROR("Output FIFO does not exist: %s", fifo_path);
            return DRAVA_ERROR;
        }
        out = std::fopen(fifo_path, "wb");
        if (out == NULL) {
            LOGGER_ERROR("Failed to open output FIFO %s: %s", fifo_path,
                         std::strerror(errno));
            return DRAVA_ERROR;
        }
        LOGGER_INFO("Socket publish output ready: fifo=%s", fifo_path);
    }

    const uint32_t be_len = htonl((uint32_t)data_len);
    if (std::fwrite(&be_len, sizeof(be_len), 1, out) != 1)
        return DRAVA_ERROR;
    if (std::fwrite(data, data_len, 1, out) != 1)
        return DRAVA_ERROR;
    if (std::fflush(out) != 0)
        return DRAVA_ERROR;

    return DRAVA_SUCCESS;
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

        int flush_timeout_ms =
                drava_env_get_int_default("DRAVA_FETCH_TIMEOUT_MS", 1000);
        LOGGER_INFO(
                "Socket fetch config: flush_timeout_ms=%d callback_batch=%zu",
                flush_timeout_ms, drava->callback_batch_size);

        std::vector<std::string> pending;
        pending.reserve(drava->callback_batch_size);

        auto flush_pending = [&]() {
            if (pending.empty())
                return;
            std::vector<std::string> batch_payloads = std::move(pending);
            pending.clear();
            pending.reserve(drava->callback_batch_size);

            drava->runtime.team_task_spawn(
                    team,
                    [drava, device_global_id,
                     batch_payloads = std::move(batch_payloads)](task_t *task) {
                        (void)task;
                        drava_dispatch_payload_batch(drava, device_global_id,
                                                     batch_payloads);
                    });
        };

        /* each frame is: [4-byte big-endian length][payload bytes] */
        while (true) {
            if (!pending.empty()) {
                fd_set rfds;
                FD_ZERO(&rfds);
                FD_SET(sockfd, &rfds);
                struct timeval tv;
                tv.tv_sec = flush_timeout_ms / 1000;
                tv.tv_usec = (flush_timeout_ms % 1000) * 1000;
                int sel = select(sockfd + 1, &rfds, nullptr, nullptr, &tv);
                if (sel == 0) {
                    flush_pending();
                    continue;
                }
                if (sel < 0) {
                    if (errno == EINTR)
                        continue;
                    break;
                }
            }

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

            flush_pending();
        }

        flush_pending();
        close(sockfd);
    }

    /* other threads worksteal */
    drava->runtime.team_barrier<true>(team, thread);

    return DRAVA_SUCCESS;
}
