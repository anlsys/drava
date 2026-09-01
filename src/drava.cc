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

int drava_t::init(void)
{
    int rc = drava_apply_stage_config(this);
    if (rc != DRAVA_SUCCESS)
        return rc;
    this->runtime.init();
    this->frame_routine = NULL;
    this->frame_routine_user_data = NULL;
    this->eos_routine = NULL;
    this->eos_routine_user_data = NULL;
    this->eos_payload.clear();
    this->eos_expected_frames = 0;
    this->eos_seen = false;
    this->eos_finalized = false;
    this->forward_eos = this->egress_cfg.forward_eos;
    this->next_data_index.store(0);
    this->callback_batch_size = this->runtime_cfg.callback_batch;
    this->callback_flush_timeout_ms =
            this->runtime_cfg.callback_flush_timeout_ms;
    this->callback_serialize = this->runtime_cfg.callback_serialize;
    this->next_batch_id.store(1);
    this->next_frame_id.store(1);
    if (this->energy_sampler == NULL)
        this->energy_sampler = drava_energy_create();
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

int drava_t::register_eos_routine(drava_eos_routine_t routine, void *user_data)
{
    this->eos_routine = routine;
    this->eos_routine_user_data = user_data;
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
        team->desc.nthreads = this->runtime_cfg.threads;
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
#ifdef DRAVA_HAS_NATS
    if (this->transport_type == DRAVA_TRANSPORT_NATS)
        (void)drava_transport_nats_shutdown(this);
#endif
    if (this->energy_sampler != NULL) {
        drava_energy_destroy(this->energy_sampler);
        this->energy_sampler = NULL;
    }
    this->runtime.deinit();
    return DRAVA_SUCCESS;
}

int drava_t::publish(const void *data, size_t data_len)
{
    if (data == NULL || data_len == 0)
        return DRAVA_EINVAL;

    const uint64_t publish_t0 = drava_monotonic_ns();
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
        const uint64_t publish_t1 = drava_monotonic_ns();
        drava_stats_record_tx(this, data_len, publish_t1 - publish_t0,
                              publish_t1);
        const uint64_t recv_ts_ns = drava_callback_context_recv_ts_ns();
        if (recv_ts_ns > 0) {
            if (publish_t1 >= recv_ts_ns)
                drava_stats_record_stage_latency_ns(this,
                                                    publish_t1 - recv_ts_ns);
        }
        if (drava_payload_is_eos(data, data_len)) {
            this->pending_tx_eos_snapshot.store(1);
            if (this->pending_callback_tasks.load() == 0 &&
                this->pending_tx_eos_snapshot.exchange(0) != 0) {
                drava_stats_log_snapshot(this, "tx_eos");
            }
        }
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
    out_stats->rx_items = this->rx_items.load();
    out_stats->rx_bytes = this->rx_bytes.load();
    out_stats->tx_msgs = this->tx_msgs.load();
    out_stats->tx_bytes = this->tx_bytes.load();
    out_stats->callback_batches = this->callback_batches.load();
    out_stats->callback_ns_sum = this->callback_ns_sum.load();
    out_stats->callback_ns_max = this->callback_ns_max.load();
    out_stats->publish_ns_sum = this->publish_ns_sum.load();
    out_stats->publish_ns_max = this->publish_ns_max.load();
    out_stats->stage_latency_samples = this->stage_latency_samples.load();
    out_stats->stage_latency_ns_sum = this->stage_latency_ns_sum.load();
    out_stats->stage_latency_ns_max = this->stage_latency_ns_max.load();
    out_stats->first_rx_ns = this->first_rx_ns.load();
    out_stats->last_stage_ns = this->last_stage_ns.load();
    return DRAVA_SUCCESS;
}

int drava_t::stats_reset(void)
{
    this->rx_msgs.store(0);
    this->rx_items.store(0);
    this->rx_bytes.store(0);
    this->tx_msgs.store(0);
    this->tx_bytes.store(0);
    this->callback_batches.store(0);
    this->callback_ns_sum.store(0);
    this->callback_ns_max.store(0);
    this->publish_ns_sum.store(0);
    this->publish_ns_max.store(0);
    this->stage_latency_samples.store(0);
    this->stage_latency_ns_sum.store(0);
    this->stage_latency_ns_max.store(0);
    this->first_rx_ns.store(0);
    this->last_stage_ns.store(0);
    this->pending_callback_tasks.store(0);
    this->pending_rx_eos_snapshot.store(0);
    this->pending_tx_eos_snapshot.store(0);
    return DRAVA_SUCCESS;
}

int drava_t::set_callback_batch(size_t batch_size)
{
    if (batch_size == 0)
        return DRAVA_EINVAL;
    this->callback_batch_size = batch_size;
    return DRAVA_SUCCESS;
}

int drava_t::set_callback_flush_timeout_ms(int timeout_ms)
{
    if (timeout_ms < 0)
        return DRAVA_EINVAL;
    this->callback_flush_timeout_ms = timeout_ms;
    return DRAVA_SUCCESS;
}

int drava_t::set_callback_serialize(bool enabled)
{
    this->callback_serialize = enabled;
    return DRAVA_SUCCESS;
}

int drava_t::set_forward_eos(bool enabled)
{
    this->forward_eos = enabled;
    return DRAVA_SUCCESS;
}
