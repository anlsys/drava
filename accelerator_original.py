#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio, os
from dataclasses import dataclass
from typing import Deque, List, Tuple, Iterable, Protocol
from collections import deque
from enum import IntEnum

SOCK_PATH = "/tmp/accel_2048.sock"

@dataclass
class QueuedReq:
	# Queued requests from UpDown (REGWRITE/REGREAD/MEMWRITE/MEMREAD)
	tokens: List[str]

@dataclass
class QueuedNotify:
	# Queued requests from Accelerator (REGWRITE/COMPUTATION_DONE)
	tokens: List[str]

@dataclass
class Reg:
	"""
	Registers to be emulated
	We dont emulate INIT_START and DATA_READY and instead trigger init_accelerator()/start_computation() directly if there is a REGWRITE request
	queued in
	"""
	INIT_DONE: int = 0
	NOTIFICATION_EVENT: str = ""

class RegID(IntEnum):
	INIT_START = 1
	INIT_DONE = 2
	NOTIFICATION_EVENT = 3
	DATA_READY = 4

# ==========================
# Accelerator plugins
# ==========================

class AccelOps(Protocol):
	async def catch_up_to(self, updown_target_tick: int) -> None:
		"""
		Waits until updown-visible tick of *all running operations*
		reaches at least updown_target_tick (handles slow simulation).
		"""
		...

	async def apply_command_at_boundary(self, cmd_tokens: List[str], updown_currtick: int) -> None:
		"""
		Execute all queued commands *at this boundary* (updown_currtick).
		Interpretation is plugin-defined (e.g., REGWRITE/MEMWRITE/etc.).
		"""
		...

	async def notifications_up_to(self, updown_currtick: int) -> Iterable[List[str]]:
		"""
		Dequeue all REGWRITE and COMPUTATION_DONE notifications from accelerator whose updown-visible tick
		is <= updown_currtick
		Handles fast simulation
		"""
		...


# ==========================
# Generic IPC wrapper
# ==========================

class IpcServer:
	def __init__(self, ops: AccelOps):
		self.ops = ops
		self.req_q: Deque[QueuedReq] = deque()

	async def sendIPC(self, w: asyncio.StreamWriter, line: str):
		w.write((line + "\n").encode()); await w.drain()

	async def handle(self, r: asyncio.StreamReader, w: asyncio.StreamWriter):
		try:
			while True:
				raw = await r.readline()
				if not raw:
					break
				parts = raw.decode().strip().split()
				if not parts:
					continue

				cmd = parts[0].upper()

				if cmd != "TICK":
					self.req_q.append(QueuedReq(tokens = parts))
					#await self.sendIPC(w, "ACK")

					continue

				# Sync boundary
				if cmd == "TICK" and len(parts) == 2:
					curr_updown_tick = int(parts[1])

					response = False

					# (1) let accelerator catch up (if slower simulation)
					await self.ops.catch_up_to(curr_updown_tick)

					# (2) release notifications visible at this boundary
					for tokens in await self.ops.notifications_up_to(curr_updown_tick):
						response = True
						await self.sendIPC(w, " ".join(tokens))

					# (3) drain queued commands at this boundary (FIFO)
					# Queued commands are always REGWRITE/MEMWRITE/REGREAD/MEMREAD
					while self.req_q:
						request = self.req_q.popleft()
						tokens = await self.ops.apply_command_at_boundary(request.tokens, curr_updown_tick)

						if tokens != None:
							await self.sendIPC(w, " ".join(tokens))

					# (5) deliver ACK for the IPC issued
					if response == False:
						await self.sendIPC(w, "ACK")

					continue

				# unknown
				await self.sendIPC(w, "ERR")
		finally:
			try:
				w.close(); await w.wait_closed()
			except Exception:
				pass

