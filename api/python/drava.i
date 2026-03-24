%module drava

%{
# define SWIGPYTHON_NOGIL 1
#include "drava/drava_c.h"
%}

/* Automatically strip 'drava_' prefix from all symbols */
%rename("%(strip:[drava_])s") "";

%include "drava/drava_c.h"

/* Python-specific wrapper functions */
%inline %{
/*ToDo: keep one function*/
void drava_register_routine_py(PyObject * cb);
void drava_listen_py(void);
int drava_publish_py(PyObject *payload);
PyObject *drava_stats_snapshot_py(void);
int drava_stats_reset_py(void);
int drava_set_callback_batch(size_t batch_size);
int drava_set_callback_flush_timeout_ms(int timeout_ms);
int drava_set_callback_serialize(int enabled);
%}
