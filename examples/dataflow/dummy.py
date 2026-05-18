import drava

# User-defined stage/callback
def func(frames):
    for frame in frames:
        ...

# Initialize Drava runtime (loads config, sets up transport/execution)
drava.init()

# Register callback as a pipeline stage
drava.register_routine(func)

# Start event loop / begin processing incoming data stream
drava.listen()

# Shutdown runtime and release resources
drava.deinit()