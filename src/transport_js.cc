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
#include <string>
#include <vector>

#include <nats/nats.h> // Core + JetStream API (libnats 3.12.x)

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
        const char *NATS_URL =
                drava_env_get_str_default("NATS_URL", "nats://127.0.0.1:4222");
        const char *STREAM =
                drava_env_get_str_default("DRAVA_STREAM", "FRAMES");
        const char *SUBJECT =
                drava_env_get_str_default("DRAVA_SUBJECT", "frames.raw");
        const char *DURABLE =
                drava_env_get_str_default("DRAVA_DURABLE", "drava_consumer");
        int fetch_batch = drava_env_get_int_default("DRAVA_JS_FETCH_BATCH", 8);
        int fetch_timeout_ms =
                drava_env_get_int_default("DRAVA_FETCH_TIMEOUT_MS", 1000);

        LOGGER_INFO(
                "JetStream fetch config: batch=%d timeout_ms=%d callback_batch=%zu",
                fetch_batch, fetch_timeout_ms,
                (size_t)drava->callback_batch_size);

        natsStatus s;
        natsConnection *nc = nullptr;
        jsCtx *js = nullptr;
        natsSubscription *sub = nullptr;

        // Connect
        s = natsConnection_ConnectTo(&nc, NATS_URL);
        if (s != NATS_OK)
            LOGGER_FATAL("NATS connect failed: %s", natsStatus_GetText(s));

        // JetStream context
        jsOptions jopts;
        jsOptions_Init(&jopts);
        s = natsConnection_JetStream(&js, nc, &jopts);
        if (s != NATS_OK)
            LOGGER_FATAL("JetStream ctx failed: %s", natsStatus_GetText(s));

        // Ensure stream exists (subjects must include frames.raw)
        jsStreamConfig sc;
        std::memset(&sc, 0, sizeof(sc));
        sc.Name = STREAM;
        sc.Storage = js_MemoryStorage; // js_FileStorage -> persisted by server to -sd dir
        sc.Retention = js_LimitsPolicy;
        const char *subs[] = {"frames.*", nullptr};
        sc.Subjects = subs;
        sc.SubjectsLen = 1;

        jsStreamInfo *si = nullptr;
        (void)js_AddStream(&si, js, &sc, /*opts*/ nullptr, /*err*/ nullptr);
        jsStreamInfo_Destroy(si); // ok if it already existed

        // Ensure durable consumer filtered to SUBJECT (explicit acks)
        jsConsumerConfig cc;
        std::memset(&cc, 0, sizeof(cc));
        cc.Durable = DURABLE;
        cc.AckPolicy = js_AckExplicit;
        cc.FilterSubject = SUBJECT;

        jsConsumerInfo *ci = nullptr;
        (void)js_AddConsumer(&ci, js, STREAM, &cc, /*opts*/ nullptr,
                             /*err*/ nullptr);
        jsConsumerInfo_Destroy(ci);

        // Pull subscribe
        s = js_PullSubscribe(&sub, js, SUBJECT, STREAM,
                             /*opts*/ nullptr, /*subOpts*/ nullptr,
                             /*err*/ nullptr);
        if (s != NATS_OK)
            LOGGER_FATAL("PullSubscribe failed: %s", natsStatus_GetText(s));

        LOGGER_INFO("JetStream ready: url=%s stream=%s subject=%s durable=%s",
                    NATS_URL, STREAM, SUBJECT, DURABLE);

        // Fetch loop — pull batches and spawn Drava tasks
        std::vector<std::string> pending;
        pending.reserve(drava->callback_batch_size);

        while (true) {
            natsMsgList list = {0};
            s = natsSubscription_Fetch(&list, sub, /*batch*/ fetch_batch,
                                       /*timeout ms*/ fetch_timeout_ms,
                                       /*err*/ nullptr);
            if (s == NATS_TIMEOUT) {
                if (!pending.empty()) {
                    std::vector<std::string> batch_payloads =
                            std::move(pending);
                    pending.clear();
                    pending.reserve(drava->callback_batch_size);
                    drava->runtime.team_task_spawn(
                            team, [drava, device_global_id,
                                   batch_payloads = std::move(batch_payloads)](
                                          task_t *task) {
                                (void)task;
                                drava_dispatch_payload_batch(drava,
                                                             device_global_id,
                                                             batch_payloads);
                            });
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
                if (natsMsg_GetMetaData(&md, msg) == NATS_OK && md != nullptr) {
                    LOGGER_DEBUG("[stream_seq=%" PRIu64 " consumer_seq=%" PRIu64
                                 "]",
                                 (uint64_t)md->Sequence.Stream,
                                 (uint64_t)md->Sequence.Consumer);
                    jsMsgMetaData_Destroy(md);
                }

                // Extract payload bytes
                std::string line(natsMsg_GetData(msg),
                                 (size_t)natsMsg_GetDataLength(msg));
                pending.push_back(std::move(line));

                if (pending.size() >= drava->callback_batch_size) {
                    std::vector<std::string> batch_payloads =
                            std::move(pending);
                    pending.clear();
                    pending.reserve(drava->callback_batch_size);

                    drava->runtime.team_task_spawn(
                            team, [drava, device_global_id,
                                   batch_payloads = std::move(batch_payloads)](
                                          task_t *task) {
                                (void)task;
                                drava_dispatch_payload_batch(drava,
                                                             device_global_id,
                                                             batch_payloads);
                            });
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
