import drava

def func(s):
    print("Python app received: {}".format(s))

drava.init("nats")
drava.register_routine_py(func)
drava.listen_py()
drava.deinit()
