# Drava on JLSE — build, datasets, and running the examples

Drava is developed and tested on the ALCF **JLSE** cluster, where the native
dependencies are preinstalled as modules. This is a copy-paste-ready guide to go
from a fresh checkout to running the PtychoNN and TomoGAN examples, including
their datasets and model weights.

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

# xkrt (xkaapi) runtime — targets A40/A100/H100 nodes
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
make -j && make install
cd ~
```

## 3. NATS (for the JetStream transport)

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
make -j && make install
cd ~
```

Add to the shell profile (`~/.bashrc` / `~/.zshrc`):

```shell
export NATS_ROOT="$HOME/opt/nats"
export PATH="$HOME/nats_binary:$PATH"
```

## 4. Build Drava

```shell
cd ~/drava
export NATS_ROOT=$HOME/opt/nats     # JetStream transport
export NVML_ROOT=$CUDA_HOME         # GPU energy
mkdir build && cd build
CC=clang CXX=clang++ cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j
export PYTHONPATH="$(pwd):$PYTHONPATH"   # so `import drava` works
python -c "import drava; print('drava OK')"
cd ~/drava
```

CMake prints whether NATS and NVML were enabled. On nodes without readable RAPL
domains, CPU energy is disabled; GPU energy still works when NVML is enabled.

## 5. Python environment for the examples

The example apps (TensorFlow, NumPy, h5py, nats-py, …) need a Python env. Use a
no-GIL venv:

```shell
python -m venv ~/venvs/no-gil-3.13
source ~/venvs/no-gil-3.13/bin/activate
# On a JLSE interactive node, use the ALCF proxy for pip:
pip install --proxy http://proxy.ftm.alcf.anl.gov:3128 -r ~/drava/examples/ptychonn/requirements.txt
pip install --proxy http://proxy.ftm.alcf.anl.gov:3128 -r ~/drava/examples/tomogan/requirements.txt
```

Always put the build directory on `PYTHONPATH` before running an app:

```shell
export PYTHONPATH="$HOME/drava/build:$PYTHONPATH"
```

## 6. PtychoNN dataset + model weights

The PtychoNN test data and pretrained weights come from the
[PtychoNN_data](https://huggingface.co/datasets/mcherukara/PtychoNN_data)
Hugging Face dataset. Download the partial set (test frames + one weight file):

```shell
cd ~/drava/examples/ptychonn
source ~/venvs/no-gil-3.13/bin/activate
python download_partial.py
# creates PtychoNN_data_partial/{X_test.npy, wts4/min_epoch.npy, wts4/weights.66.hdf5}
```

Run the two-stage benchmark (starts NATS with the bundled `nats.conf`, wires both
stages, prints throughput):

```shell
cd ~/drava/examples/ptychonn
python benchmark_two_stages.py --batches 256 --runs 1 --num-frames 10000 \
    --threads 4 --timeout-ms 200 --rate-hz 1000 --nats-url nats://127.0.0.1:4222
```

## 7. TomoGAN dataset + model weights

TomoGAN uses a sample dataset (`dataset/demo-dataset-real.h5`) and a trained
generator checkpoint (`dataset/testjob-it00500.h5`). Copy them into the example's
`dataset/` directory (from a local checkout or shared location):

```shell
# from a workstation:
scp -r <local>/drava/examples/tomogan/dataset \
    jlse:~/drava/examples/tomogan/dataset
# expected files:
#   ~/drava/examples/tomogan/dataset/demo-dataset-real.h5
#   ~/drava/examples/tomogan/dataset/testjob-it00500.h5
```

To regenerate the checkpoint on the cluster, the original training
script writes generator checkpoints usable directly by the Drava app:

```shell
cd ~/drava/examples/tomogan/tf2
python main-gan.py -gpus=0 -expName=testjob -dsfn=../dataset/demo-dataset-real.h5
export DRAVA_TOMOGAN_MODEL_PATH=$PWD/../dataset/testjob-it00500.h5
```

The dataset and model paths can be overridden via `TOMOGAN_DATASET_PATH` /
`DRAVA_TOMOGAN_MODEL_PATH`. Run the energy benchmark (uses the bundled
`config.nats`, which sets `max_payload=8MB` for the multi-MB frames):

```shell
cd ~/drava/examples/tomogan
python benchmark.py --batches 2,4,8,16 --thread-list 2,4,8 \
    --num-frames 512 --runs 3 --rate-hz 0 --gpu-sample-interval-s 0.2
```

## 8. Reproducing the paper

All paper experiments and their exact commands are in [docs/paper.md](paper.md).

## Setting up the test dependencies (Check + Bats)

The C runtime tests use [Check](https://libcheck.github.io/check/); the
integration tests use [Bats](https://bats-core.readthedocs.io/).

```shell
# Check
wget https://github.com/libcheck/check/archive/refs/tags/0.15.2.zip
unzip 0.15.2.zip && cd check-0.15.2
module load cmake
mkdir build-gcc && cd build-gcc
CC=gcc CXX=g++ cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/opt/check-0.15.2
make -j && make install
cd ~

# Bats
git clone https://github.com/bats-core/bats-core.git
cd bats-core && git checkout v1.13.0
./install.sh "$HOME/opt/bats-1.13.0"
cd ~
```

Environment (add to the shell profile):

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
