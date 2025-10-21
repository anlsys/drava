from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Optional, Tuple, List
from .ops import DemoAccel

class State(Enum):
    INIT = auto()
    WAITING_FOR_INPUT = auto()
    RUN = auto()
    WAITING_ON_OUTPUT = auto()
    OUTPUT = auto()

@dataclass
class Payload:
    tokens: List[str]
    tick: int

Handler = Callable[['FsmCtx', Payload], Tuple[Optional[State], Optional[List[str]]]]

@dataclass
class FsmCtx:
    ops: DemoAccel
