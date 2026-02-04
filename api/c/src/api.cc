/*******************************************************************************
 * Copyright 2025 UChicago Argonne, LLC.
 * (c.f. AUTHORS, LICENSE)
 *
 * This file is part of the drava project.
 * For more info, see https://github.com/anlsys/drava
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *****************************************************************************/

#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <drava/drava.h>

/* The C api uses a global singleton */
static drava_t drava;

static const char *env_get(const char *k) {
    const char *v = getenv(k);
    return (v && v[0] != '\0') ? v : nullptr;
}

static int parse_transport_from_env(drava_transport_t *out)
{
    if (!out) return DRAVA_EINVAL;

    const char *t = env_get("DRAVA_TRANSPORT");
    if (!t || strcmp(t, "auto") == 0) {
        *out = DRAVA_TRANSPORT_SOCKET;
        return DRAVA_SUCCESS;
    }

    if (strcmp(t, "socket") == 0) {
        *out = DRAVA_TRANSPORT_SOCKET;
        return DRAVA_SUCCESS;
    }

    if (strcmp(t, "nats") == 0) {
#ifdef DRAVA_HAS_NATS
        *out = DRAVA_TRANSPORT_NATS;
        return DRAVA_SUCCESS;
#else
        return DRAVA_ENOTSUP;
#endif
    }

    return DRAVA_EINVAL;
}

int drava_init(void)
{
    drava_transport_t transport = DRAVA_TRANSPORT_SOCKET;
    int rc = parse_transport_from_env(&transport);
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
