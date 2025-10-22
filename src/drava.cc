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

struct drava_args_t {
    drava_t * drava;
    device_global_id_t device_global_id;
};

/* The routine executed by each thread of each team of each device */
static void *
drava_main(team_t * team, thread_t * thread)
{
    drava_args_t * args = (drava_args_t *) team->desc.args;
    assert(args);

    LOGGER_DEBUG("Starting thread %u on device %d", thread->tid, args->device_global_id);
    drava_device_main(args->drava, args->device_global_id, thread);

    return NULL;
}

int
drava_t::listen(drava_routine_t routine)
{
    this->routine = routine;

    /* Fork a team of threads for each device */
    drava_args_t args[XKRT_DEVICES_MAX];

    for (device_global_id_t i = 0 ; i < this->runtime.get_ndevices() ; ++i)
    {
        if (i == HOST_DEVICE_GLOBAL_ID)
            continue ;

        /* save team information */
        drava_args_t * arg = args + i;
        arg->drava = this;
        arg->device_global_id = i;

        /* drava device */
        drava_device_t * drava_device = this->devices + i;

        /* setup the team */
        team_t * team = &drava_device->team;
        team->desc.routine             = drava_main;
        team->desc.args                = arg;
        team->desc.nthreads            = 4;
        team->desc.master_is_member    = false;
        team->desc.binding.mode        = XKRT_TEAM_BINDING_MODE_COMPACT;
        team->desc.binding.places      = XKRT_TEAM_BINDING_PLACES_EXPLICIT;
        team->desc.binding.nplaces     = 1;
        team->desc.binding.places_list = &drava_device->places_list;

        /* TODO: XKRT API is quite ugly */
        /* retrieve the places of that device */
        device_t * device = this->runtime.device_get(i);
        assert(device);

        driver_t * driver = this->runtime.driver_get(device->driver_type);
        assert(driver);

        int err = driver->f_device_cpuset(this->runtime.topology,
                team->desc.binding.places_list, device->driver_id);
        if (err)
            LOGGER_FATAL("Fail to retrieve cpuset for device %u", i);

        /* spawn threads of the team */
        this->runtime.team_create(team);
    }

    /* Wait for all teams completion */
    for (device_global_id_t i = 0 ; i < this->runtime.get_ndevices() ; ++i)
        this->runtime.team_join(&this->devices[i].team);

    return DRAVA_SUCCESS;
}

int
drava_t::deinit(void)
{
    this->runtime.deinit();
    return DRAVA_SUCCESS;
}
