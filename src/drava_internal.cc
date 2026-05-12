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
#include <yaml-cpp/yaml.h>

static const char *env_get(const char *k)
{
    const char *v = getenv(k);
    return (v && v[0] != '\0') ? v : nullptr;
}

static thread_local uint64_t g_callback_recv_ts_ns = 0;

struct stage_config_state_t {
    std::once_flag once;
    bool loaded = false;
    drava_transport_t transport_type = DRAVA_TRANSPORT_SOCKET;
    std::string stage_name = "unknown";
    std::string nats_url = "nats://127.0.0.1:4222";
    drava_stage_runtime_config_t runtime_cfg;
    drava_stage_ingress_config_t ingress_cfg;
    drava_stage_egress_config_t egress_cfg;
    int nats_async_drain_timeout_ms = 30000;
};

static stage_config_state_t &stage_config_state()
{
    static stage_config_state_t st;
    return st;
}

static const char *drava_transport_name(drava_transport_t type)
{
    switch (type) {
    case DRAVA_TRANSPORT_SOCKET:
        return "socket";
    case DRAVA_TRANSPORT_NATS:
        return "nats";
    default:
        return "socket";
    }
}

static bool drava_parse_transport_name(const std::string &value,
                                       drava_transport_t *out)
{
    if (out == nullptr)
        return false;
    if (value == "socket") {
        *out = DRAVA_TRANSPORT_SOCKET;
        return true;
    }
    if (value == "nats") {
        *out = DRAVA_TRANSPORT_NATS;
        return true;
    }
    return false;
}

static bool
yaml_read_string(const YAML::Node &node, const char *key, std::string *out)
{
    if (out == nullptr || !node || !node[key] || !node[key].IsScalar())
        return false;
    *out = node[key].as<std::string>();
    return true;
}

static bool yaml_read_int(const YAML::Node &node, const char *key, int *out)
{
    if (out == nullptr || !node || !node[key] || !node[key].IsScalar())
        return false;
    *out = node[key].as<int>();
    return true;
}

static bool
yaml_read_size_t(const YAML::Node &node, const char *key, size_t *out)
{
    if (out == nullptr || !node || !node[key] || !node[key].IsScalar())
        return false;
    *out = node[key].as<size_t>();
    return true;
}

static bool yaml_read_bool(const YAML::Node &node, const char *key, bool *out)
{
    if (out == nullptr || !node || !node[key] || !node[key].IsScalar())
        return false;
    *out = node[key].as<bool>();
    return true;
}

static void load_stage_config_once()
{
    auto &st = stage_config_state();
    const char *cfg_path = env_get("DRAVA_STAGE_CONFIG");
    const char *stage_name = env_get("DRAVA_STAGE_NAME");
    if (cfg_path == nullptr || stage_name == nullptr)
        return;

    try {
        YAML::Node root = YAML::LoadFile(cfg_path);
        st.stage_name = stage_name;

        YAML::Node transport = root["transport"];
        if (transport) {
            if (transport["type"] && transport["type"].IsScalar()) {
                drava_transport_t parsed_type;
                if (drava_parse_transport_name(
                            transport["type"].as<std::string>(),
                            &parsed_type)) {
                    st.transport_type = parsed_type;
                }
            }
            (void)yaml_read_string(transport, "nats_url", &st.nats_url);
        }

        YAML::Node stages = root["stages"];
        if (stages && stages.IsSequence()) {
            for (const YAML::Node &stage : stages) {
                YAML::Node name_node = stage["name"];
                if (!name_node || !name_node.IsScalar())
                    continue;
                if (name_node.as<std::string>() != st.stage_name)
                    continue;

                YAML::Node runtime = stage["runtime"];
                if (runtime && runtime.IsMap()) {
                    (void)yaml_read_int(runtime, "threads",
                                        &st.runtime_cfg.threads);
                    (void)yaml_read_size_t(runtime, "callback_batch",
                                           &st.runtime_cfg.callback_batch);
                    (void)yaml_read_int(
                            runtime, "callback_flush_timeout_ms",
                            &st.runtime_cfg.callback_flush_timeout_ms);
                    (void)yaml_read_bool(runtime, "callback_serialize",
                                         &st.runtime_cfg.callback_serialize);
                    (void)yaml_read_int(runtime, "nats_async_drain_timeout_ms",
                                        &st.nats_async_drain_timeout_ms);
                }

                YAML::Node ingress = stage["ingress"];
                if (ingress && ingress.IsMap()) {
                    (void)yaml_read_string(ingress, "stream",
                                           &st.ingress_cfg.stream);
                    (void)yaml_read_string(ingress, "subject",
                                           &st.ingress_cfg.subject);
                    (void)yaml_read_string(ingress, "durable",
                                           &st.ingress_cfg.durable);
                    (void)yaml_read_string(ingress, "socket_path",
                                           &st.ingress_cfg.socket_path);
                    (void)yaml_read_int(ingress, "fetch_batch",
                                        &st.ingress_cfg.fetch_batch);
                    (void)yaml_read_int(ingress, "fetch_timeout_ms",
                                        &st.ingress_cfg.fetch_timeout_ms);
                }

                YAML::Node egress = stage["egress"];
                if (egress && egress.IsMap()) {
                    (void)yaml_read_string(egress, "stream",
                                           &st.egress_cfg.stream);
                    (void)yaml_read_string(egress, "subject",
                                           &st.egress_cfg.subject);
                    (void)yaml_read_string(egress, "output_fifo_path",
                                           &st.egress_cfg.output_fifo_path);
                }

                st.loaded = true;
                break;
            }
        }
    } catch (const std::exception &exc) {
        LOGGER_WARN("Failed to parse DRAVA_STAGE_CONFIG=%s: %s", cfg_path,
                    exc.what());
        return;
    }

    if (st.loaded) {
        LOGGER_INFO("Loaded stage config: file=%s stage=%s transport=%s",
                    cfg_path, st.stage_name.c_str(),
                    drava_transport_name(st.transport_type));
    }
}

static const stage_config_state_t &drava_stage_config()
{
    auto &st = stage_config_state();
    std::call_once(st.once, load_stage_config_once);
    return st;
}

int drava_apply_stage_config(drava_t *drava)
{
    if (drava == nullptr)
        return DRAVA_EINVAL;

    const auto &cfg = drava_stage_config();
    if (cfg.transport_type == DRAVA_TRANSPORT_NATS) {
#ifdef DRAVA_HAS_NATS
        drava->transport_type = cfg.transport_type;
#else
        return DRAVA_ENOTSUP;
#endif
    } else {
        drava->transport_type = cfg.transport_type;
    }
    drava->stage_name = cfg.stage_name;
    drava->nats_url = cfg.nats_url;
    drava->runtime_cfg = cfg.runtime_cfg;
    drava->ingress_cfg = cfg.ingress_cfg;
    drava->egress_cfg = cfg.egress_cfg;
    drava->nats_async_drain_timeout_ms = cfg.nats_async_drain_timeout_ms;
    return DRAVA_SUCCESS;
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
            stage_total_s, stage_total_fps, drava->stage_name.c_str());
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
                                   device_unique_id_t device_unique_id,
                                   const std::vector<std::string> &payloads)
{
    (void)device_unique_id;
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
                                  device_unique_id_t device_unique_id,
                                  const std::vector<std::string> &payloads)
{
    drava_dispatch_execute(drava, device_unique_id, payloads);
}
