# Drava
Runtime and end-to-end simulation for BIA systems and simulations

## Installation

### Requirements
- C/C++ compiler with C++20 support (tested: LLVM ≥ 20.x)
- xkrt - https://gitlab.inria.fr/xkaapi/dev-v2 (see [JLSE](#on-jlse))
- swig if generating Python bindings
- NATS server if run with Jetstream

### On JLSE
Requirements are preinstalled:

```shell
# GPU 

# module path setup
module use /soft/modulefiles
module load spack/gcc-0.6.1
module use /home/rpereira/shared/modules

# C/C++ 20 compiler
module use /soft/modulefiles
module load llvm/master-nightly
module load cmake
module load intel/oneapi/release/2024.1
module load cuda/12.3.0
module load hwloc

# XKRT
module load xkaapi/502226c375a8/Debug-cuda  #  if using A100/H100 nodes

# if using swig
module load swig/4.1.1

module load xkaapi/502226c375a8/Debug-hip   #  if using MI250X nodes

```

### (Optional) NATS requirements
- Install NATS server
```shell
cd ~/nats_binary
curl -fsSL https://binaries.nats.dev/nats-io/nats-server/v2@v2.11.6 | sh
```
- Build NATS C client
```shell
git clone git@github.com:nats-io/nats.c.git
mkdir build && cd build
cmake .. -DNATS_BUILD_STREAMING=OFF -DCMAKE_INSTALL_PREFIX=$HOME/opt/nats
make -j
make install
```

### Build Drava (for both NATS Jetstream and Socket)
```shell
# Define NATS_ROOT if Jetstream is used
export NATS_ROOT=$HOME/opt/nats
mkdir build-debug-nats && cd build-debug-nats
CC=clang CXX=clang++ cmake -DCMAKE_BUILD_TYPE=Debug ..
make
export PYTHONPATH="$(pwd):$PYTHONPATH" # so that the build dir is in the Python path
```


## Applications

Example applications are located in [examples](examples) directory.
Each application contains its own README with instructions for running it.
Available applications:
- [Iris Inferrence](examples/iris_knn)
- [Dataflow](examples/dataflow)


### References
- [NATS C client](https://github.com/nats-io/nats.c/)
