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
#include <inttypes.h>
#include <string>

struct drava_args_t {
    drava_t *drava;
    device_global_id_t device_global_id;
};

/* dispatcher: choose transport at runtime */
int drava_transport_main(drava_t *drava,
                         device_global_id_t device_global_id,
                         thread_t *thread)
{
    switch (drava->transport_type) {
    case DRAVA_TRANSPORT_SOCKET:
        LOGGER_DEBUG("Drava transport: Socket");
        return drava_transport_socket_main(drava, device_global_id, thread);

    case DRAVA_TRANSPORT_NATS:
#ifdef DRAVA_HAS_NATS
        LOGGER_DEBUG("Drava transport: NATS");
        return drava_transport_nats_main(drava, device_global_id, thread);
#else
        LOGGER_FATAL("NATS transport selected at runtime but not compiled in");
        return -1;
#endif

    default:
        LOGGER_FATAL("Unknown transport type %d", (int)drava->transport_type);
        return -1;
    }
}

/* The routine executed by each thread of each team of each device */
static void *drava_main(team_t *team, thread_t *thread)
{
    drava_args_t *args = (drava_args_t *)team->desc.args;
    assert(args);

    LOGGER_INFO("Starting thread %u on device %d", thread->tid,
                args->device_global_id);
    drava_transport_main(args->drava, args->device_global_id, thread);

    return NULL;
}

int drava_t::init(drava_transport_t transport_type)
{
    /* Remember which backend to use (socket vs NATS) */
    int cb = drava_env_get_int_default("DRAVA_INFER_BATCH", 128);
    this->transport_type = transport_type;
    this->runtime.init();
    this->frame_routine = NULL;
    this->frame_routine_user_data = NULL;
    this->callback_batch_size = (size_t)cb;
    this->next_batch_id.store(1);
    this->next_frame_id.store(1);
    this->stats_reset();
    return DRAVA_SUCCESS;
}

int drava_t::register_frame_routine(drava_frame_routine_t routine,
                                    void *user_data)
{
    this->frame_routine = routine;
    this->frame_routine_user_data = user_data;
    return DRAVA_SUCCESS;
}

int drava_t::listen(void)
{
    /* Fork a team of threads for each device */
    drava_args_t args[XKRT_DEVICES_MAX];

    for (device_global_id_t i = 0; i < this->runtime.get_ndevices(); ++i) {
        if (i == HOST_DEVICE_GLOBAL_ID)
            continue;

        /* save team information */
        drava_args_t *arg = args + i;
        arg->drava = this;
        arg->device_global_id = i;

        /* drava device */
        drava_device_t *drava_device = this->devices + i;

        /* setup the team */
        team_t *team = &drava_device->team;
        team->desc.routine = drava_main;
        team->desc.args = arg;
        team->desc.nthreads = drava_env_get_int_default("DRAVA_THREADS", 4);
        LOGGER_INFO("team->desc.nthreads: %d", team->desc.nthreads);

        team->desc.master_is_member = false;
        team->desc.binding.mode = XKRT_TEAM_BINDING_MODE_COMPACT;
        team->desc.binding.places = XKRT_TEAM_BINDING_PLACES_EXPLICIT;
        team->desc.binding.nplaces = 1;
        team->desc.binding.places_list = &drava_device->places_list;

        /* TODO: XKRT API is quite ugly */
        /* retrieve the places of that device */
        device_t *device = this->runtime.device_get(i);
        assert(device);

        driver_t *driver = this->runtime.driver_get(device->driver_type);
        assert(driver);

        int err = driver->f_device_cpuset(this->runtime.topology,
                                          team->desc.binding.places_list,
                                          device->driver_id);
        if (err)
            LOGGER_FATAL("Fail to retrieve cpuset for device %u", i);

        /* spawn threads of the team */
        this->runtime.team_create(team);
    }

    /* Wait for all teams completion */
    for (device_global_id_t i = 0; i < this->runtime.get_ndevices(); ++i)
        this->runtime.team_join(&this->devices[i].team);
    LOGGER_INFO("drava.listen: enter, ndevices=%u",
                (unsigned)this->runtime.get_ndevices());
    return DRAVA_SUCCESS;
}

