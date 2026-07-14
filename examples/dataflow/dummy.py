import drava

# User-defined stage/callback
def func(frames):
    for frame in frames:
        ...

# Run the Drava stage: loads config, sets up transport/execution, registers the
# callback, processes the incoming stream, and shuts down on end-of-stream.
drava.run(func)