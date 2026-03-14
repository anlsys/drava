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

    /* Batching and id allocation for callback dispatch */
    size_t callback_batch_size;
    std::atomic<uint64_t> next_batch_id;
    std::atomic<uint64_t> next_frame_id;
    std::atomic<uint64_t> rx_msgs;
    std::atomic<uint64_t> rx_frames;
    std::atomic<uint64_t> rx_bytes;
    std::atomic<uint64_t> tx_msgs;
    std::atomic<uint64_t> tx_bytes;
    std::atomic<uint64_t> callback_batches;
    std::atomic<uint64_t> callback_frames;
    std::atomic<uint64_t> callback_ns_sum;
    std::atomic<uint64_t> callback_ns_max;
    std::atomic<uint64_t> stage_latency_samples;
    std::atomic<uint64_t> stage_latency_ns_sum;
    std::atomic<uint64_t> stage_latency_ns_max;
    std::atomic<uint64_t> rx_first_ns;
    std::atomic<uint64_t> rx_last_ns;
    std::atomic<uint64_t> tx_first_ns;
    std::atomic<uint64_t> tx_last_ns;

    /***********/
    /* Methods */
    /***********/

    /* Initialize drava */
    int init(drava_transport_t transport_type);

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
};

int drava_parse_transport_from_env(drava_transport_t *out);

const char *drava_env_get_str_default(const char *key,
                                      const char *default_value);

int drava_env_get_int_default(const char *key, int default_value);

bool drava_payload_is_eos(const void *data, size_t data_len);

uint64_t drava_monotonic_ns();

void drava_stats_record_callback_batch(drava_t *drava,
                                       size_t frame_count,
                                       size_t total_bytes,
                                       uint64_t callback_ns);

void drava_stats_record_stage_latency_ns(drava_t *drava, uint64_t latency_ns);

void drava_stats_record_tx(drava_t *drava, size_t data_len);

void drava_stats_log_snapshot(drava_t *drava, const char *reason);

uint64_t drava_callback_context_recv_ts_ns();

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

/* main for a thread on a given device */
int drava_transport_main(drava_t *drava,
                         device_global_id_t device_global_id,
                         thread_t *thread);

#endif /* __DRAVA_H__ */
