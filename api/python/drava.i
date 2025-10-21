%module drava

%{
#include "drava/drava_c.h"
%}

/* Rename C for Python */
%rename(init)       drava_init;
%rename(run)        drava_run;
%rename(deinit)     drava_deinit;
%rename(routine_t)  drava_routine_t;
%rename(op_t)       drava_op_t;
%rename(rcode_t)    drava_rcode_t;

%include "drava/drava_c.h"
