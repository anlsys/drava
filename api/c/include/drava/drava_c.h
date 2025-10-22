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
# define __DRAVA_C_H__

/**
 * Drava return code
 */
typedef enum    drava_rcode_t
{
    DRAVA_SUCCESS   = 0,
    DRAVA_ERROR     = 1
}               drava_rcode_t;

/**
 * Drava operations
 */
typedef enum    drava_op_t
{
    DRAVA_OP_WRITE32,
    DRAVA_OP_READ32,
    DRAVA_OP_DONE
}               drava_op_t;

/** Drava routine type */
typedef void * (*drava_routine_t)(void);

/* Initialize drava */
int drava_init(void);

/* Read until the socket is closed */
int drava_listen(drava_routine_t routine);

/* Deinitialize drava */
int drava_deinit(void);

# endif /* __DRAVA_C_H__ */
