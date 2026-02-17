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

    PyObject *args = PyTuple_New(1);
    PyTuple_SetItem(args, 0, py_frames); /* steals py_frames */
    PyObject *ret = PyObject_CallObject(g_routine, args);
    Py_DECREF(args);
    Py_XDECREF(ret);

#ifndef PY_NO_GIL
    PyGILState_Release(gstate);
#endif /* PY_NO_GIL */

    return NULL;
}

/* Called from Python to register the routine */
void drava_register_routine_py(PyObject *cb)
{
    Py_XINCREF(cb);
    Py_XDECREF(g_routine);
    g_routine = cb;
    drava_register_frame_routine(drava_frame_routine_trampoline, NULL);
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
