from typing import Dict, Tuple
from ..events import Event
from ..fsm import State, Handler
from .. import handlers as H

# Flat hash table of (Event, State) → Handler
TRANSITIONS: Dict[Tuple[Event, State], Handler] = {
    # -------- core state transitions --------
    (Event.INIT_EVT, State.INIT): H.on_init,
    (Event.REG_WRITE_START, State.WAITING_FOR_INPUT): H.on_start_computation,
    (Event.COMPUTE_DONE, State.RUN): H.on_compute_done,
    (Event.REGREAD, State.WAITING_ON_OUTPUT): H.on_reg_read_output,
    (Event.MEMREAD, State.OUTPUT): H.on_mem_read_output,

    # -------- side effects (no state change) --------
    (Event.MEMWRITE, State.INIT): H.on_mem_write,
    (Event.MEMWRITE, State.WAITING_FOR_INPUT): H.on_mem_write,
    (Event.MEMWRITE, State.RUN): H.on_mem_write,
    (Event.MEMWRITE, State.WAITING_ON_OUTPUT): H.on_mem_write,
    (Event.MEMWRITE, State.OUTPUT): H.on_mem_write,

    (Event.MEMREAD, State.INIT): H.on_mem_read,
    (Event.MEMREAD, State.WAITING_FOR_INPUT): H.on_mem_read,
    (Event.MEMREAD, State.RUN): H.on_mem_read,
    (Event.MEMREAD, State.WAITING_ON_OUTPUT): H.on_mem_read,

    (Event.REGREAD, State.INIT): H.on_reg_read,
    (Event.REGREAD, State.WAITING_FOR_INPUT): H.on_reg_read,
    (Event.REGREAD, State.RUN): H.on_reg_read,
    (Event.REGREAD, State.OUTPUT): H.on_reg_read,

    (Event.REG_WRITE_NOTIFY_EVENT, State.INIT): H.on_set_notify_event,
    (Event.REG_WRITE_NOTIFY_EVENT, State.WAITING_FOR_INPUT): H.on_set_notify_event,
    (Event.REG_WRITE_NOTIFY_EVENT, State.RUN): H.on_set_notify_event,
    (Event.REG_WRITE_NOTIFY_EVENT, State.WAITING_ON_OUTPUT): H.on_set_notify_event,
    (Event.REG_WRITE_NOTIFY_EVENT, State.OUTPUT): H.on_set_notify_event,

    (Event.TICK, State.INIT): H.on_tick,
    (Event.TICK, State.WAITING_FOR_INPUT): H.on_tick,
    (Event.TICK, State.RUN): H.on_tick,
    (Event.TICK, State.WAITING_ON_OUTPUT): H.on_tick,
    (Event.TICK, State.OUTPUT): H.on_tick,
}
