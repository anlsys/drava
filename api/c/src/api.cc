/*******************************************************************************
 * Copyright 2025 UChicago Argonne, LLC.
 * (c.f. AUTHORS, LICENSE)
 *
 * This file is part of the drava project.
 * For more info, see https://github.com/anlsys/drava
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *****************************************************************************/

#include <drava/drava.h>

/* The C api uses a global singleton */
static drava_t drava;

int drava_init(void)
{
    drava_transport_t transport = DRAVA_TRANSPORT_SOCKET;
    int rc = drava_parse_transport_from_env(&transport);
    if (rc != DRAVA_SUCCESS) return rc;
    return drava.init(transport);
}

int drava_register_routine(drava_routine_t routine)
{
    return drava.register_routine(routine);
}

int drava_listen(void)
{
    return drava.listen();
}

int drava_deinit(void)
{
    return drava.deinit();
}

int drava_log(const drava_verbose_t verbose_level, const char * msg)
{
    return drava.log(verbose_level, msg);
}
