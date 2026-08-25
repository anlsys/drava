## PtychoNN Example

This example demonstrates an end-to-end inference workflow for PtychoNN (TF v2) using Drava as the runtime.
Diffraction patches are sent from a publisher in batches, transported through Drava using either
JetStream or a Unix domain socket, and consumed by the application.

The application accumulates all
incoming patches and runs inference once on the complete dataset, followed by stitching and MSE
evaluation.


### Dataset and model

The example uses test data and pre-trained weights from the official PtychoNN dataset hosted on
Hugging Face.

Input data:
- X_test.npy  
  Shape: (N, 64, 64, 1)  # N = 3600
  Each entry is a diffraction patch used as input to the network.

Model selection:
- wts4/min_epoch.npy  
  Contains the epoch index of the best-performing model during training.

Model file:
- wts4/weights.<min_epoch>.hdf5  
  This is the actual Keras model file. The network has two outputs:
    - predicted amplitude
    - predicted phase

### Downloading required data and files
Before running the example, download the required files using the Hugging Face Hub API.
```shell 
cd examples/ptychonn
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python download_partial.py
```

## Build

Follow the build instructions for Drava from the root [README file](../../README.md). To ensure Jetstream support, put the `NATS_ROOT` path in the environment variable.

Add the build directory to `PYTHONPATH` before running the app.
```shell
cd ~/drava/build-debug-nats # the build dir
export PYTHONPATH="$(pwd):$PYTHONPATH"
```


## Transport layers

Transport layer → Drava → app.py

Supported transport layers:

- JetStream (NATS JetStream)
- Socket (Unix domain socket)

Both ultimately deliver raw frame bytes to `app.py` (no JSON/base64).

## JetStream Transport

JetStream → (pull) → Drava → (push) → app.py

1. Publisher [publisher_jetstream.py](publisher_jetstream.py):
    - Loads `X_test.npy`.
    - Publishes each frame as raw `float32` bytes (`64x64x1`, row-major) to `frames.raw`.
2. Transport Layer (JetStream + Drava runtime):
    - JetStream provides a reliable messaging backend.
    - Drava receives the raw message from the JetStream device.
    - Drava groups incoming frames into internal batches (fixed at 128) and invokes the Python callback.

3. Application (`app.py`):
    - Loads the PtychoNN `.hdf5` model once at startup.
    - Callback decodes incoming batches into `(B, 64, 64, 1)` tensors.
    - Callback runs inference on each batch.
    - Registers callback with `drava.register_routine_py(func)`.

### Run using Jetstream

- In terminal 1, run the NATS server

```shell
cd ~/nats_binary
./nats-server -js
```

- In terminal 2, run the publisher script

```shell
cd examples/ptychonn
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python publisher_jetstream.py
```

- In terminal 3, point the runtime at the stage config (transport type comes from `transport.type` in `pipeline.yaml`, set to `nats`) and run the app:

```shell
cd examples/ptychonn
source venv/bin/activate
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml
export DRAVA_STAGE_NAME=stage1
python app.py
```
## Socket Transport

The socket backend provides a lightweight alternative to JetStream using a Unix domain socket.
The data flow is:

```shell
publisher_socket.py → FIFO (/tmp/drava_in) → socat → /tmp/accel_2048.sock → Drava → app.py
```

For socket mode, each frame is written as:
`[4-byte big-endian length][raw frame bytes]`.

### Run using Socket

- In terminal 1, create the FIFO and start `socat` to forward FIFO input into the socket:

```shell
# Create the FIFO if it doesn't already exist (suppress error if it does)
mkfifo /tmp/drava_in 2>/dev/null || true

# Start socat to forward everything from the FIFO into the Unix domain socket
socat /tmp/drava_in UNIX-LISTEN:/tmp/accel_2048.sock,fork
```

- In terminal 2, run the publisher script

```shell
cd examples/ptychonn
python -m venv venv
source venv/bin/activate
# JLSE Interactive node
# pip install --proxy http://proxy.ftm.alcf.anl.gov:3128 -r requirements.txt
pip install -r requirements.txt
python publisher_socket.py
```

- In terminal 3, set `transport.type: socket` in `pipeline.yaml`, then point the runtime at it and run the app:

```shell
cd examples/ptychonn
source venv/bin/activate
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml
export DRAVA_STAGE_NAME=stage1
python app.py
```

### Benchmark

Paper experiment logs and figure-generation scripts are organized from the
repository root:

- Experiment index: [../../experiments.md](../../experiments.md)
- Preserved logs: [../../experiments/logs](../../experiments/logs)
- Figure packages: [../../experiments/figures](../../experiments/figures)

- In JLSE compute node
```shell
source ~/drava_nvidia.sh
source ~/venvs/no-gil-3.13/bin/activate
cd ~/drava/build
export XKAAPI_VERBOSE=4
export PYTHONPATH="$(pwd):$PYTHONPATH" # so that the build dir is in the Python path
# Transport, threads, streams, etc. come from pipeline.yaml; the benchmark
# driver sets DRAVA_STAGE_CONFIG/DRAVA_STAGE_NAME on the app subprocess for you.
cd ../examples/ptychonn

# The maintained driver is benchmark_two_stages.py (it regenerates a per-run
# pipeline.yaml so --threads/--batches actually reach the runtime). The old
# single-stage benchmark.py is archived under archive/rough/ for paper
# reproducibility only.

python3 benchmark_two_stages.py \
  --batches 256 \
  --runs 1 \
  --num-frames 10000 \
  --threads 4 \
  --timeout-ms 200 \
  --nats-url nats://127.0.0.1:4222 \
  --rate-hz 1000 \
  --input-stream FRAMES \
  --input-subject frames.raw \
  --output-stream PREDICTIONS \
  --output-subject frames.stage1
  
  python tune_two_stage_ytopt.py --max-evals 6 --initial-points 8 --batches 256,512 --stage1-threads 4,8,16 --stage2-threads 2,4,8 --stage1-callback-batches 256,512 --stage2-callback-batches 64,128,256 --objective pipeline_e2e_s


```

### References
- [PtychoNN Github repository](https://github.com/mcherukara/PtychoNN)
- [PtychoNN HuggingFace repository](https://huggingface.co/datasets/mcherukara/PtychoNN_data/tree/main)
- Cherukara, M. J., Zhou, T., Nashed, Y., Enfedaque, P., Hexemer, A., Harder, R. J., & Holt, M. V. (2020). AI-enabled high-resolution scanning coherent diffraction imaging. Applied Physics Letters, 117(4).
