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

static std::once_flag g_publish_init_once;
static int g_publish_init_rc = DRAVA_SUCCESS;
static natsConnection *g_publish_nc = nullptr;
static jsCtx *g_publish_js = nullptr;
static std::string g_publish_subject;

static const char *drava_nats_status_text(natsStatus status)
{
   const char *text = natsStatus_GetText(status);
   return text != nullptr ? text : "unknown";
}

static natsStatus
drava_nats_ensure_stream(jsCtx *js, const char *name, const char *subject)
{
   jsStreamConfig sc;
   std::memset(&sc, 0, sizeof(sc));
   sc.Name = name;
   sc.Storage = js_MemoryStorage;
   sc.Retention = js_LimitsPolicy;
   const char *subs[2] = {subject, nullptr};
   sc.Subjects = subs;
   sc.SubjectsLen = 1;

   jsStreamInfo *si = nullptr;
   jsErrCode js_err = (jsErrCode)0;
   natsStatus s = js_AddStream(&si, js, &sc, nullptr, &js_err);
   if (s != NATS_OK) {
       LOGGER_WARN(
               "JetStream add stream returned: stream=%s subject=%s nats_status=%s js_error=%u",
               name, subject, drava_nats_status_text(s), (unsigned)js_err);
   } else {
       LOGGER_INFO("JetStream stream ready: stream=%s subject=%s", name,
                   subject);
   }
   jsStreamInfo_Destroy(si);
   return s;
}

int drava_transport_nats_publish(drava_t *drava,
                                const void *data,
                                size_t data_len)
{
   if (data == NULL || data_len == 0)
       return DRAVA_EINVAL;

   std::call_once(g_publish_init_once, [&]() {
       natsStatus s;
       s = natsConnection_ConnectTo(&g_publish_nc, drava->nats_url.c_str());
       if (s != NATS_OK) {
           LOGGER_ERROR("NATS publish connect failed: %s",
                        natsStatus_GetText(s));
           g_publish_init_rc = DRAVA_ERROR;
           return;
       }

       jsOptions jopts;
       jsOptions_Init(&jopts);
       s = natsConnection_JetStream(&g_publish_js, g_publish_nc, &jopts);
       if (s != NATS_OK) {
           LOGGER_ERROR("JetStream publish ctx failed: %s",
                        natsStatus_GetText(s));
           g_publish_init_rc = DRAVA_ERROR;
           return;
       }

       drava_nats_ensure_stream(g_publish_js, drava->egress_cfg.stream.c_str(),
                                drava->egress_cfg.subject.c_str());

       g_publish_subject = drava->egress_cfg.subject;
       LOGGER_INFO("NATS publish output ready: url=%s stream=%s subject=%s",
                   drava->nats_url.c_str(), drava->egress_cfg.stream.c_str(),
                   g_publish_subject.c_str());
   });

   if (g_publish_init_rc != DRAVA_SUCCESS || g_publish_js == nullptr)
       return DRAVA_ERROR;

   natsStatus s;
   const bool is_eos = drava_payload_is_eos(data, data_len);
   if (is_eos) {
       s = js_PublishAsync(g_publish_js, g_publish_subject.c_str(),
                           (const void *)data, (int)data_len, nullptr);
       if (s != NATS_OK) {
           LOGGER_ERROR("NATS async publish failed: %s",
                        natsStatus_GetText(s));
           return DRAVA_ERROR;
       }
       jsPubOptions js_pub_opts;
       jsPubOptions_Init(&js_pub_opts);
       js_pub_opts.MaxWait = drava->nats_async_drain_timeout_ms;
       s = js_PublishAsyncComplete(g_publish_js, &js_pub_opts);
   } else {
       s = js_PublishAsync(g_publish_js, g_publish_subject.c_str(),
                           (const void *)data, (int)data_len, nullptr);
   }
   if (s != NATS_OK) {
       LOGGER_ERROR("NATS async publish failed: %s", natsStatus_GetText(s));
       return DRAVA_ERROR;
   }
   return DRAVA_SUCCESS;
}

