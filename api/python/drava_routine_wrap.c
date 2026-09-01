/*******************************************************************************
 * Copyright 2025 UChicago Argonne, LLC.
 * (c.f. AUTHORS, LICENSE)
 *
 * This file is part of the drava project.
 * For more info, see https://github.com/anlsys/drava
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *****************************************************************************/

#include <Python.h>
#include <drava/drava_c.h>

/* Python routines */
static PyObject *g_routine = NULL;
static PyObject *g_eos_routine = NULL;

static void *drava_frame_routine_trampoline(const drava_frame_batch_t *batch,
                                            void *user_data)
{
    (void)user_data;
    if (!g_routine)
        return NULL;

#ifndef PY_NO_GIL
    PyGILState_STATE gstate = PyGILState_Ensure();
#endif /* PY_NO_GIL */

    const uint32_t count = batch ? batch->count : 0;
    const unsigned long long base_index =
            batch ? (unsigned long long)batch->base_index : 0ULL;
    PyObject *py_frames = PyList_New((Py_ssize_t)count);
    if (!py_frames) {
#ifndef PY_NO_GIL
        PyGILState_Release(gstate);
#endif /* PY_NO_GIL */
        return NULL;
    }

    for (uint32_t i = 0; i < count; ++i) {
        const drava_frame_t *f = &batch->frames[i];
        PyObject *payload = PyBytes_FromStringAndSize((const char *)f->data,
                                                      (Py_ssize_t)f->data_len);
        if (!payload) {
            payload = PyBytes_FromStringAndSize("", 0);
            if (!payload)
                continue;
        }
        PyList_SetItem(py_frames, (Py_ssize_t)i, payload); /* steals payload */
    }

    /* Call func(frames, base_index). The Python-side run()/register wrapper
     * adapts single-argument callbacks, so the trampoline always passes both. */
    PyObject *args = PyTuple_New(2);
    PyTuple_SetItem(args, 0, py_frames); /* steals py_frames */
    PyTuple_SetItem(args, 1, PyLong_FromUnsignedLongLong(base_index));
    PyObject *ret = PyObject_CallObject(g_routine, args);
    Py_DECREF(args);
    if (ret == NULL) {
        PyErr_Print();
    } else {
        Py_DECREF(ret);
    }

#ifndef PY_NO_GIL
    PyGILState_Release(gstate);
#endif /* PY_NO_GIL */

    return NULL;
}

static void drava_eos_routine_trampoline(uint64_t expected_frames,
                                         void *user_data)
{
    (void)user_data;
    if (!g_eos_routine)
        return;

#ifndef PY_NO_GIL
    PyGILState_STATE gstate = PyGILState_Ensure();
#endif /* PY_NO_GIL */

    PyObject *args = PyTuple_New(1);
    PyTuple_SetItem(args, 0,
                    PyLong_FromUnsignedLongLong(
                            (unsigned long long)expected_frames));
    PyObject *ret = PyObject_CallObject(g_eos_routine, args);
    Py_DECREF(args);
    if (ret == NULL) {
        PyErr_Print();
    } else {
        Py_DECREF(ret);
    }

#ifndef PY_NO_GIL
    PyGILState_Release(gstate);
#endif /* PY_NO_GIL */
}

/* Called from Python to register the routine */
void drava_register_routine_py(PyObject *cb)
{
    Py_XINCREF(cb);
    Py_XDECREF(g_routine);
    g_routine = cb;
    drava_register_frame_routine(drava_frame_routine_trampoline, NULL);
}

/* Called from Python to register the end-of-stream routine */
void drava_register_eos_routine_py(PyObject *cb)
{
    Py_XINCREF(cb);
    Py_XDECREF(g_eos_routine);
    g_eos_routine = cb;
    drava_register_eos_routine(drava_eos_routine_trampoline, NULL);
}

/* Listen from python */
int drava_listen_py(void)
{
    /* release the GIL and save thread state */
    PyThreadState *_save = PyEval_SaveThread(); /* releases GIL */

    /* Other threads may now acquire the GIL from routines */
    int rc = drava_listen();

    /* restore the GIL for the current thread */
    PyEval_RestoreThread(_save);

    return rc;
}

int drava_publish_py(PyObject *payload)
{
    if (payload == NULL)
        return DRAVA_EINVAL;

    Py_buffer view;
    if (PyObject_GetBuffer(payload, &view, PyBUF_CONTIG_RO) != 0)
        return DRAVA_EINVAL;

    int rc = drava_publish(view.buf, (size_t)view.len);
    PyBuffer_Release(&view);
    return rc;
}

PyObject *drava_stats_snapshot_py(void)
{
    drava_stats_t s;
    int rc = drava_stats_snapshot(&s);
    if (rc != DRAVA_SUCCESS)
        return Py_BuildValue("{s:i}", "rc", rc);

    return Py_BuildValue(
            "{s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:i}",
            "rx_msgs", (unsigned long long)s.rx_msgs, "rx_items",
            (unsigned long long)s.rx_items, "rx_bytes",
            (unsigned long long)s.rx_bytes, "tx_msgs",
            (unsigned long long)s.tx_msgs, "tx_bytes",
            (unsigned long long)s.tx_bytes, "callback_batches",
            (unsigned long long)s.callback_batches, "callback_ns_sum",
            (unsigned long long)s.callback_ns_sum, "callback_ns_max",
            (unsigned long long)s.callback_ns_max, "stage_latency_samples",
            (unsigned long long)s.stage_latency_samples, "stage_latency_ns_sum",
            (unsigned long long)s.stage_latency_ns_sum, "stage_latency_ns_max",
            (unsigned long long)s.stage_latency_ns_max, "first_rx_ns",
            (unsigned long long)s.first_rx_ns, "last_stage_ns",
            (unsigned long long)s.last_stage_ns, "publish_ns_sum",
            (unsigned long long)s.publish_ns_sum, "publish_ns_max",
            (unsigned long long)s.publish_ns_max, "rc", rc);
}

int drava_stats_reset_py(void)
{
    return drava_stats_reset();
}