int drava_t::deinit(void)
{
    this->runtime.deinit();
    return DRAVA_SUCCESS;
}

int drava_t::publish(const void *data, size_t data_len)
{
    if (data == NULL || data_len == 0)
        return DRAVA_EINVAL;

    int rc = DRAVA_EINVAL;
    switch (this->transport_type) {
    case DRAVA_TRANSPORT_SOCKET:
        rc = drava_transport_socket_publish(this, data, data_len);
        break;

    case DRAVA_TRANSPORT_NATS:
#ifdef DRAVA_HAS_NATS
        rc = drava_transport_nats_publish(this, data, data_len);
        break;
#else
        LOGGER_FATAL("NATS transport selected at runtime but not compiled in");
        return DRAVA_ENOTSUP;
#endif

    default:
        LOGGER_FATAL("Unknown transport type %d", (int)this->transport_type);
        return DRAVA_EINVAL;
    }

    if (rc == DRAVA_SUCCESS) {
        drava_stats_record_tx(this, data_len);
        const uint64_t recv_ts_ns = drava_callback_context_recv_ts_ns();
        if (recv_ts_ns > 0) {
            const uint64_t now_ns = drava_monotonic_ns();
            if (now_ns >= recv_ts_ns)
                drava_stats_record_stage_latency_ns(this, now_ns - recv_ts_ns);
        }
        if (drava_payload_is_eos(data, data_len))
            drava_stats_log_snapshot(this, "tx_eos");
    }
    return rc;
}

int drava_t::log(const int verbose_level, const char *msg)
{
    LOGGER_PRINT(verbose_level, "%s", msg);
    return DRAVA_SUCCESS;
}

int drava_t::stats_snapshot(drava_stats_t *out_stats) const
{
    if (out_stats == NULL)
        return DRAVA_EINVAL;
    out_stats->rx_msgs = this->rx_msgs.load();
    out_stats->rx_frames = this->rx_frames.load();
    out_stats->rx_bytes = this->rx_bytes.load();
    out_stats->tx_msgs = this->tx_msgs.load();
    out_stats->tx_bytes = this->tx_bytes.load();
    out_stats->callback_batches = this->callback_batches.load();
    out_stats->callback_frames = this->callback_frames.load();
    out_stats->callback_ns_sum = this->callback_ns_sum.load();
    out_stats->callback_ns_max = this->callback_ns_max.load();
    out_stats->stage_latency_samples = this->stage_latency_samples.load();
    out_stats->stage_latency_ns_sum = this->stage_latency_ns_sum.load();
    out_stats->stage_latency_ns_max = this->stage_latency_ns_max.load();
    out_stats->rx_first_ns = this->rx_first_ns.load();
    out_stats->rx_last_ns = this->rx_last_ns.load();
    out_stats->tx_first_ns = this->tx_first_ns.load();
    out_stats->tx_last_ns = this->tx_last_ns.load();
    return DRAVA_SUCCESS;
}

int drava_t::stats_reset(void)
{
    this->rx_msgs.store(0);
    this->rx_frames.store(0);
    this->rx_bytes.store(0);
    this->tx_msgs.store(0);
    this->tx_bytes.store(0);
    this->callback_batches.store(0);
    this->callback_frames.store(0);
    this->callback_ns_sum.store(0);
    this->callback_ns_max.store(0);
    this->stage_latency_samples.store(0);
    this->stage_latency_ns_sum.store(0);
    this->stage_latency_ns_max.store(0);
    this->rx_first_ns.store(0);
    this->rx_last_ns.store(0);
    this->tx_first_ns.store(0);
    this->tx_last_ns.store(0);
    return DRAVA_SUCCESS;
}
