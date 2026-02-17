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
    if (rc != DRAVA_SUCCESS) {
        LOGGER_ERROR("drava_init: invalid/unsupported DRAVA_TRANSPORT (rc=%d)",
                     rc);
        return rc;
    }
    LOGGER_INFO("drava_init: selected transport=%s",
                transport == DRAVA_TRANSPORT_NATS ? "nats" : "socket");
    return drava.init(transport);
}

int drava_register_frame_routine(drava_frame_routine_t routine, void *user_data)
{
    LOGGER_INFO("drava_register_frame_routine: routine=%p user_data=%p",
                (void *)routine, user_data);
    return drava.register_frame_routine(routine, user_data);
}

int drava_listen(void)
{
    return drava.listen();
}

int drava_deinit(void)
{
    return drava.deinit();
}

int drava_log(const drava_verbose_t verbose_level, const char *msg)
{
    return drava.log(verbose_level, msg);
}
