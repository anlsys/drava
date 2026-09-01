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
void drava_register_eos_routine_py(PyObject * cb);
void drava_listen_py(void);
int drava_publish_py(PyObject *payload);
PyObject *drava_stats_snapshot_py(void);
int drava_stats_reset_py(void);
int drava_set_callback_batch(size_t batch_size);
int drava_set_callback_flush_timeout_ms(int timeout_ms);
int drava_set_callback_serialize(int enabled);
%}

/* High-level Python helpers */
%pythoncode %{
import inspect as _inspect


def _adapt_frame_routine(func):
    """Allow callbacks written as func(frames) or func(frames, base_index).

    The C trampoline always calls with (frames, base_index); older callbacks
    that accept a single argument are wrapped transparently.
    """
    try:
        params = _inspect.signature(func).parameters
        has_varargs = any(
            p.kind == _inspect.Parameter.VAR_POSITIONAL for p in params.values()
        )
        positional = [
            p for p in params.values()
            if p.kind in (
                _inspect.Parameter.POSITIONAL_ONLY,
                _inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
    except (TypeError, ValueError):
        return func

    if has_varargs or len(positional) >= 2:
        return func

    def _wrapper(frames, base_index):
        return func(frames)

    return _wrapper


def run(func, on_end_of_stream=None):
    """Run a Drava stage: init, register callback(s), listen, deinit.

    func: called as func(frames) or func(frames, base_index) per incoming batch.
          The EOS marker is handled by the runtime and never appears in frames.
    on_end_of_stream: optional callable invoked once as fn(expected_frames)
          after the stream drains (all data callbacks complete).

    EOS forwarding to the downstream stage is controlled by the pipeline
    config (egress.forward_eos); terminal stages set it to false.
    """
    rc = init()
    if rc != DRAVA_SUCCESS:
        raise RuntimeError(
            f"drava.init() failed with rc={rc}. "
            "If DRAVA_TRANSPORT=nats, rebuild Drava with NATS enabled."
        )
    try:
        register_routine_py(_adapt_frame_routine(func))
        if on_end_of_stream is not None:
            register_eos_routine_py(on_end_of_stream)
        rc = listen_py()
        if rc != DRAVA_SUCCESS:
            raise RuntimeError(f"drava.listen_py() failed with rc={rc}")
    finally:
        rc_deinit = deinit()
        if rc_deinit != DRAVA_SUCCESS:
            raise RuntimeError(f"drava.deinit() failed with rc={rc_deinit}")
%}