class DemoAccel(AccelOps):
	def __init__(self, scale: int, memSize: int):
		self.regs = Reg()

		# each "op" tracks its own local tick
		self._ops: List[dict] = []  # [{"name": str, "updown_start_tick": int, "local": int}]
		self._notify: Deque[Tuple[int, QueuedNotify]] = deque()  # (updown_tick, response)

		self.mem = bytearray(memSize)
		self.scale = scale

		self._tasks: set[asyncio.Task] = set()

	# ---- helpers ----
	def get_updown_visible_tick_for_op(self, op) -> int:
		# map local tick to updown tick for this op
		return op["updown_start_tick"] + (op["local"] // self.scale)

	"""
	Dummy initialization runtime. Drop in your simulation code here
	"""
	async def _run_init_until_done(self, op: dict):
		dummyTicks = 3000
		localStep = 1500
		step_interval = 10

		try:
			while op["local"] < dummyTicks:
				op["local"] += localStep

				await asyncio.sleep(step_interval)

			updown_tick = self.get_updown_visible_tick_for_op(op)
			print(f"[ACCEL] init done at {updown_tick}")
			self._notify.append((updown_tick, QueuedNotify(tokens=["REGWRITE", str(RegID.INIT_DONE.value), "1"])))

		finally:
			self._ops.remove(op)

	def init_accelerator(self, entry: dict):
		"""
		Start the init operation without blocking:
		@: 'entry' is the op dict already inserted into self._ops
		Spawns a background task that increments entry["local"] over time
		"""
		task = asyncio.create_task(self._run_init_until_done(entry))
		self._tasks.add(task)
		task.add_done_callback(self._tasks.discard)

	"""
	Dummy computation runtime. Drop in your simulation code here
	"""
	async def _run_exec_until_done(self, op: dict):
		dummyTicks = 3000
		localStep = 2
		step_interval = 0

		try:
			while op["local"] < dummyTicks:
				op["local"] += localStep

				await asyncio.sleep(step_interval)

			updown_tick = self.get_updown_visible_tick_for_op(op)
			print(f"[ACCEL] exec done at {updown_tick}")
			self._notify.append((updown_tick, QueuedNotify(tokens=["COMPUTATION_DONE"])))

		finally:
			self._ops.remove(op)

	def start_computation(self, entry: dict):
		"""
		Start the frame computation operation without blocking:
		@: 'entry' is the op dict already inserted into self._ops
		Spawns a background task that increments entry["local"] over time
		"""
		task = asyncio.create_task(self._run_exec_until_done(entry))
		self._tasks.add(task)
		task.add_done_callback(self._tasks.discard)

	async def catch_up_to(self, updown_target_tick: int) -> None:
		# advance each running op until its updown-visible tick reaches target

		while True:
			progress = False
			for op in self._ops:
				if self.get_updown_visible_tick_for_op(op) >= updown_target_tick:
					continue
				progress = True

			if not progress:
				break
			await asyncio.sleep(0)

	async def apply_command_at_boundary(self, cmd_tokens: List[str], updown_currtick: int):
		if not cmd_tokens:
			return
		name = cmd_tokens[0].upper()

		if name == "REGWRITE":
			# <REGWRITE> <reg id> <value>

			reg_id = int(cmd_tokens[1])
			val = cmd_tokens[2]

			"""
			If INIT_START &&
			If value to write is 1, trigger accelerator initialization
			"""
			if reg_id == RegID.INIT_START and int(val) == 1:
				self._ops.append({"name": "INIT_ACCELERATOR", "updown_start_tick": updown_currtick, "local": 0})
				entry = self._ops[-1]

				# Call the accelerator hook. The hook will internally keep incrementing 'local' tick as the operation continues
				self.init_accelerator(entry)

			elif reg_id == RegID.NOTIFICATION_EVENT:
				self.regs.NOTIFICATION_EVENT = int(val)

			elif reg_id == RegID.DATA_READY and int(val) == 1:
				self._ops.append({"name": "START_COMPUTATION", "updown_start_tick": updown_currtick, "local": 0})
				entry = self._ops[-1]

				# Call the accelerator hook. The hook will internally keep incrementing 'local' tick as the operation continues
				self.start_computation(entry)

			return None

		if name == "REGREAD":
			# <REGREAD> <reg id> <evword>

			reg_id = int(cmd_tokens[1])
			evword = cmd_tokens[2]

			if (reg_id == RegID.INIT_DONE):
				val = self.regs.INIT_DONE

				# <REGREADACK> <reg id> <val> <evword>
				tokens = ["REGREADACK", str(reg_id), str(val), evword]
				return tokens

		if name == "MEMWRITE":
			# <MEMWRITE> <offset> <data> <evword>

			offset = int(cmd_tokens[1])
			hex_data = cmd_tokens[2]

			evword = cmd_tokens[3]

			self.mem[offset:offset + 64] = bytes.fromhex(hex_data)

			# <MEMWRITEACK> <offset> <evword>
			tokens = ["MEMWRITEACK", str(offset), evword]
			return tokens

		if name == "MEMREAD":
			# <MEMREAD> <offset> <evword>

			offset = int(cmd_tokens[1])
			evword = cmd_tokens[2]

			data = self.mem[offset:offset + 64]

			# <MEMREADACK> <offset> <data> <evword>
			tokens = ["MEMREADACK", str(offset), data.hex(), evword]

	async def notifications_up_to(self, updown_currtick: int) -> Iterable[List[str]]:
		out: List[List[str]] = []

		while self._notify and self._notify[0][0] <= updown_currtick:
			_, item = self._notify.popleft()
			tokens = item.tokens

			name = tokens[0].upper()

			if name == "REGWRITE":
				# <REGWRITE> <reg id> <value>
				reg_id = int(tokens[1])
				val = tokens[2]

				if reg_id == RegID.INIT_DONE:
					self.regs.INIT_DONE = int(val)

			elif name == "COMPUTATION_DONE":
				evword = self.regs.NOTIFICATION_EVENT

				# <COMPUTATION_DONE> <NOTIFICATION_EVENT>
				out.append([name, evword])

		return out

async def main():
	try:
		os.unlink(SOCK_PATH)
	except FileNotFoundError:
		pass

	ops = DemoAccel(scale=1000, memSize=1024)  # demo accelerator
	server = IpcServer(ops)

	srv = await asyncio.start_unix_server(server.handle, path=SOCK_PATH)
	print(f"[ACCEL] listening on {SOCK_PATH}")
	async with srv:
		await srv.serve_forever()

if __name__ == "__main__":
	asyncio.run(main())
