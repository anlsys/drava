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
%}
