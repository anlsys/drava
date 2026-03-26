/*******************************************************************************
 * Copyright 2025 UChicago Argonne, LLC.
 * (c.f. AUTHORS, LICENSE)
 *
 * This file is part of the drava project.
 * For more info, see https://github.com/anlsys/drava
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *****************************************************************************/

#ifndef __DRAVA_C_H__
#define __DRAVA_C_H__

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Drava return code
 */
typedef enum drava_rcode_t {
    DRAVA_SUCCESS = 0,
    DRAVA_ERROR = 1,
    DRAVA_EINVAL = 2,
    DRAVA_ENOTSUP = 3
} drava_rcode_t;

/**
 * Drava operations
 */
typedef enum drava_op_t {
    DRAVA_OP_WRITE32,
    DRAVA_OP_READ32,
    DRAVA_OP_DONE
} drava_op_t;

/**
 * Drava transport type
 */
typedef enum drava_transport_t {
    DRAVA_TRANSPORT_SOCKET = 0,
    DRAVA_TRANSPORT_NATS = 1
} drava_transport_t;

/**
 * Global transport configuration shared by the runtime.
 * Stage-local routing/endpoints live under ingress/egress.
 * For now the only global backend-specific field is the NATS server URL.
 */
typedef struct drava_transport_config_t {
    drava_transport_t type;
    const char *nats_url;
} drava_transport_config_t;

/**
 * Drava logger levels
 */
typedef enum drava_verbose_t {
    DRAVA_VERBOSE_FATAL = 0, // LOGGER_PRINT_FATAL_ID,
    DRAVA_VERBOSE_ERROR = 1, // LOGGER_PRINT_ERROR_ID,
    DRAVA_VERBOSE_WARN = 2, // LOGGER_PRINT_WARN_ID,
    DRAVA_VERBOSE_INFO = 3, // LOGGER_PRINT_IN FO_ID,
    DRAVA_VERBOSE_IMPL = 4, // LOGGER_PRINT_IMPL_ID,
    DRAVA_VERBOSE_DEBUG = 5 // LOGGER_PRINT_DEBUG_ID
} drava_verbose_t;

/**
 * Data model for single frame
 */
typedef struct drava_frame_t {
    uint64_t frame_id;
    /* Receive timestamp at Drava ingress */
    uint64_t recv_ts_ns;
    const void *data;
    size_t data_len;
} drava_frame_t;

/**
 * Data model for batch of frames
 */
typedef struct drava_frame_batch_t {
    uint64_t batch_id;
    uint32_t count;
    const drava_frame_t *frames;
} drava_frame_batch_t;

typedef struct drava_stats_t {
    uint64_t rx_msgs;
    uint64_t rx_items;
    uint64_t rx_bytes;
    uint64_t tx_msgs;
    uint64_t tx_bytes;
    uint64_t callback_batches;
    uint64_t callback_ns_sum;
    uint64_t callback_ns_max;
    uint64_t publish_ns_sum;
    uint64_t publish_ns_max;
    uint64_t stage_latency_samples;
    uint64_t stage_latency_ns_sum;
    uint64_t stage_latency_ns_max;
    uint64_t first_rx_ns;
    uint64_t last_stage_ns;
} drava_stats_t;

/** Batch routine type */
typedef void *(*drava_frame_routine_t)(const drava_frame_batch_t *batch,
                                       void *user_data);

int drava_register_frame_routine(drava_frame_routine_t routine,
                                 void *user_data);

int drava_init(void);

int drava_listen(void);

int drava_publish(const void *data, size_t data_len);

int drava_deinit(void);

int drava_log(const drava_verbose_t verbose_level, const char *msg);

int drava_stats_snapshot(drava_stats_t *out_stats);

int drava_stats_reset(void);

int drava_set_callback_batch(size_t batch_size);

int drava_set_callback_flush_timeout_ms(int timeout_ms);

int drava_set_callback_serialize(int enabled);

#ifdef __cplusplus
}
#endif

#endif /* __DRAVA_C_H__ */
