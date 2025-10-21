from .fsm import FsmCtx, State, Payload
from .regs import RegID

# ----- state-changing transitions -----

def on_init(ctx: FsmCtx, p: Payload):
    ctx.ops.begin_init(p.tick)
    return (State.WAITING_FOR_INPUT, None)

def on_start_computation(ctx: FsmCtx, p: Payload):
    ctx.ops.begin_exec(p.tick)
    return (State.RUN, None)

def on_compute_done(ctx: FsmCtx, p: Payload):
    evword = ctx.ops.get_reg_NOTIFICATION_EVENT()
    return (State.WAITING_ON_OUTPUT, ["COMPUTATION_DONE", str(evword)])

# After host reads output memory → back to WAITING_FOR_INPUT
def on_mem_read_output(ctx: FsmCtx, p: Payload):
    offset, evword = int(p.tokens[1]), p.tokens[2]
    data = ctx.ops.read_mem64(offset)
    return (State.WAITING_FOR_INPUT, ["MEMREADACK", str(offset), data.hex(), evword])

# REGREAD after output ready → OUTPUT state
def on_reg_read_output(ctx: FsmCtx, p: Payload):
    reg_id, evword = int(p.tokens[1]), p.tokens[2]
    val = ctx.ops.get_reg_INIT_DONE() if reg_id == RegID.INIT_DONE else 0
    return (State.OUTPUT, ["REGREADACK", str(reg_id), str(val), evword])

# ----- side effects (no state change) -----

def on_set_notify_event(ctx: FsmCtx, p: Payload):
    val = int(p.tokens[2])
    ctx.ops.set_reg_NOTIFICATION_EVENT(val)
    return (None, None)

def on_mem_write(ctx: FsmCtx, p: Payload):
    offset, data, evword = int(p.tokens[1]), p.tokens[2], p.tokens[3]
    ctx.ops.write_mem64(offset, data)
    return (None, ["MEMWRITEACK", str(offset), evword])

def on_mem_read(ctx: FsmCtx, p: Payload):
    offset, evword = int(p.tokens[1]), p.tokens[2]
    data = ctx.ops.read_mem64(offset)
    return (None, ["MEMREADACK", str(offset), data.hex(), evword])

def on_reg_read(ctx: FsmCtx, p: Payload):
    reg_id, evword = int(p.tokens[1]), p.tokens[2]
    val = ctx.ops.get_reg_INIT_DONE() if reg_id == RegID.INIT_DONE else 0
    return (None, ["REGREADACK", str(reg_id), str(val), evword])

def on_tick(ctx: FsmCtx, p: Payload):
    return (None, None)
