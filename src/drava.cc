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

XKRT_NAMESPACE_USE;

int
drava_t::init(void)
{
    this->runtime.init();
    return DRAVA_SUCCESS;
}

typedef struct  drava_device_t
{
    /* drava instance */
    drava_t * drava;

    /* xkrt team of threads */
    team_t team;

    /* the device of that team */
    device_global_id_t device_global_id;

    /* the list of places for that device (= 1x cpuset) */
    thread_place_t places_list;

}               drava_device_t;

/* The routine executed by each thread of each team of each device */
static void *
drava_main(team_t * team, thread_t * thread)
{
    drava_device_t * drava_device = (drava_device_t *) team->desc.args;
    assert(drava_device);

    LOGGER_DEBUG("Starting thread %u on device %d", thread->tid, drava_device->device_global_id);

    sleep(1);
    LOGGER_FATAL("TODO: read on socket and progress Drava operations");

    return NULL;
}

int
drava_t::run(drava_routine_t routine)
{
    /* Fork a team of threads for each device */
    drava_device_t drava_devices[XKRT_DEVICES_MAX];

    for (device_global_id_t i = 0 ; i < this->runtime.get_ndevices() ; ++i)
    {
        /* save team information */
        drava_device_t * drava_device = drava_devices + i;
        drava_device->drava = this;
        drava_device->device_global_id = i;

        /* setup the team */
        team_t * team = &drava_device->team;
        team->desc.routine             = drava_main;
        team->desc.args                = drava_device;
        team->desc.nthreads            = 1;
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

        int err = driver->f_device_cpuset(this->runtime.topology, team->desc.binding.places_list, device->driver_id);
        if (err)
            LOGGER_FATAL("Fail to retrieve cpuset for device %u", i);

        /* spawn threads of the team */
        this->runtime.team_create(team);
    }

    /* Wait for all teams completion */
    for (device_global_id_t i = 0 ; i < this->runtime.get_ndevices() ; ++i)
        this->runtime.team_join(&drava_devices[i].team);

    return DRAVA_SUCCESS;
}

int
drava_t::deinit(void)
{
    this->runtime.deinit();
    return DRAVA_SUCCESS;
}
