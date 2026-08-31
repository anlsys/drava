# Building Drava on JLSE

Drava has been developed and tested on the ALCF **JLSE** cluster, where the
dependencies (xkrt, LLVM/Clang, CUDA, a no-GIL Python build) are preinstalled as
modules. This document gives the exact, site-specific steps used there. For a
generic dependency list, see the [main README](../README.md#building-from-source).

## 1. Load modules

```shell
# module paths
module use /soft/modulefiles
module load spack/gcc-0.6.1
module use /home/rpereira/shared/modules

# C/C++20 compiler + toolchain
module load llvm/master-nightly
module load cmake
module load intel/oneapi/release/2024.1
module load cuda/12.3.0
module load hwloc

# xkrt (xkaapi) runtime — this build targets A40/A100/H100 nodes
module load xkaapi/502226c375a8/Debug-cuda

# SWIG for the Python bindings
module load swig/4.4.1

# no-GIL Python (3.14.3 built with --disable-gil)
module load python/3.14.3-no-gil
```

## 2. Build yaml-cpp

```shell
git clone git@github.com:jbeder/yaml-cpp.git
cd yaml-cpp && mkdir build && cd build
CC=clang CXX=clang++ cmake .. -DYAML_BUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX=$HOME/opt/yaml-cpp-install
make -j
make install
```

## 3. (Optional) NATS for the JetStream transport

Install the NATS server:

```shell
mkdir -p ~/nats_binary && cd ~/nats_binary
curl -fsSL https://binaries.nats.dev/nats-io/nats-server/v2@v2.11.6 | sh
```

Build the NATS C client:

```shell
git clone git@github.com:nats-io/nats.c.git
cd nats.c && mkdir build && cd build
cmake .. -DNATS_BUILD_STREAMING=OFF -DCMAKE_INSTALL_PREFIX=$HOME/opt/nats
make -j
make install
```

## 4. Build Drava

```shell
export NATS_ROOT=$HOME/opt/nats     # only if using the JetStream transport
export NVML_ROOT=$CUDA_HOME         # only if you want GPU energy
mkdir build-debug-nats && cd build-debug-nats
CC=clang CXX=clang++ cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j
export PYTHONPATH="$(pwd):$PYTHONPATH"   # so `import drava` finds the built module
```

CMake prints whether the NATS and NVML backends were enabled. On JLSE nodes
without readable RAPL domains, CPU energy is disabled and only GPU energy (if
NVML is enabled) is reported.

## 5. Run an example

```shell
source ~/venvs/no-gil-3.13/bin/activate     # a venv with the example deps
cd ~/drava/build-debug-nats
export PYTHONPATH="$(pwd):$PYTHONPATH"
cd ../examples/ptychonn

# start nats-server -js in another terminal, then:
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml DRAVA_STAGE_NAME=stage1
python app.py
```

See [docs/paper.md](paper.md) for the full benchmark commands used in the paper.

## Setting up the test dependencies (Check + Bats)

The C runtime tests use [Check](https://libcheck.github.io/check/); the
integration tests use [Bats](https://bats-core.readthedocs.io/).

Install Check:

```shell
wget https://github.com/libcheck/check/archive/refs/tags/0.15.2.zip
unzip 0.15.2.zip && cd check-0.15.2
module load cmake
mkdir build-gcc && cd build-gcc
CC=gcc CXX=g++ cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/opt/check-0.15.2
make -j
make install
```

Install Bats:

```shell
git clone https://github.com/bats-core/bats-core.git
cd bats-core && git checkout v1.13.0
./install.sh "$HOME/opt/bats-1.13.0"
```

Environment (add to `~/.zshrc` / `~/.bashrc`):

```shell
export CHECK_ROOT="$HOME/opt/check-0.15.2"
export NATS_ROOT="$HOME/opt/nats"
export PATH="$HOME/nats_binary:$PATH"
export PATH="$HOME/opt/bats-1.13.0/bin:$PATH"
```

Run the tests:

```shell
ctest --test-dir $HOME/drava/build/tests --output-on-failure

# Transport-specific (opt-in; require a running server/endpoint):
USE_NATS=1  ctest --test-dir $HOME/drava/build/tests -R transport_nats -V
USE_SOCKET=1 ctest --test-dir $HOME/drava/build/tests -R transport_socket -V

# Python integration tests:
ctest --test-dir $HOME/drava/build/tests -R integration_transport_jetstream_python -V
ctest --test-dir $HOME/drava/build/tests -R integration_transport_socket_python -V
```
