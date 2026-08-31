# Building Drava from source

The C++ runtime depends on several native libraries. If you are on the ALCF
**JLSE** cluster, use [docs/jlse.md](jlse.md) instead — the dependencies are
preinstalled there and that guide is copy-paste ready. This page is the generic
build for other environments.

> The example apps and the `drava-pipeline` CLI are pure Python and run anywhere;
> only the C++ runtime (the `drava` module) needs the build below.

## Dependencies

- A C/C++ compiler with C++20 support (tested with LLVM/Clang).
- [xkrt](https://gitlab.inria.fr/xkaapi/dev-v2) — the task runtime Drava is built on.
- [yaml-cpp](https://github.com/jbeder/yaml-cpp) — pipeline config parsing.
- [SWIG](https://www.swig.org/) — generates the Python bindings.
- A no-GIL Python build (3.13+ compiled with `--disable-gil`).
- Optional: a NATS server + [nats.c](https://github.com/nats-io/nats.c) client
  for the JetStream transport.
- Optional: NVML/CUDA for GPU energy reporting.

## Build yaml-cpp

```shell
git clone https://github.com/jbeder/yaml-cpp.git
cd yaml-cpp && mkdir build && cd build
CC=clang CXX=clang++ cmake .. -DYAML_BUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX=$HOME/opt/yaml-cpp-install
make -j && make install
```

## (Optional) NATS for the JetStream transport

```shell
# NATS server
curl -fsSL https://binaries.nats.dev/nats-io/nats-server/v2@v2.11.6 | sh

# NATS C client
git clone https://github.com/nats-io/nats.c.git
cd nats.c && mkdir build && cd build
cmake .. -DNATS_BUILD_STREAMING=OFF -DCMAKE_INSTALL_PREFIX=$HOME/opt/nats
make -j && make install
```

## Build Drava

```shell
export NATS_ROOT=$HOME/opt/nats     # only if using the JetStream transport
export NVML_ROOT=$CUDA_HOME         # only if you want GPU energy
mkdir build && cd build
CC=clang CXX=clang++ cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j
export PYTHONPATH="$(pwd):$PYTHONPATH"   # so `import drava` finds the built module
```

CMake prints whether the NATS and NVML backends were enabled. Confirm the module
imports:

```shell
python -c "import drava; print('drava OK')"
```

Next: [running the examples](examples.md).
