%module drava

%{
# include "drava/drava_c.h"
void drava_register_routine_py(PyObject * cb);
void drava_listen_py(void);
%}

/* Automatically strip 'drava_' prefix from all symbols */
%rename("%(strip:[drava_])s") "";

%include "drava/drava_c.h"
%inline %{
void drava_register_routine_py(PyObject * cb);
void drava_listen_py(void);
%}
