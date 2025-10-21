import asyncio
from typing import Iterable, Protocol, Deque, Tuple
from collections import deque
from .regs import Reg, RegID, QueuedNotify

class AccelOps(Protocol):
    async def catch_up_to(self, updown_target_tick: int) -> None: ...
    async def notifications_up_to(self, updown_currtick: int) -> Iterable[list[str]]: ...
    # actions the FSM can invoke:
    def begin_init(self, updown_currtick: int) -> None: ...
    def begin_exec(self, updown_currtick: int) -> None: ...
    def write_mem64(self, offset: int, hex_data: str) -> None: ...
    def read_mem64(self, offset: int) -> bytes: ...
    def get_reg_INIT_DONE(self) -> int: ...
    def set_reg_INIT_DONE(self, val: int) -> None: ...
    def set_reg_NOTIFICATION_EVENT(self, val: int) -> None: ...
    def get_reg_NOTIFICATION_EVENT(self) -> int: ...

class DemoAccel(AccelOps):
    def __init__(self, scale: int, memSize: int):
        self.regs = Reg()
        self._ops: list[dict] = []  # each op has {"name","updown_start_tick","local"}
        self._notify: Deque[Tuple[int, QueuedNotify]] = deque()
        self.mem = bytearray(memSize)
        self.scale = scale
        self._tasks: set[asyncio.Task] = set()

    # --- time mapping ---
    def _visible_tick(self, op) -> int:
        return op["updown_start_tick"] + (op["local"] // self.scale)

    # --- init runtime (demo) ---
    async def _run_init_until_done(self, op: dict):
        dummyTicks, localStep, step_interval = 3000, 1500, 0.01
        try:
            while op["local"] < dummyTicks:
                op["local"] += localStep
                await asyncio.sleep(step_interval)
            updown_tick = self._visible_tick(op)
            print(f"[ACCEL] init done at {updown_tick}")
            # queue a REGWRITE INIT_DONE 1 notification (silent to host, but sets reg)
            self._notify.append((updown_tick, QueuedNotify(tokens=["REGWRITE", str(RegID.INIT_DONE.value), "1"])))
        finally:
            self._ops.remove(op)

    def begin_init(self, updown_currtick: int) -> None:
        entry = {"name": "INIT", "updown_start_tick": updown_currtick, "local": 0}
        self._ops.append(entry)
        t = asyncio.create_task(self._run_init_until_done(entry))
        self._tasks.add(t); t.add_done_callback(self._tasks.discard)

    # --- exec runtime (demo) ---
    async def _run_exec_until_done(self, op: dict):
        dummyTicks, localStep, step_interval = 3000, 2, 0
        try:
            while op["local"] < dummyTicks:
                op["local"] += localStep
                await asyncio.sleep(step_interval)
            updown_tick = self._visible_tick(op)
            print(f"[ACCEL] exec done at {updown_tick}")
            # queue COMPUTATION_DONE; host sees "COMPUTATION_DONE <evword>"
            self._notify.append((updown_tick, QueuedNotify(tokens=["COMPUTATION_DONE"])))
        finally:
            self._ops.remove(op)

    def begin_exec(self, updown_currtick: int) -> None:
        entry = {"name": "EXEC", "updown_start_tick": updown_currtick, "local": 0}
        self._ops.append(entry)
        t = asyncio.create_task(self._run_exec_until_done(entry))
        self._tasks.add(t); t.add_done_callback(self._tasks.discard)

    async def catch_up_to(self, updown_target_tick: int) -> None:
        # let background tasks advance; break when all ops are visible past target
        while True:
            await asyncio.sleep(0)
            if all(self._visible_tick(op) >= updown_target_tick for op in self._ops):
                break

    async def notifications_up_to(self, updown_currtick: int) -> Iterable[list[str]]:
        out: list[list[str]] = []
        while self._notify and self._notify[0][0] <= updown_currtick:
            _, item = self._notify.popleft()
            name = item.tokens[0].upper()
            if name == "REGWRITE":
                reg_id = int(item.tokens[1]); val = int(item.tokens[2])
                if reg_id == RegID.INIT_DONE:
                    self.regs.INIT_DONE = val  # silent to host
            elif name == "COMPUTATION_DONE":
                evword = self.regs.NOTIFICATION_EVENT
                out.append(["COMPUTATION_DONE", str(evword)])
            else:
                # passthrough if you add more
                out.append(item.tokens)
        return out

    # ---- mem/regs helpers ----
    def write_mem64(self, offset: int, hex_data: str) -> None:
        self.mem[offset:offset+64] = bytes.fromhex(hex_data)

    def read_mem64(self, offset: int) -> bytes:
        return self.mem[offset:offset+64]

    def get_reg_INIT_DONE(self) -> int:
        return self.regs.INIT_DONE

    def set_reg_INIT_DONE(self, val: int) -> None:
        self.regs.INIT_DONE = val

    def set_reg_NOTIFICATION_EVENT(self, val: int) -> None:
        self.regs.NOTIFICATION_EVENT = val

    def get_reg_NOTIFICATION_EVENT(self) -> int:
        return self.regs.NOTIFICATION_EVENT
