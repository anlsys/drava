import drava

def func():
    print("Hello Python")

drava.init()
drava.register_routine_py(func)
drava.listen_py()
drava.deinit()
