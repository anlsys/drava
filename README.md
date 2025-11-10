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
# module path setup
module use /soft/modulefiles
module load spack/gcc-0.6.1
module use /home/rpereira/shared/modules

# C/C++ 20 compiler
module use /soft/modulefiles
module load llvm/master-nightly
<<<<<<< HEAD
module load cmake
module load spack/gcc-0.6.1
=======
>>>>>>> origin/main
module load intel/oneapi/release/2024.1
module load cuda/12.3.0

# XKRT
module load xkaapi/502226c375a8/Debug-cuda  #  if using A100/H100 nodes
module load xkaapi/502226c375a8/Debug-hip   #  if using MI250X nodes

# if using swig
module load swig/4.1.1
```

### Example build using Jetstream
- Get NATS server binary
```bash
cd jetstream
curl -fsSL https://binaries.nats.dev/nats-io/nats-server/v2@v2.11.6 | sh
```
- Build NATS C client
```bash
git clone git@github.com:nats-io/nats.c.git
mkdir build && cd build
cmake .. -DNATS_BUILD_STREAMING=OFF -DCMAKE_INSTALL_PREFIX=$HOME/opt/nats
make -j
make install
```
- Build Drava
```bash
mkdir build-debug-nats && cd build-debug-nats
CC=clang CXX=clang++ cmake -DCMAKE_BUILD_TYPE=Debug -DUSE_NATS=ON -DNATS_ROOT=$HOME/opt/nats ..
make
export PYTHONPATH="$(pwd):$PYTHONPATH" # so that the build dir is in the Python path
```

### Example run using Jetstream
- In terminal 1, run the NATS server
```bash
./nats-server -js -sd ./jsdata
```
- In terminal 2, run the subscriber script
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python jetstream/publisher.py
```
- In terminal 3, run test
```bash
./tests/tests
```

### Example run using Sockets
In terminal A
```
socat UNIX-LISTEN:/tmp/accel_2048.sock,fork -
```

In terminal B
```
./tests/tests
```


### References
- [NATS C client](https://github.com/nats-io/nats.c/)
