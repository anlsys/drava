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
    if (data == NULL || data_len == 0)
        return DRAVA_EINVAL;

    static std::mutex out_mu;
    static FILE *out = NULL;

    std::lock_guard<std::mutex> lock(out_mu);
    if (out == NULL) {
        const char *fifo_path = drava->egress_cfg.output_fifo_path.c_str();
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
                                device_unique_id_t device_unique_id,
                                thread_t *thread)
{
    drava_device_t *drava_device = drava->devices + device_unique_id;
    team_t *team = &drava_device->team;

    /* the thread 0 reads from the socket and spawns task */
    if (thread->tid == 0) {
        const char *sock_path = drava->ingress_cfg.socket_path.c_str();
        /* setup unix socket */
        if (!std::filesystem::exists(sock_path))
            LOGGER_FATAL("Socket %s does not exists", sock_path);

        int sockfd = socket(AF_UNIX, SOCK_STREAM, 0);
        if (sockfd < 0)
            LOGGER_FATAL("Could not open socket %s: %s", sock_path,
                         strerror(errno));

        sockaddr_un addr{};
        addr.sun_family = AF_UNIX;
        std::strncpy(addr.sun_path, sock_path, sizeof(addr.sun_path) - 1);

        if (connect(sockfd, reinterpret_cast<sockaddr *>(&addr),
                    sizeof(addr)) == -1)
            LOGGER_FATAL("Could not connect socket %s: %s", sock_path,
                         strerror(errno));

        LOGGER_INFO("Connected to socket %s, reading framed binary payloads...",
                    sock_path);

        int flush_timeout_ms = drava->ingress_cfg.fetch_timeout_ms;
        int callback_flush_timeout_ms = drava->callback_flush_timeout_ms;
        LOGGER_INFO(
                "Socket fetch config: read_timeout_ms=%d callback_batch=%zu callback_flush_timeout_ms=%d",
                flush_timeout_ms, drava->callback_batch_size,
                callback_flush_timeout_ms);

        std::vector<std::string> pending;
        pending.reserve(drava->callback_batch_size);

        auto flush_pending = [&]() {
            if (pending.empty())
                return;
            std::vector<std::string> batch_payloads = std::move(pending);
            pending.clear();
            pending.reserve(drava->callback_batch_size);
            if (drava->callback_serialize) {
                drava_callback_task_begin(drava);
                drava_dispatch_payload_batch(drava, device_unique_id,
                                             batch_payloads);
                return;
            }
            drava_callback_task_begin(drava);

            constexpr task_flags_t flags = TASK_FLAG_ZERO;
            drava->runtime.team_task_spawn<flags>(
                    team,
                    XKRT_UNSPECIFIED_DEVICE_UNIQUE_ID, 0, nullptr, nullptr,
                    [drava, device_unique_id,
                     batch_payloads = std::move(batch_payloads)](runtime_t * runtime, device_t * device, task_t *task) {
                        (void)runtime;(void)device;(void)task;
                        drava_dispatch_payload_batch(drava, device_unique_id,
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
                    if (callback_flush_timeout_ms <= 0)
                        continue;
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

            const bool is_eos =
                    drava_payload_is_eos(payload.data(), payload.size());
            pending.push_back(std::move(payload));

            if (!is_eos && pending.size() < drava->callback_batch_size)
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
