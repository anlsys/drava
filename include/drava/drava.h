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
#define __DRAVA_H__

#include <drava/drava_c.h>
#include <xkrt/runtime.h>

XKRT_NAMESPACE_USE;

struct drava_device_t {
    /* xkrt team of threads */
    team_t team;

    /* the list of places for that device (= 1x cpuset) */
    thread_place_t places_list;
};

struct drava_t {
    /***********/
    /* Members */
    /***********/

    /* runtime instance */
    xkrt::runtime_t runtime;

    /* devices */
    drava_device_t devices[XKRT_DEVICES_MAX];

    /* the routine to run */
    drava_routine_t routine;

    /* which transport backend to use (socket or NATS) */
    drava_transport_t transport_type;

    /***********/
    /* Methods */
    /***********/

    /* Initialize drava */
    int init(drava_transport_t transport_type);

    /* Register a routine (TODO: add an event associated with it?) */
    int register_routine(drava_routine_t routine);

    /* Read until the socket is closed */
    int listen(void);

    /* Deinitialize drava */
    int deinit(void);

    /* Log a debug message */
    int log(const int verbose_level, const char * msg);
};

void parse_line(drava_t *drava,
                device_global_id_t device_global_id,
                const std::string &line);

/* Transport-specific entry points (implemented in transport_*.cc) */
int drava_transport_socket_main(drava_t *drava,
                                device_global_id_t device_global_id,
                                thread_t *thread);

int drava_transport_nats_main(drava_t *drava,
                              device_global_id_t device_global_id,
                              thread_t *thread);

/* main for a thread on a given device */
int drava_transport_main(drava_t *drava,
                         device_global_id_t device_global_id,
                         thread_t *thread);

#endif /* __DRAVA_H__ */
