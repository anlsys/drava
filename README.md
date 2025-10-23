# drava
End-to-end functional simulation for BIA systems and simulations

## Installation

### Requirements
- A C/C++ compiler with support for C++20 (the only compiler tested is LLVM >=20.x)
- xkrt - https://gitlab.inria.fr/xkaapi/dev-v2 (see [JLSE](#on-jlse))
- swig if generating Python bindings

### On JLSE
Requirements are preinstalled:

```bash
# C/C++ 20 compiler
module use /soft/modulefiles
module load llvm/master-nightly

# XKRT
module use /home/rpereira/shared/modules
module load xkaapi/502226c375a8/Debug-cuda  #  if using A100/H100 nodes
module load xkaapi/502226c375a8/Debug-hip   #  if using MI250X nodes

# if using swig
module load swig/4.1.1
```

### Example build
```bash
mkdir build-debug
cd build-debug
cmake -DCMAKE_BUILD_TYPE=Debug ..    # must use a C++20 compiler, CC=clang CXX=clang++
make
```

### Example run
In terminal A
```
socat UNIX-LISTEN:/tmp/accel_2048.sock,fork -
```

In terminal B
```
./tests/tests
```
