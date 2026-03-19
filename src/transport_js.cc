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

#include <cstring>
#include <iostream>
#include <mutex>
#include <string>
#include <vector>

#include <nats/nats.h> // Core + JetStream API (libnats 3.12.x)

const char *nats_url =
        drava_env_get_str_default("NATS_URL", "nats://127.0.0.1:4222");
const char *stream_name = drava_env_get_str_default("DRAVA_STREAM", "FRAMES");
const char *subject_name =
        drava_env_get_str_default("DRAVA_SUBJECT", "frames.raw");
const char *durable_name =
        drava_env_get_str_default("DRAVA_DURABLE", "drava_consumer");
const char *output_stream_name =
        drava_env_get_str_default("DRAVA_OUTPUT_STREAM", "PREDICTIONS");
const char *output_subject_name =
        drava_env_get_str_default("DRAVA_OUTPUT_SUBJECT", "frames.stage1");

int drava_transport_nats_publish(drava_t *drava,
                                 const void *data,
                                 size_t data_len)
{
    (void)drava;
    if (data == NULL || data_len == 0)
        return DRAVA_EINVAL;

    static std::mutex out_mu;
    static bool initialized = false;
    static natsConnection *nc = nullptr;
    static jsCtx *js = nullptr;
    static std::string output_subject;

    std::lock_guard<std::mutex> lock(out_mu);
    if (!initialized) {
        natsStatus s;
        s = natsConnection_ConnectTo(&nc, nats_url);
        if (s != NATS_OK) {
            LOGGER_ERROR("NATS publish connect failed: %s",
                         natsStatus_GetText(s));
            return DRAVA_ERROR;
        }

        jsOptions jopts;
        jsOptions_Init(&jopts);
        s = natsConnection_JetStream(&js, nc, &jopts);
        if (s != NATS_OK) {
            LOGGER_ERROR("JetStream publish ctx failed: %s",
                         natsStatus_GetText(s));
            return DRAVA_ERROR;
        }

        jsStreamConfig sc;
        std::memset(&sc, 0, sizeof(sc));
        sc.Name = output_stream_name;
//        sc.Storage = js_FileStorage;
        sc.Storage = js_MemoryStorage;
        sc.MaxBytes = 1024LL * 1024LL * 1024LL;
        sc.Retention = js_LimitsPolicy;
        const char *subs[2] = {output_subject_name, nullptr};
        sc.Subjects = subs;
        sc.SubjectsLen = 1;
        jsStreamInfo *si = nullptr;
        (void)js_AddStream(&si, js, &sc, nullptr, nullptr);
        jsStreamInfo_Destroy(si);

        output_subject = output_subject_name;
        initialized = true;
        LOGGER_INFO("NATS publish output ready: url=%s stream=%s subject=%s",
                    nats_url, output_stream_name, output_subject.c_str());
    }

    jsPubAck *pa = nullptr;
    natsStatus s =
            js_Publish(&pa, js, output_subject.c_str(), (const void *)data,
                       (int)data_len, nullptr, nullptr);
    if (s != NATS_OK) {
        LOGGER_ERROR("NATS publish failed: %s", natsStatus_GetText(s));
        return DRAVA_ERROR;
    }
    jsPubAck_Destroy(pa);
    return DRAVA_SUCCESS;
}

