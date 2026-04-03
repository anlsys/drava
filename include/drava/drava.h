/*******************************************************************************
 * Copyright 2025 UChicago Argonne, LLC.
 * (c.f. AUTHORS, LICENSE)
 *
 * This file is part of the drava project.
 * For more info, see https://github.com/anlsys/drava
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *****************************************************************************/

#ifndef __DRAVA_H__
#define __DRAVA_H__

#include <atomic>
#include <cstdint>
#include <drava/drava_c.h>
#include <mutex>
#include <string>
#include <vector>
#include <xkrt/runtime.h>

XKRT_NAMESPACE_USE;

struct drava_device_t {
    /* xkrt team of threads */
    team_t team;

    /* the list of places for that device (= 1x cpuset) */
    thread_place_t places_list;
};

struct drava_stage_runtime_config_t {
    int threads = 4;
    size_t callback_batch = 128;
    int callback_flush_timeout_ms = 0;
    bool callback_serialize = true;
};

struct drava_stage_ingress_config_t {
    std::string stream = "FRAMES";
    std::string subject = "frames.raw";
    std::string durable = "drava_consumer";
    std::string socket_path = "/tmp/accel_2048.sock";
    int fetch_batch = 8;
    int fetch_timeout_ms = 1000;
};

struct drava_stage_egress_config_t {
    std::string stream = "PREDICTIONS";
    std::string subject = "frames.stage1";
    std::string output_fifo_path = "/tmp/drava_stage2_in";
};

struct drava_t {
    /***********/
    /* Members */
    /***********/

    /* runtime instance */
    xkrt::runtime_t runtime;

    /* devices */
    drava_device_t devices[XKRT_DEVICES_MAX];

    /* Batch-aware routine */
    drava_frame_routine_t frame_routine;
    void *frame_routine_user_data;

    /* which transport backend to use (socket or NATS) */
    drava_transport_t transport_type;
    std::string stage_name;
    std::string nats_url;
    drava_stage_runtime_config_t runtime_cfg;
    drava_stage_ingress_config_t ingress_cfg;
    drava_stage_egress_config_t egress_cfg;
    int nats_async_drain_timeout_ms;

    /* Batching and id allocation for callback dispatch */
    size_t callback_batch_size;
    int callback_flush_timeout_ms;
    bool callback_serialize;
    std::mutex callback_mutex;
    std::atomic<uint64_t> next_batch_id;
    std::atomic<uint64_t> next_frame_id;
    std::atomic<uint64_t> rx_msgs;
    std::atomic<uint64_t> rx_items;
    std::atomic<uint64_t> rx_bytes;
    std::atomic<uint64_t> tx_msgs;
    std::atomic<uint64_t> tx_bytes;
    std::atomic<uint64_t> callback_batches;
    std::atomic<uint64_t> callback_ns_sum;
    std::atomic<uint64_t> callback_ns_max;
    std::atomic<uint64_t> publish_ns_sum;
    std::atomic<uint64_t> publish_ns_max;
    std::atomic<uint64_t> stage_latency_samples;
    std::atomic<uint64_t> stage_latency_ns_sum;
    std::atomic<uint64_t> stage_latency_ns_max;
    std::atomic<uint64_t> first_rx_ns;
    std::atomic<uint64_t> last_stage_ns;
    std::atomic<uint64_t> pending_callback_tasks;
    std::atomic<uint64_t> pending_rx_eos_snapshot;
    std::atomic<uint64_t> pending_tx_eos_snapshot;

    /***********/
    /* Methods */
    /***********/

    /* Initialize drava */
    int init(void);

    /* Register a batch-aware routine */
    int register_frame_routine(drava_frame_routine_t routine, void *user_data);

    /* Read until the socket is closed */
    int listen(void);

    /* Publish one payload through the configured transport backend */
    int publish(const void *data, size_t data_len);

    /* Deinitialize drava */
    int deinit(void);

    /* Log a debug message */
    int log(const int verbose_level, const char *msg);

    int stats_snapshot(drava_stats_t *out_stats) const;

    int stats_reset(void);

    int set_callback_batch(size_t batch_size);

    int set_callback_flush_timeout_ms(int timeout_ms);

    int set_callback_serialize(bool enabled);
};

int drava_apply_stage_config(drava_t *drava);

bool drava_payload_is_eos(const void *data, size_t data_len);

uint64_t drava_monotonic_ns();

void drava_stats_record_callback_batch(drava_t *drava,
                                       size_t frame_count,
                                       size_t total_bytes,
                                       uint64_t first_recv_ns,
                                       uint64_t last_recv_ns,
                                       uint64_t callback_start_ns,
                                       uint64_t callback_end_ns);

void drava_stats_record_stage_latency_ns(drava_t *drava, uint64_t latency_ns);

void drava_stats_record_tx(drava_t *drava,
                           size_t data_len,
                           uint64_t publish_ns,
                           uint64_t publish_end_ns);

void drava_stats_log_snapshot(drava_t *drava, const char *reason);

uint64_t drava_callback_context_recv_ts_ns();

void drava_callback_task_begin(drava_t *drava);

void drava_callback_task_end(drava_t *drava, bool saw_eos);

void drava_dispatch_payload_batch(drava_t *drava,
                                  device_global_id_t device_global_id,
                                  const std::vector<std::string> &payloads);

/* Transport-specific entry points (implemented in transport_*.cc) */
int drava_transport_socket_main(drava_t *drava,
                                device_global_id_t device_global_id,
                                thread_t *thread);

int drava_transport_nats_main(drava_t *drava,
                              device_global_id_t device_global_id,
                              thread_t *thread);

int drava_transport_socket_publish(drava_t *drava,
                                   const void *data,
                                   size_t data_len);

int drava_transport_nats_publish(drava_t *drava,
                                 const void *data,
                                 size_t data_len);

int drava_transport_nats_shutdown(drava_t *drava);

/* main for a thread on a given device */
int drava_transport_main(drava_t *drava,
                         device_global_id_t device_global_id,
                         thread_t *thread);

#endif /* __DRAVA_H__ */
