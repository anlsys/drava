import os
import drava


def func(s):
    print("Python app received: {}".format(s))

drava.init()
drava.register_routine_py(func)
drava.listen_py()
drava.deinit()
