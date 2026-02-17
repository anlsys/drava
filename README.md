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
module load llvm/master-nightly
module load cmake
module load intel/oneapi/release/2024.1
module load cuda/12.3.0
module load hwloc

# XKRT
module load xkaapi/502226c375a8/Debug-cuda  #  if using A40/A100/H100 nodes

# if using swig
module load swig/4.4.1

# if using python 3.14.3, compiled with `--disable-gil`
module load python/3.14.3-no-gil
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

### Build Drava
```shell
# Define NATS_ROOT if Jetstream is used
export NATS_ROOT=$HOME/opt/nats
mkdir build-debug-nats && cd build-debug-nats
CC=clang CXX=clang++ cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j
export PYTHONPATH="$(pwd):$PYTHONPATH" # so that the build dir is in the Python path
```
- To use Jetstream/Socket set it with environment variable:
```shell
export DRAVA_TRANSPORT=nats
# export DRAVA_TRANSPORT=socket
export DRAVA_INFER_BATCH=128
export DRAVA_JS_FETCH_BATCH=8
export DRAVA_JS_FETCH_TIMEOUT_MS=1000
```
- Set number of threads for XKRT with environment variable (default = 4):
```shell
export DRAVA_THREADS=20
```

## Applications

Example applications are located in [examples](examples) directory.
Each application contains its own README with instructions for running it.
Available applications:
- [PtychoNN](examples/ptychonn)
- [Iris Inferrence](examples/iris_knn)
- [Dataflow](examples/dataflow)

## Tests
### Dependency
- [Check unit testing framework](https://libcheck.github.io/check/index.html)
- [Bats-core: Bash automated testing system](https://bats-core.readthedocs.io/en/stable/)

### Setup tests in JLSE
- Install `Check`:
```shell
wget https://github.com/libcheck/check/archive/refs/tags/0.15.2.zip
unzip 0.15.2.zip
cd check-0.15.2
module load cmake
mkdir build-gcc && cd build-gcc
CC=gcc CXX=g++ cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/opt/check-0.15.2
make -j
make install
```
- Install `Bats`:
```shell
git clone https://github.com/bats-core/bats-core.git
cd bats-core
git checkout v1.13.0
./install.sh "$HOME/opt/bats-1.13.0"
```
- Set the environment variables:
```shell
# Add to .zshrc/.bashrc
export CHECK_ROOT="$HOME/opt/check-0.15.2"
export NATS_ROOT="$HOME/opt/nats"
# Add binaries to PATH
export PATH="$HOME/nats_binary:$PATH"
export PATH="$HOME/opt/bats-1.13.0/bin:$PATH"
```
- Run all tests
```shell
ctest --test-dir $HOME/drava/build/tests --output-on-failure
```
- Transport specific tests for Drava C API:
```shell
# Enable JetStream tests (requires a running NATS server)
USE_NATS=1 ctest --test-dir $HOME/drava/build/tests --output-on-failure
USE_NATS=1 ctest --test-dir $HOME/drava/build/tests -R transport_nats -V
# Enable socket tests (requires socket endpoint to exist)
USE_SOCKET=1 ctest --test-dir $HOME/drava/build/tests --output-on-failure
USE_SOCKET=1 ctest --test-dir $HOME/drava/build/tests -R transport_socket -V
# Enable both (requires both NATS server and socket running)
USE_NATS=1 USE_SOCKET=1 ctest --test-dir $HOME/drava/build/tests --output-on-failure
```
- Integration test with verbose:
```
ctest --test-dir $HOME/drava/build/tests -R integration_transport_jetstream_python -V
ctest --test-dir $HOME/drava/build/tests -R integration_transport_socket_python -V
```
### References
- [NATS C client](https://github.com/nats-io/nats.c/)
- [Check unit testing framework](https://libcheck.github.io/check/index.html)
- [Bats-core: Bash Automated Testing System](https://bats-core.readthedocs.io/en/stable/)
