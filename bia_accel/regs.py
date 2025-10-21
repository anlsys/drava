from dataclasses import dataclass
from enum import IntEnum

@dataclass
class QueuedReq:
    tokens: list[str]

@dataclass
class QueuedNotify:
    tokens: list[str]

@dataclass
class Reg:
    # emulate only these two like in the original
    INIT_DONE: int = 0
    NOTIFICATION_EVENT: int = 0  # keep as int for simplicity

class RegID(IntEnum):
    INIT_START = 1
    INIT_DONE = 2
    NOTIFICATION_EVENT = 3
    DATA_READY = 4
