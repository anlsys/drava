#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio, os
from bia_accel.ops import DemoAccel
from bia_accel.server import FsmServer

SOCK_PATH = "/tmp/accel_2048.sock"

async def main():
    try:
        os.unlink(SOCK_PATH)
    except FileNotFoundError:
        pass

    ops = DemoAccel(scale=1000, memSize=1024)
    server = FsmServer(ops)
    srv = await asyncio.start_unix_server(server.handle, path=SOCK_PATH)
    print(f"[ACCEL] listening on {SOCK_PATH}")
    async with srv:
        await srv.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
