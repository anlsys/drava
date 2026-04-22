
# TomoGAN

## Drava Example

This folder also includes a Drava-oriented wrapper around the original TomoGAN TF2 code. The
original files under `tf2/` and `dataset/` are unchanged; the new files (`app.py`,
`publisher_jetstream.py`, `publisher_socket.py`, `publisher_util.py`, `config.py`,
`pipeline.yaml`) provide a streaming example similar to `examples/ptychonn`.

### What the Drava wrapper does

- `publisher_jetstream.py` publishes raw `float32` tomography frames from
  `dataset/demo-dataset-real.h5:test_ns` into JetStream.
- `publisher_socket.py` publishes the same data through the socket/FIFO transport.
- `app.py` receives batched frames through Drava, loads the trained `.h5` model file, runs
  `model.predict(...)`, and writes
  an output HDF5 file containing:
  - `ns`: noisy input frames
  - `dn`: denoised predictions
  - `gt`: ground truth frames when `test_gt` is present

### Model path

This example now defaults to the trained checkpoint generated from the sample dataset:

```shell
scp -r /Users/arshovon/Codes/drava_Code/drava/examples/tomogan/dataset jlse:/home/ashovon/drava/examples/tomogan/dataset
examples/tomogan/dataset/testjob-it00500.h5
```

So if that file is present, you can run the example without setting any extra model-path variable.
You can still override it through:

```shell
export DRAVA_TOMOGAN_MODEL_PATH=/path/to/tomogan-generator.h5
```

### Recommended workflow for TomoGAN

For TomoGAN, the closest equivalent to the PtychoNN example is:

1. Use the provided sample dataset in `dataset/demo-dataset-real.h5`.
2. Use the trained checkpoint produced from that same dataset.
3. Use the provided input dataset in `dataset/demo-dataset-real.h5` for the default
   end-to-end Drava example.

In your current setup, that trained checkpoint is already available:

```shell
examples/tomogan/dataset/testjob-it00500.h5
```

If you ever need to regenerate it on the cluster, the original training script already saves
generator checkpoints that can be used directly by the Drava app:

```shell
cd examples/tomogan/tf2
python main-gan.py -gpus=0 -expName=testjob -dsfn=../dataset/demo-dataset-real.h5
export DRAVA_TOMOGAN_MODEL_PATH=$PWD/../dataset/testjob-it00500.h5
```

### Dataset-only input path

This example uses only the provided sample dataset as publisher input. There is no synthetic input
path in the default workflow.

By default, the publisher reads the frame count directly from `test_ns` in
`dataset/demo-dataset-real.h5`, so you do not need to set `num_frames` in `pipeline.yaml` for the
real-dataset path.

If you want to send more frames than the dataset contains, set `DRAVA_PUBLISH_NUM_FRAMES`; the
publisher will loop over the same dataset frames.

Recommended split:

- Functional example: real TomoGAN model file + real sample dataset.
- Throughput benchmark: same model file + repeated dataset frames with a fixed
  `DRAVA_PUBLISH_NUM_FRAMES` and `DRAVA_PUBLISH_RATE_HZ`.

### Install

```shell
cd examples/tomogan
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Build Drava

Follow the build instructions from the root `README.md`, and make sure the Drava build directory is
in `PYTHONPATH` before running the app:

```shell
cd ~/drava/build-debug-nats
export PYTHONPATH="$(pwd):$PYTHONPATH"
```

### Run with JetStream

Terminal 1:

```shell
cd ~/nats_binary
./nats-server -js
```

Terminal 2:

```shell
cd examples/tomogan
source venv/bin/activate
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml
python publisher_jetstream.py
```

Terminal 3:

```shell
cd examples/tomogan
source venv/bin/activate
export DRAVA_TRANSPORT=nats
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml
python app.py
```

By default the app writes `drava_tomogan_output.h5` in this folder.

### Run with Socket

Terminal 1:

```shell
mkfifo /tmp/drava_in 2>/dev/null || true
socat /tmp/drava_in UNIX-LISTEN:/tmp/accel_2048.sock,fork
```

Terminal 2:

```shell
cd examples/tomogan
source venv/bin/activate
python publisher_socket.py
```

Terminal 3:

```shell
cd examples/tomogan
source venv/bin/activate
export DRAVA_TRANSPORT=socket
python app.py
```