int drava_transport_nats_shutdown(drava_t *drava)
{
   (void)drava;
   if (g_publish_js != nullptr) {
       jsPubOptions js_pub_opts;
       jsPubOptions_Init(&js_pub_opts);
       js_pub_opts.MaxWait = drava->nats_async_drain_timeout_ms;
       natsStatus s = js_PublishAsyncComplete(g_publish_js, &js_pub_opts);
       if (s != NATS_OK) {
           LOGGER_WARN("NATS async drain failed during shutdown: %s",
                       natsStatus_GetText(s));
       }
       jsCtx_Destroy(g_publish_js);
       g_publish_js = nullptr;
   }
   if (g_publish_nc != nullptr) {
       natsConnection_Destroy(g_publish_nc);
       g_publish_nc = nullptr;
   }
   nats_Close();
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
       int fetch_batch = drava->ingress_cfg.fetch_batch;
       int fetch_timeout_ms = drava->ingress_cfg.fetch_timeout_ms;
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
       s = natsConnection_ConnectTo(&nc, drava->nats_url.c_str());
       if (s != NATS_OK)
           LOGGER_FATAL("NATS connect failed: url=%s stage=%s err=%s",
                        drava->nats_url.c_str(), drava->stage_name.c_str(),
                        drava_nats_status_text(s));
       LOGGER_INFO("NATS connected: url=%s stage=%s",
                   drava->nats_url.c_str(), drava->stage_name.c_str());

       // JetStream context
       jsOptions jopts;
       jsOptions_Init(&jopts);
       s = natsConnection_JetStream(&js, nc, &jopts);
       if (s != NATS_OK)
           LOGGER_FATAL("JetStream ctx failed: url=%s stage=%s err=%s",
                        drava->nats_url.c_str(), drava->stage_name.c_str(),
                        drava_nats_status_text(s));
       LOGGER_INFO("JetStream context ready: url=%s stage=%s",
                   drava->nats_url.c_str(), drava->stage_name.c_str());

       // Ensure stream exists for the configured subject
       drava_nats_ensure_stream(js, drava->ingress_cfg.stream.c_str(),
                                drava->ingress_cfg.subject.c_str());

       // Ensure durable consumer filtered to SUBJECT (explicit acks)
       jsConsumerConfig cc;
       std::memset(&cc, 0, sizeof(cc));
       cc.Durable = drava->ingress_cfg.durable.c_str();
       cc.AckPolicy = js_AckExplicit;
       cc.FilterSubject = drava->ingress_cfg.subject.c_str();

       jsConsumerInfo *ci = nullptr;
       jsErrCode consumer_js_err = (jsErrCode)0;
       s = js_AddConsumer(&ci, js, drava->ingress_cfg.stream.c_str(), &cc,
                          /*opts*/ nullptr, &consumer_js_err);
       if (s != NATS_OK) {
           LOGGER_WARN(
                   "JetStream add consumer returned: stream=%s subject=%s durable=%s stage=%s nats_status=%s js_error=%u",
                   drava->ingress_cfg.stream.c_str(),
                   drava->ingress_cfg.subject.c_str(),
                   drava->ingress_cfg.durable.c_str(),
                   drava->stage_name.c_str(), drava_nats_status_text(s),
                   (unsigned)consumer_js_err);
       } else {
           LOGGER_INFO(
                   "JetStream consumer ready: stream=%s subject=%s durable=%s stage=%s",
                   drava->ingress_cfg.stream.c_str(),
                   drava->ingress_cfg.subject.c_str(),
                   drava->ingress_cfg.durable.c_str(),
                   drava->stage_name.c_str());
       }
       jsConsumerInfo_Destroy(ci);

       // Pull subscribe
       LOGGER_INFO(
               "JetStream pull subscribe: stream=%s subject=%s durable=%s stage=%s",
               drava->ingress_cfg.stream.c_str(),
               drava->ingress_cfg.subject.c_str(),
               drava->ingress_cfg.durable.c_str(),
               drava->stage_name.c_str());
       s = js_PullSubscribe(&sub, js, drava->ingress_cfg.subject.c_str(),
                            drava->ingress_cfg.durable.c_str(),
                            /*opts*/ nullptr, /*subOpts*/ nullptr,
                            /*err*/ nullptr);
       if (s != NATS_OK)
           LOGGER_FATAL(
                   "PullSubscribe failed: stream=%s subject=%s durable=%s stage=%s err=%s",
                   drava->ingress_cfg.stream.c_str(),
                   drava->ingress_cfg.subject.c_str(),
                   drava->ingress_cfg.durable.c_str(),
                   drava->stage_name.c_str(), drava_nats_status_text(s));

       LOGGER_INFO("JetStream ready: url=%s stream=%s subject=%s durable=%s",
                   drava->nats_url.c_str(), drava->ingress_cfg.stream.c_str(),
                   drava->ingress_cfg.subject.c_str(),
                   drava->ingress_cfg.durable.c_str());

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
                   last_consumer_seq, drava->stage_name.c_str());
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
                               drava->stage_name.c_str());
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
