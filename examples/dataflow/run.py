import os
import drava


def func(s):
    print("Python app received: {}".format(s))


transport = os.getenv("DRAVA_TRANSPORT", "socket")
drava.init(transport)

drava.register_routine_py(func)
drava.listen_py()
drava.deinit()
