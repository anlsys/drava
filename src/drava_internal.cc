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
#include <fstream>
#include <inttypes.h>
#include <limits>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

static const char *env_get(const char *k)
{
    const char *v = getenv(k);
    return (v && v[0] != '\0') ? v : nullptr;
}

static thread_local uint64_t g_callback_recv_ts_ns = 0;

static std::string trim_copy(const std::string &s)
{
    size_t b = 0;
    while (b < s.size() && (s[b] == ' ' || s[b] == '\t'))
        ++b;
    size_t e = s.size();
    while (e > b && (s[e - 1] == ' ' || s[e - 1] == '\t'))
        --e;
    return s.substr(b, e - b);
}

static std::string strip_quotes(const std::string &s)
{
    if (s.size() >= 2 && ((s.front() == '"' && s.back() == '"') ||
                          (s.front() == '\'' && s.back() == '\'')))
        return s.substr(1, s.size() - 2);
    return s;
}

static bool
split_kv(const std::string &line, std::string *key, std::string *value)
{
    size_t pos = line.find(':');
    if (pos == std::string::npos)
        return false;
    *key = trim_copy(line.substr(0, pos));
    *value = strip_quotes(trim_copy(line.substr(pos + 1)));
    return !key->empty();
}

struct stage_config_state_t {
    std::once_flag once;
    std::unordered_map<std::string, std::string> overrides;
};

static stage_config_state_t &stage_config_state()
{
    static stage_config_state_t st;
    return st;
}

static const char *map_stage_field_to_env(const std::string &section,
                                          const std::string &key)
{
    if (section == "ingress") {
        if (key == "transport")
            return "DRAVA_TRANSPORT";
        if (key == "url")
            return "NATS_URL";
        if (key == "stream")
            return "DRAVA_STREAM";
        if (key == "subject")
            return "DRAVA_SUBJECT";
        if (key == "durable")
            return "DRAVA_DURABLE";
        if (key == "fetch_batch")
            return "DRAVA_JS_FETCH_BATCH";
        if (key == "callback_batch")
            return "DRAVA_CALLBACK_BATCH";
        if (key == "fetch_timeout_ms")
            return "DRAVA_FETCH_TIMEOUT_MS";
    } else if (section == "egress") {
        if (key == "stream")
            return "DRAVA_OUTPUT_STREAM";
        if (key == "subject")
            return "DRAVA_OUTPUT_SUBJECT";
    }
    return nullptr;
}

static void load_stage_config_once()
{
    const char *cfg_path = env_get("DRAVA_STAGE_CONFIG");
    const char *stage_name = env_get("DRAVA_STAGE_NAME");
    if (cfg_path == nullptr || stage_name == nullptr)
        return;

    std::ifstream in(cfg_path);
    if (!in.good()) {
        LOGGER_WARN("DRAVA_STAGE_CONFIG not readable: %s", cfg_path);
        return;
    }

    std::unordered_map<std::string, std::string> local;
    bool in_stages = false;
    bool in_target_stage = false;
    std::string section;
    std::string line;
    while (std::getline(in, line)) {
        size_t hash = line.find('#');
        if (hash != std::string::npos)
            line.resize(hash);
        if (line.empty())
            continue;

        size_t indent = 0;
        while (indent < line.size() && line[indent] == ' ')
            ++indent;
        std::string body = trim_copy(line.substr(indent));
        if (body.empty())
            continue;

        if (body == "stages:") {
            in_stages = true;
            in_target_stage = false;
            section.clear();
            continue;
        }
        if (!in_stages)
            continue;

        if (indent == 2 && body.rfind("- ", 0) == 0) {
            in_target_stage = false;
            section.clear();
            std::string key;
            std::string value;
            std::string kv = trim_copy(body.substr(2));
            if (split_kv(kv, &key, &value) && key == "name" &&
                value == stage_name) {
                in_target_stage = true;
            }
            continue;
        }
        if (!in_target_stage)
            continue;

        if (indent == 4 && (body == "ingress:" || body == "egress:")) {
            section = body.substr(0, body.size() - 1);
            continue;
        }

        if (indent >= 6 && !section.empty()) {
            std::string key;
            std::string value;
            if (!split_kv(body, &key, &value))
                continue;
            const char *env_key = map_stage_field_to_env(section, key);
            if (env_key != nullptr)
                local[env_key] = value;
        }
    }

    if (!local.empty()) {
        auto &st = stage_config_state();
        st.overrides = std::move(local);
        LOGGER_INFO("Loaded stage config: file=%s stage=%s overrides=%zu",
                    cfg_path, stage_name, st.overrides.size());
    }
}

