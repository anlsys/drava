%module drava

%{
#include "drava/drava_c.h"
%}

/* Automatically strip 'drava_' prefix from all symbols */
%rename("%(strip:[drava_])s") "";

%include "drava/drava_c.h"
