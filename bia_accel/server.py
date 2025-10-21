import asyncio
from collections import deque
from typing import Deque, Optional, List
from .ops import DemoAccel
from .events import tokens_to_event, Event
from .fsm import FsmCtx, State, Payload
from .regs import QueuedReq
from .config.transitions import TRANSITIONS


class FsmServer:
    def __init__(self, ops: DemoAccel):
        self.ops = ops
        self.ctx = FsmCtx(ops=ops)
        self.state = State.INIT  # starting state of the FSM
        self.req_q: Deque[QueuedReq] = deque()

    async def send(self, w: asyncio.StreamWriter, line: str):
        w.write((line + "\n").encode())
        await w.drain()

    def _dispatch(self, evt: Event, payload: Payload) -> Optional[List[str]]:
        # strict table lookup: (event, current_state)
        handler = TRANSITIONS.get((evt, self.state))
        if not handler:
            # No direct transition found, try side-effect handlers valid in all states
            for (e, s), h in TRANSITIONS.items():
                if e == evt and s != self.state:
                    handler = h
                    break
        if not handler:
            return None

        next_state, reply = handler(self.ctx, payload)
        if next_state is not None:
            self.state = next_state
        return reply

    async def handle(self, r: asyncio.StreamReader, w: asyncio.StreamWriter):
        try:
            while True:
                raw = await r.readline()
                if not raw:
                    break
                parts = raw.decode().strip().split()
                if not parts:
                    continue

                # non-TICK commands are queued for next boundary
                if parts[0].upper() != "TICK":
                    self.req_q.append(QueuedReq(tokens=parts))
                    continue

                # ---- TICK boundary ----
                if len(parts) == 2:
                    curr_tick = int(parts[1])
                    responded = False

                    # (1) allow accelerator background ops to progress
                    await self.ops.catch_up_to(curr_tick)

                    # (2) process notifications visible at this boundary
                    for ntoks in await self.ops.notifications_up_to(curr_tick):
                        evt = tokens_to_event(ntoks)
                        reply = self._dispatch(evt, Payload(tokens=ntoks, tick=curr_tick))
                        if reply:
                            responded = True
                            await self.send(w, " ".join(reply))

                    # (3) drain queued commands at this boundary
                    while self.req_q:
                        req = self.req_q.popleft()
                        evt = tokens_to_event(req.tokens)
                        reply = self._dispatch(evt, Payload(tokens=req.tokens, tick=curr_tick))
                        if reply:
                            responded = True
                            await self.send(w, " ".join(reply))

                    # (4) send ACK if nothing else replied
                    if not responded:
                        await self.send(w, "ACK")
                    continue

                # unknown command
                await self.send(w, "ERR")
        finally:
            try:
                w.close()
                await w.wait_closed()
            except Exception:
                pass
