/*******************************************************************************
 * Copyright 2025 UChicago Argonne, LLC.
 * (c.f. AUTHORS, LICENSE)
 *
 * This file is part of the drava project.
 * For more info, see https://github.com/anlsys/drava
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *****************************************************************************/

# include <drava/drava.h>

int
drava_t::init(void)
{
    this->runtime.init();
    return DRAVA_SUCCESS;
}

int
drava_t::run(drava_routine_t routine)
{
    LOGGER_FATAL("TODO");
    // fork a team of thread, with 1 thread per device, reading on a socket,
    // and executing drava operations
    return DRAVA_SUCCESS;
}

int
drava_t::deinit(void)
{
    this->runtime.deinit();
    return DRAVA_SUCCESS;
}
