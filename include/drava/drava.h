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
# define __DRAVA_H__

extern "C" {
    # include <drava/drava_c.h>
};

# include <xkrt/runtime.h>

struct drava_t
{
    /***********/
    /* Members */
    /***********/

    /* runtime instance */
    xkrt::runtime_t runtime;

    /***********/
    /* Methods */
    /***********/

    /* Initialize drava */
    int init(void);

    /* Read until the socket is closed */
    int run(drava_routine_t routine);

    /* Deinitialize drava */
    int deinit(void);

};

# endif /* __DRAVA_H__ */
