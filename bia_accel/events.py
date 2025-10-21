from enum import Enum, auto
from .regs import RegID

class Event(Enum):
    INIT_EVT = auto()
    REG_WRITE_START = auto()
    REG_WRITE_NOTIFY_EVENT = auto()
    MEMWRITE = auto()
    MEMREAD = auto()
    REGREAD = auto()
    COMPUTE_DONE = auto()
    TICK = auto()
    UNKNOWN = auto()

def tokens_to_event(tokens: list[str]) -> Event:
    if not tokens:
        return Event.UNKNOWN
    name = tokens[0].upper()
    if name == "TICK":
        return Event.TICK
    if name == "REGWRITE":
        reg_id = int(tokens[1]); val = int(tokens[2])
        if reg_id == RegID.INIT_START and val == 1:
            return Event.INIT_EVT
        if reg_id == RegID.DATA_READY and val == 1:
            return Event.REG_WRITE_START
        if reg_id == RegID.NOTIFICATION_EVENT:
            return Event.REG_WRITE_NOTIFY_EVENT
        return Event.UNKNOWN
    if name == "REGREAD":
        return Event.REGREAD
    if name == "MEMWRITE":
        return Event.MEMWRITE
    if name == "MEMREAD":
        return Event.MEMREAD
    if name == "COMPUTATION_DONE":
        return Event.COMPUTE_DONE
    return Event.UNKNOWN
