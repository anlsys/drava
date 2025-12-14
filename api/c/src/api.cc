/*******************************************************************************
 * Copyright 2025 UChicago Argonne, LLC.
 * (c.f. AUTHORS, LICENSE)
 *
 * This file is part of the drava project.
 * For more info, see https://github.com/anlsys/drava
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *****************************************************************************/

# include <assert.h>
# include <drava/drava.h>

/* the C api uses an ugly global singleton, whatever */
static drava_t drava;

extern "C"
int
drava_init_with_transport(drava_transport_t transport_type) {
    /* Forward to the C++ object; drava_t::init stores the choice. */
    return drava.init(transport_type);
}

extern "C"
int
drava_init(const char *transport_name) {
    /* Default to socket backend for backward compatibility. */
    return drava_init_from_string(transport_name);
}


extern "C"
int
drava_init_from_string(const char *transport_name) {
    if (transport_name == NULL || transport_name[0] == '\0') {
        /* Default: socket */
        return drava_init_with_transport(DRAVA_TRANSPORT_SOCKET);
    }

    if (strcmp(transport_name, "socket") == 0) {
        return drava_init_with_transport(DRAVA_TRANSPORT_SOCKET);
    }

    if (strcmp(transport_name, "nats") == 0) {
#ifdef DRAVA_HAS_NATS
        return drava_init_with_transport(DRAVA_TRANSPORT_NATS);
#else
        /* NATS requested but not compiled in. */
        return -2;
#endif
    }

    /* Unknown device string. */
    return -1;
}

extern "C"
int
drava_register_routine(drava_routine_t routine) {
    return drava.register_routine(routine);
}

extern "C"
int
drava_listen(void) {
    return drava.listen();
}

extern "C"
int
drava_deinit(void) {
    return drava.deinit();
}