static const char *stage_config_lookup(const char *key)
{
    auto &st = stage_config_state();
    std::call_once(st.once, load_stage_config_once);
    auto it = st.overrides.find(std::string(key));
    if (it == st.overrides.end())
        return nullptr;
    return it->second.c_str();
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
        s = stage_config_lookup(key);
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
    if (!s)
        s = stage_config_lookup(key);
    return s ? s : default_value;
}

uint64_t drava_monotonic_ns()
{
    auto now = std::chrono::steady_clock::now().time_since_epoch();
    return (uint64_t)std::chrono::duration_cast<std::chrono::nanoseconds>(now)
            .count();
}

bool drava_payload_is_eos(const void *data, size_t data_len)
{
    if (data == nullptr || data_len < 10)
        return false;
    static const char *prefix = "DRAVA_EOS:";
    return std::memcmp(data, prefix, 10) == 0;
}

void drava_stats_record_callback_batch(drava_t *drava,
                                       size_t frame_count,
                                       size_t total_bytes,
                                       uint64_t first_recv_ns,
                                       uint64_t last_recv_ns,
                                       uint64_t callback_start_ns,
                                       uint64_t callback_end_ns)
{
    if (drava == nullptr)
        return;
    (void)last_recv_ns;
    const uint64_t callback_ns = (callback_end_ns >= callback_start_ns) ?
                                         (callback_end_ns - callback_start_ns) :
                                         0;
    drava->rx_msgs.fetch_add(1);
    drava->rx_items.fetch_add((uint64_t)frame_count);
    drava->rx_bytes.fetch_add((uint64_t)total_bytes);
    drava->callback_batches.fetch_add(1);
    drava->callback_ns_sum.fetch_add(callback_ns);
    uint64_t zero = 0;
    if (first_recv_ns > 0)
        (void)drava->first_rx_ns.compare_exchange_strong(zero, first_recv_ns);
    if (callback_end_ns > 0)
        drava->last_stage_ns.store(callback_end_ns);
    uint64_t prev = drava->callback_ns_max.load();
    while (callback_ns > prev &&
           !drava->callback_ns_max.compare_exchange_weak(prev, callback_ns)) {
    }
}

void drava_stats_record_stage_latency_ns(drava_t *drava, uint64_t latency_ns)
{
    if (drava == nullptr)
        return;
    drava->stage_latency_samples.fetch_add(1);
    drava->stage_latency_ns_sum.fetch_add(latency_ns);
    uint64_t prev = drava->stage_latency_ns_max.load();
    while (latency_ns > prev &&
           !drava->stage_latency_ns_max.compare_exchange_weak(prev,
                                                              latency_ns)) {
    }
}

void drava_stats_record_tx(drava_t *drava,
                           size_t data_len,
                           uint64_t publish_ns,
                           uint64_t publish_end_ns)
{
    if (drava == nullptr)
        return;
    drava->tx_msgs.fetch_add(1);
    drava->tx_bytes.fetch_add((uint64_t)data_len);
    drava->publish_ns_sum.fetch_add(publish_ns);
    uint64_t prev = drava->publish_ns_max.load();
    while (publish_ns > prev &&
           !drava->publish_ns_max.compare_exchange_weak(prev, publish_ns)) {
    }
    if (publish_end_ns > 0)
        drava->last_stage_ns.store(publish_end_ns);
}

