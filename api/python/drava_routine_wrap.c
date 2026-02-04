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

static void *drava_routine_trampoline(const char *s)
{
    if (!g_routine)
        return NULL;

    PyGILState_STATE gstate = PyGILState_Ensure();

    /* Step 1: Create Python string from C string */
    PyObject *py_arg = PyUnicode_FromString(s);

    /* Step 2: Create a tuple to hold the argument(s) */
    PyObject *args = PyTuple_New(1);
    PyTuple_SetItem(args, 0, py_arg); // Steals a reference to py_arg

    /* Step 3: call */
    PyObject_CallObject(g_routine, args);

    /* Step 4: Cleanup */
    Py_DECREF(args);

    PyGILState_Release(gstate);

    return NULL;
}

/* Called from Python to register the routine */
void drava_register_routine_py(PyObject *cb)
{
    Py_XINCREF(cb);
    Py_XDECREF(g_routine);
    g_routine = cb;
    drava_register_routine(drava_routine_trampoline);
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
