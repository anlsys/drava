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
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Return codes for Drava C API functions. DRAVA_SUCCESS is zero; all others
 * are positive error codes.
 */
typedef enum drava_rcode_t {
    DRAVA_SUCCESS = 0,  /**< Operation succeeded. */
    DRAVA_ERROR = 1,    /**< Unspecified error. */
    DRAVA_EINVAL = 2,   /**< Invalid argument. */
    DRAVA_ENOTSUP = 3   /**< Operation not supported (e.g. transport not built in). */
} drava_rcode_t;

/**
 * Transport backend used to move frames between stages. Selected via
 * transport.type in pipeline.yaml.
 */
typedef enum drava_transport_t {
    DRAVA_TRANSPORT_SOCKET = 0,  /**< Unix-domain socket transport. */
    DRAVA_TRANSPORT_NATS = 1     /**< NATS JetStream transport. */
} drava_transport_t;

/**
 * Log verbosity levels, ordered from most to least severe. A message is emitted
 * when its level is at or below the runtime's configured verbosity.
 */
typedef enum drava_verbose_t {
    DRAVA_VERBOSE_FATAL = 0,  /**< Fatal error. */
    DRAVA_VERBOSE_ERROR = 1,  /**< Error. */
    DRAVA_VERBOSE_WARN = 2,   /**< Warning. */
    DRAVA_VERBOSE_INFO = 3,   /**< Informational. */
    DRAVA_VERBOSE_IMPL = 4,   /**< Implementation detail. */
    DRAVA_VERBOSE_DEBUG = 5   /**< Debug. */
} drava_verbose_t;

/**
 * A single frame delivered to a stage callback.
 */
typedef struct drava_frame_t {
    uint64_t frame_id;      /**< Runtime-assigned monotonic frame id. */
    uint64_t recv_ts_ns;    /**< Receive timestamp at Drava ingress (ns). */
    const void *data;       /**< Frame payload bytes (not owned by the callback). */
    size_t data_len;        /**< Length of @ref data in bytes. */
} drava_frame_t;

/**
 * A batch of frames passed to the stage callback.
 *
 * @ref base_index is the global 0-based index of the first frame in this batch
 * across the whole stream (EOS markers excluded). It lets a callback compute
 * per-frame stream positions without keeping its own counter, which is what
 * makes callbacks safe to run concurrently and out of order.
 */
typedef struct drava_frame_batch_t {
    uint64_t batch_id;             /**< Runtime-assigned monotonic batch id. */
    uint32_t count;                /**< Number of frames in @ref frames. */
    uint64_t base_index;           /**< Global index of the first frame in the batch. */
    const drava_frame_t *frames;   /**< Array of @ref count frames. */
} drava_frame_batch_t;

/**
 * Cumulative per-stage counters, as returned by drava_stats_snapshot(). Derived
 * quantities (throughput, average latency, energy) are computed from these; see
 * the metrics documentation.
 */
typedef struct drava_stats_t {
    uint64_t rx_msgs;               /**< Transport messages received. */
    uint64_t rx_items;              /**< Frames received (excludes EOS markers). */
    uint64_t rx_bytes;              /**< Bytes received. */
    uint64_t tx_msgs;               /**< Messages published downstream. */
    uint64_t tx_bytes;              /**< Bytes published downstream. */
    uint64_t callback_batches;      /**< Number of callback batches dispatched. */
    uint64_t callback_ns_sum;       /**< Total time spent in the callback (ns). */
    uint64_t callback_ns_max;       /**< Longest single callback (ns). */
    uint64_t publish_ns_sum;        /**< Total time spent publishing (ns). */
    uint64_t publish_ns_max;        /**< Longest single publish (ns). */
    uint64_t stage_latency_samples; /**< Number of per-frame latency samples. */
    uint64_t stage_latency_ns_sum;  /**< Sum of per-frame stage latencies (ns). */
    uint64_t stage_latency_ns_max;  /**< Maximum per-frame stage latency (ns). */
    uint64_t first_rx_ns;           /**< Timestamp of the first received frame (ns). */
    uint64_t last_stage_ns;         /**< Timestamp of the last stage completion (ns). */
} drava_stats_t;

/**
 * Application callback invoked once per batch of received frames. @p user_data
 * is the pointer passed to drava_register_frame_routine(). The return value is
 * currently unused.
 */
typedef void *(*drava_frame_routine_t)(const drava_frame_batch_t *batch,
                                       void *user_data);

/**
 * End-of-stream routine type.
 *
 * Invoked once by the runtime after the EOS marker has been observed and all
 * in-flight data callbacks have drained. @p expected_frames is the frame count
 * carried by the EOS marker (0 if the marker had no/invalid count).
 */
typedef void (*drava_eos_routine_t)(uint64_t expected_frames, void *user_data);

/** Register the per-batch frame callback. Returns DRAVA_SUCCESS on success. */
int drava_register_frame_routine(drava_frame_routine_t routine,
                                 void *user_data);

/** Register the optional end-of-stream callback (see drava_eos_routine_t). */
int drava_register_eos_routine(drava_eos_routine_t routine, void *user_data);

/**
 * Initialize the runtime: apply the stage configuration and start the task
 * runtime. Returns DRAVA_ENOTSUP if the configured transport is unavailable.
 */
int drava_init(void);

/** Run the stage: receive frames and dispatch batches until end-of-stream. */
int drava_listen(void);

/** Publish one payload downstream through the configured transport. */
int drava_publish(const void *data, size_t data_len);

/** Shut down the runtime and release resources. */
int drava_deinit(void);

/** Emit a log message at the given verbosity level. */
int drava_log(const drava_verbose_t verbose_level, const char *msg);

/** Copy the current cumulative counters into @p out_stats. */
int drava_stats_snapshot(drava_stats_t *out_stats);

/** Reset all cumulative counters to zero. */
int drava_stats_reset(void);

/** Override the number of frames grouped into each callback batch. */
int drava_set_callback_batch(size_t batch_size);

/** Override the idle-flush timeout (ms) for partial callback batches. */
int drava_set_callback_flush_timeout_ms(int timeout_ms);

/** Enable (1) or disable (0) serialized, single-threaded callback dispatch. */
int drava_set_callback_serialize(int enabled);

/**
 * When enabled (default), the runtime re-publishes the EOS marker to the
 * configured egress once the stream drains. Terminal stages set this to 0.
 */
int drava_set_forward_eos(int enabled);

/**
 * Return non-zero if the payload is an EOS marker. When it is and out_count is
 * non-NULL, *out_count receives the frame count encoded after the prefix
 * (0 if absent/invalid).
 */
int drava_payload_parse_eos(const void *data,
                            size_t data_len,
                            uint64_t *out_count);

#ifdef __cplusplus
}
#endif

#endif /* __DRAVA_C_H__ */