void drava_stats_log_snapshot(drava_t *drava, const char *reason)
{
    if (drava == nullptr)
        return;
    drava_stats_t s;
    if (drava->stats_snapshot(&s) != DRAVA_SUCCESS)
        return;
    const double cb_avg_ms = (s.callback_batches > 0) ?
                                     ((double)s.callback_ns_sum /
                                      (double)s.callback_batches / 1.0e6) :
                                     0.0;
    const double cb_total_s = (double)s.callback_ns_sum / 1.0e9;
    const double publish_total_s = (double)s.publish_ns_sum / 1.0e9;
    const double compute_total_s =
            (s.callback_ns_sum >= s.publish_ns_sum) ?
                    (double)(s.callback_ns_sum - s.publish_ns_sum) / 1.0e9 :
                    0.0;
    const double stage_avg_ms =
            (s.stage_latency_samples > 0) ?
                    ((double)s.stage_latency_ns_sum /
                     (double)s.stage_latency_samples / 1.0e6) :
                    0.0;
    const double stage_max_ms = (double)s.stage_latency_ns_max / 1.0e6;
    const double stage_total_s =
            (s.first_rx_ns > 0 && s.last_stage_ns > s.first_rx_ns) ?
                    (double)(s.last_stage_ns - s.first_rx_ns) / 1.0e9 :
                    0.0;
    const double stage_total_fps = (s.rx_items > 0 && stage_total_s > 0.0) ?
                                           (double)s.rx_items / stage_total_s :
                                           0.0;
    const double rx_item_fps = (s.rx_items > 0 && stage_total_s > 0.0) ?
                                       (double)s.rx_items / stage_total_s :
                                       0.0;
    const double tx_msg_fps = (s.tx_msgs > 0 && stage_total_s > 0.0) ?
                                      (double)s.tx_msgs / stage_total_s :
                                      0.0;
    const char *stage_name =
            drava_env_get_str_default("DRAVA_STAGE_NAME", "unknown");
    LOGGER_INFO(
            "[drava-metrics] reason=%s rx_msgs=%" PRIu64 " rx_items=%" PRIu64
            " rx_bytes=%" PRIu64 " tx_msgs=%" PRIu64 " tx_bytes=%" PRIu64
            " cb_batches=%" PRIu64 " cb_avg_ms=%.3f stage_samples=%" PRIu64
            " stage_avg_ms=%.3f stage_max_ms=%.3f rx_item_fps=%.2f tx_msg_fps=%.2f "
            "cb_total_s=%.6f publish_total_s=%.6f compute_total_s=%.6f "
            "stage_total_s=%.6f stage_total_fps=%.2f stage=%s",
            (reason != nullptr ? reason : "snapshot"), s.rx_msgs, s.rx_items,
            s.rx_bytes, s.tx_msgs, s.tx_bytes, s.callback_batches, cb_avg_ms,
            s.stage_latency_samples, stage_avg_ms, stage_max_ms, rx_item_fps,
            tx_msg_fps, cb_total_s, publish_total_s, compute_total_s,
            stage_total_s, stage_total_fps, stage_name);
}

uint64_t drava_callback_context_recv_ts_ns()
{
    return g_callback_recv_ts_ns;
}

void drava_callback_task_begin(drava_t *drava)
{
    if (drava == nullptr)
        return;
    drava->pending_callback_tasks.fetch_add(1);
}

void drava_callback_task_end(drava_t *drava, bool saw_eos)
{
    if (drava == nullptr)
        return;

    if (saw_eos)
        drava->pending_rx_eos_snapshot.store(1);

    const uint64_t remaining = drava->pending_callback_tasks.fetch_sub(1) - 1;
    if (remaining != 0)
        return;

    if (drava->pending_rx_eos_snapshot.exchange(0) != 0)
        drava_stats_log_snapshot(drava, "rx_eos");
    if (drava->pending_tx_eos_snapshot.exchange(0) != 0)
        drava_stats_log_snapshot(drava, "tx_eos");
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
    size_t total_bytes = 0;
    bool saw_eos = false;
    size_t data_frame_count = 0;
    uint64_t first_recv_ns = 0;
    uint64_t last_recv_ns = 0;

    for (size_t i = 0; i < payloads.size(); ++i) {
        const std::string &payload = payloads[i];
        drava_frame_t &frame = frames[i];
        frame.frame_id = drava->next_frame_id.fetch_add(1);
        frame.recv_ts_ns = drava_monotonic_ns();
        if (first_recv_ns == 0)
            first_recv_ns = frame.recv_ts_ns;
        last_recv_ns = frame.recv_ts_ns;
        frame.data = payload.data();
        frame.data_len = payload.size();
        total_bytes += payload.size();
        if (drava_payload_is_eos(payload.data(), payload.size())) {
            saw_eos = true;
        } else {
            data_frame_count += 1;
        }
    }

    drava_frame_batch_t batch;
    batch.batch_id = batch_id;
    batch.count = (uint32_t)frames.size();
    batch.frames = frames.data();
    const uint64_t prev_recv_ts = g_callback_recv_ts_ns;
    g_callback_recv_ts_ns = frames.empty() ? 0 : frames[0].recv_ts_ns;
    const uint64_t cb_t0 = drava_monotonic_ns();
    if (drava->callback_serialize) {
        std::lock_guard<std::mutex> lock(drava->callback_mutex);
        drava->frame_routine(&batch, drava->frame_routine_user_data);
    } else {
        drava->frame_routine(&batch, drava->frame_routine_user_data);
    }
    const uint64_t cb_t1 = drava_monotonic_ns();
    g_callback_recv_ts_ns = prev_recv_ts;
    drava_stats_record_callback_batch(drava, data_frame_count, total_bytes,
                                      first_recv_ns, last_recv_ns, cb_t0,
                                      cb_t1);
    drava_callback_task_end(drava, saw_eos);
}

void drava_dispatch_payload_batch(drava_t *drava,
                                  device_global_id_t device_global_id,
                                  const std::vector<std::string> &payloads)
{
    drava_dispatch_execute(drava, device_global_id, payloads);
}