int drava_transport_nats_main(drava_t *drava,
                              device_global_id_t device_global_id,
                              thread_t *thread)
{
    LOGGER_INFO("drava_transport_nats_main: device=%d tid=%u",
                (int)device_global_id, (unsigned)thread->tid);
    drava_device_t *drava_device = drava->devices + device_global_id;
    team_t *team = &drava_device->team;

    /* thread 0: subscribe + fetch from JetStream, spawn a task per message */
    if (thread->tid == 0) {
        LOGGER_INFO("JetStream trying to connect");
        int fetch_batch = drava_env_get_int_default("DRAVA_JS_FETCH_BATCH", 8);
        int fetch_timeout_ms =
                drava_env_get_int_default("DRAVA_FETCH_TIMEOUT_MS", 1000);
        int callback_flush_timeout_ms = drava->callback_flush_timeout_ms;

        LOGGER_INFO(
                "JetStream fetch config: batch=%d timeout_ms=%d callback_batch=%zu callback_flush_timeout_ms=%d",
                fetch_batch, fetch_timeout_ms,
                (size_t)drava->callback_batch_size, callback_flush_timeout_ms);

        natsStatus s;
        natsConnection *nc = nullptr;
        jsCtx *js = nullptr;
        natsSubscription *sub = nullptr;

        // Connect
        s = natsConnection_ConnectTo(&nc, nats_url);
        if (s != NATS_OK)
            LOGGER_FATAL("NATS connect failed: %s", natsStatus_GetText(s));

        // JetStream context
        jsOptions jopts;
        jsOptions_Init(&jopts);
        s = natsConnection_JetStream(&js, nc, &jopts);
        if (s != NATS_OK)
            LOGGER_FATAL("JetStream ctx failed: %s", natsStatus_GetText(s));

        // Ensure stream exists for the configured subject
        jsStreamConfig sc;
        std::memset(&sc, 0, sizeof(sc));
        sc.Name = stream_name;
        sc.Storage = js_MemoryStorage;
        sc.Retention = js_LimitsPolicy;
        const char *subs[] = {subject_name, nullptr};
        sc.Subjects = subs;
        sc.SubjectsLen = 1;

        jsStreamInfo *si = nullptr;
        (void)js_AddStream(&si, js, &sc, /*opts*/ nullptr, /*err*/ nullptr);
        jsStreamInfo_Destroy(si); // ok if it already existed

        // Ensure durable consumer filtered to SUBJECT (explicit acks)
        jsConsumerConfig cc;
        std::memset(&cc, 0, sizeof(cc));
        cc.Durable = durable_name;
        cc.AckPolicy = js_AckExplicit;
        cc.FilterSubject = subject_name;

        jsConsumerInfo *ci = nullptr;
        (void)js_AddConsumer(&ci, js, stream_name, &cc, /*opts*/ nullptr,
                             /*err*/ nullptr);
        jsConsumerInfo_Destroy(ci);

        // Pull subscribe
        s = js_PullSubscribe(&sub, js, subject_name, durable_name,
                             /*opts*/ nullptr, /*subOpts*/ nullptr,
                             /*err*/ nullptr);
        if (s != NATS_OK)
            LOGGER_FATAL("PullSubscribe failed: %s", natsStatus_GetText(s));

        LOGGER_INFO("JetStream ready: url=%s stream=%s subject=%s durable=%s",
                    nats_url, stream_name, subject_name, durable_name);

        // Fetch loop — pull batches and spawn Drava tasks
        struct pending_msg_t {
            std::string payload;
            uint64_t stream_seq;
            uint64_t consumer_seq;
            bool is_eos;
        };

        std::vector<pending_msg_t> pending;
        pending.reserve(drava->callback_batch_size);
        auto dispatch_batch = [&](std::vector<pending_msg_t> batch_msgs) {
            if (batch_msgs.empty())
                return;
            bool eos_in_batch = false;
            uint64_t first_stream_seq = 0;
            uint64_t last_stream_seq = 0;
            uint64_t first_consumer_seq = 0;
            uint64_t last_consumer_seq = 0;
            std::vector<std::string> batch_payloads;
            batch_payloads.reserve(batch_msgs.size());
            for (size_t bi = 0; bi < batch_msgs.size(); ++bi) {
                const pending_msg_t &msg = batch_msgs[bi];
                if (bi == 0) {
                    first_stream_seq = msg.stream_seq;
                    first_consumer_seq = msg.consumer_seq;
                }
                last_stream_seq = msg.stream_seq;
                last_consumer_seq = msg.consumer_seq;
                eos_in_batch = eos_in_batch || msg.is_eos;
                batch_payloads.push_back(msg.payload);
            }
            LOGGER_INFO(
                    "[transport-js] dispatch batch count=%zu eos=%d stream_seq=[%" PRIu64
                    ",%" PRIu64 "] consumer_seq=[%" PRIu64 ",%" PRIu64
                    "] stage=%s",
                    batch_payloads.size(), eos_in_batch ? 1 : 0,
                    first_stream_seq, last_stream_seq, first_consumer_seq,
                    last_consumer_seq,
                    drava_env_get_str_default("DRAVA_STAGE_NAME", "unknown"));
            if (drava->callback_serialize) {
                drava_callback_task_begin(drava);
                drava_dispatch_payload_batch(drava, device_global_id,
                                             batch_payloads);
                return;
            }
            drava_callback_task_begin(drava);
            drava->runtime.team_task_spawn(
                    team,
                    [drava, device_global_id,
                     batch_payloads = std::move(batch_payloads)](task_t *task) {
                        (void)task;
                        drava_dispatch_payload_batch(drava, device_global_id,
                                                     batch_payloads);
                    });
        };

        while (true) {
            natsMsgList list = {0};
            s = natsSubscription_Fetch(&list, sub, /*batch*/ fetch_batch,
                                       /*timeout ms*/ fetch_timeout_ms,
                                       /*err*/ nullptr);
            if (s == NATS_TIMEOUT) {
                if (!pending.empty() && callback_flush_timeout_ms > 0) {
                    std::vector<pending_msg_t> batch_payloads =
                            std::move(pending);
                    pending.clear();
                    pending.reserve(drava->callback_batch_size);
                    dispatch_batch(std::move(batch_payloads));
                }
                // idle; allow other threads to progress
                continue;
            }
            if (s != NATS_OK) {
                LOGGER_FATAL("Fetch error: %s", natsStatus_GetText(s));
            }

            for (int i = 0; i < list.Count; ++i) {
                natsMsg *msg = list.Msgs[i];

                // Optional: log JetStream metadata (seq numbers)
                jsMsgMetaData *md = nullptr;
                uint64_t stream_seq = 0;
                uint64_t consumer_seq = 0;
                if (natsMsg_GetMetaData(&md, msg) == NATS_OK && md != nullptr) {
                    stream_seq = (uint64_t)md->Sequence.Stream;
                    consumer_seq = (uint64_t)md->Sequence.Consumer;
                    LOGGER_DEBUG("[stream_seq=%" PRIu64 " consumer_seq=%" PRIu64
                                 "]",
                                 stream_seq, consumer_seq);
                    jsMsgMetaData_Destroy(md);
                }

                // Extract payload bytes
                std::string line(natsMsg_GetData(msg),
                                 (size_t)natsMsg_GetDataLength(msg));
                const bool is_eos =
                        drava_payload_is_eos(line.data(), line.size());
                if (is_eos) {
                    LOGGER_INFO("[transport-js] fetched eos stream_seq=%" PRIu64
                                " consumer_seq=%" PRIu64
                                " pending_before=%zu stage=%s",
                                stream_seq, consumer_seq, pending.size(),
                                drava_env_get_str_default("DRAVA_STAGE_NAME",
                                                          "unknown"));
                }
                pending.push_back(
                        {std::move(line), stream_seq, consumer_seq, is_eos});

                if (pending.size() >= drava->callback_batch_size || is_eos) {
                    std::vector<pending_msg_t> batch_payloads =
                            std::move(pending);
                    pending.clear();
                    pending.reserve(drava->callback_batch_size);
                    dispatch_batch(std::move(batch_payloads));
                }

                // Ack after enqueue to achieve at-least-once semantics
                natsStatus as = natsMsg_Ack(msg, /*opts*/ nullptr);
                if (as != NATS_OK)
                    LOGGER_WARN("Ack failed: %s", natsStatus_GetText(as));
            }

            // Destroy the fetched batch safely
            natsMsgList_Destroy(&list);
        }

        natsSubscription_Destroy(sub);
        jsCtx_Destroy(js);
        natsConnection_Destroy(nc);
        nats_Close();
    }

    /* other threads work-steal */
    drava->runtime.team_barrier<true>(team, thread);

    return DRAVA_SUCCESS;
}
