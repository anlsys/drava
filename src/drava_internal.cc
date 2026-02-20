/*******************************************************************************
 * Copyright 2025 UChicago Argonne, LLC.
 * (c.f. AUTHORS, LICENSE)
 *
 * This file is part of the drava project.
 * For more info, see https://github.com/anlsys/drava
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *****************************************************************************/

#include <cerrno>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <drava/drava.h>
#include <limits>
#include <vector>

static const char *env_get(const char *k)
{
    const char *v = getenv(k);
    return (v && v[0] != '\0') ? v : nullptr;
}

int drava_parse_transport_from_env(drava_transport_t *out)
{
    if (!out)
        return DRAVA_EINVAL;

    const char *t = drava_env_get_str_default("DRAVA_TRANSPORT", "auto");
    if (strcmp(t, "auto") == 0) {
        *out = DRAVA_TRANSPORT_SOCKET;
        return DRAVA_SUCCESS;
    }

    if (strcmp(t, "socket") == 0) {
        *out = DRAVA_TRANSPORT_SOCKET;
        return DRAVA_SUCCESS;
    }

    if (strcmp(t, "nats") == 0) {
#ifdef DRAVA_HAS_NATS
        *out = DRAVA_TRANSPORT_NATS;
        return DRAVA_SUCCESS;
#else
        return DRAVA_ENOTSUP;
#endif
    }

    return DRAVA_EINVAL;
}

int drava_env_get_int_default(const char *key, int default_value)
{
    const char *s = env_get(key);
    if (!s)
        return default_value;
    errno = 0;
    char *end = nullptr;
    long v = std::strtol(s, &end, 10);
    if (errno != 0 || end == s || *end != '\0')
        return default_value;
    return (int)v;
}

const char *drava_env_get_str_default(const char *key,
                                      const char *default_value)
{
    const char *s = env_get(key);
    return s ? s : default_value;
}

static uint64_t ns_since_epoch()
{
    auto now = std::chrono::system_clock::now().time_since_epoch();
    return (uint64_t)std::chrono::duration_cast<std::chrono::nanoseconds>(now)
            .count();
}

static void drava_dispatch_execute(drava_t *drava,
                                   device_global_id_t device_global_id,
                                   const std::vector<std::string> &payloads)
{
    (void)device_global_id;
    if (!drava || payloads.empty())
        return;

    if (!drava->frame_routine) {
        LOGGER_WARN("No frame callback is registered; dropping batch");
        return;
    }

    if (payloads.size() > std::numeric_limits<uint32_t>::max()) {
        LOGGER_FATAL("Batch too large for C API callback");
        return;
    }

    std::vector<drava_frame_t> frames(payloads.size());
    uint64_t batch_id = drava->next_batch_id.fetch_add(1);

    for (size_t i = 0; i < payloads.size(); ++i) {
        const std::string &payload = payloads[i];
        drava_frame_t &frame = frames[i];
        frame.frame_id = drava->next_frame_id.fetch_add(1);
        frame.recv_ts_ns = ns_since_epoch();
        frame.data = payload.data();
        frame.data_len = payload.size();
    }

    drava_frame_batch_t batch;
    batch.batch_id = batch_id;
    batch.count = (uint32_t)frames.size();
    batch.frames = frames.data();
    drava->frame_routine(&batch, drava->frame_routine_user_data);
}

void drava_dispatch_payload_batch(drava_t *drava,
                                  device_global_id_t device_global_id,
                                  const std::vector<std::string> &payloads)
{
    drava_dispatch_execute(drava, device_global_id, payloads);
}
