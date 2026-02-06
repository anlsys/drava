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
 * Drava logger levels
 */
typedef enum drava_verbose_t {
    DRAVA_VERBOSE_FATAL = 0, // LOGGER_PRINT_FATAL_ID,
    DRAVA_VERBOSE_ERROR = 1, // LOGGER_PRINT_ERROR_ID,
    DRAVA_VERBOSE_WARN  = 2, // LOGGER_PRINT_WARN_ID,
    DRAVA_VERBOSE_INFO  = 3, // LOGGER_PRINT_INFO_ID,
    DRAVA_VERBOSE_IMPL  = 4, // LOGGER_PRINT_INFO_ID,
    DRAVA_VERBOSE_DEBUG = 5  // LOGGER_PRINT_DEBUG_ID
} drava_verbose_t;

/** Drava routine type */
typedef void *(*drava_routine_t)(const char *s);

int drava_init(void);

int drava_register_routine(drava_routine_t routine);

int drava_listen(void);

int drava_deinit(void);

int drava_log(const drava_verbose_t verbose_level, const char * msg);

#ifdef __cplusplus
}
#endif

#endif /* __DRAVA_C_H__ */
