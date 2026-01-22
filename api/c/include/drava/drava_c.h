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

/** Drava routine type */
typedef void *(*drava_routine_t)(const char *s);

int drava_init(int *argc, char **argv[]);

int drava_register_routine(drava_routine_t routine);

int drava_listen(void);

int drava_deinit(void);

#ifdef __cplusplus
}
#endif

#endif /* __DRAVA_C_H__ */
