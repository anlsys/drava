# Running Drava examples

Drava ships several example applications under [examples/](../examples). Each is a
stage callback (`app.py`) plus a `pipeline.yaml`, fed by a data-source publisher.
This page covers how to run them; for the full JLSE walkthrough with datasets see
[docs/jlse.md](jlse.md).

| Example | Stages | Notes |
|---|---|---|
| [PtychoNN](../examples/ptychonn) | 2 | Ptychographic inference; dataset + weights from Hugging Face. |
| [TomoGAN](../examples/tomogan) | 1 | Tomographic denoising; multi-MB frames + energy reporting. |
| [Bare runtime](../examples/bare_runtime) | 1 | Message-rate ceiling; no model. |
| [Iris KNN](../examples/iris_knn) | 1 | Minimal single-row inference. |
| [Dataflow](../examples/dataflow) | 1 | Minimal transport demo. |

## Prerequisites

- Drava built and importable ([docs/build.md](build.md) or [docs/jlse.md](jlse.md)),
  with the build directory on `PYTHONPATH`.
- The example's Python deps installed (`pip install -r examples/<name>/requirements.txt`).
- For the JetStream transport, a reachable NATS server.

## The two required environment variables

The runtime reads only these for stage identity (everything else is in
`pipeline.yaml`):

```shell
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml   # which config
export DRAVA_STAGE_NAME=stage1                 # which stage in it
```

See [docs/configuration.md](configuration.md) for the full list of variables and
precedence.

## Running a pipeline manually

Using JetStream (start `nats-server -js` first — note some examples need a larger
`max_payload`; the bundled `nats.conf` / `config.nats` set 8 MB):

```shell
cd examples/ptychonn

# stage 1
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml DRAVA_STAGE_NAME=stage1
python app.py

# stage 2 (separate terminal)
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml DRAVA_STAGE_NAME=stage2
python app_stage2.py

# data source (separate terminal)
python publisher_jetstream.py
```

## Running via the benchmark driver

The example benchmark drivers start NATS, wire the stages, run repeated
configurations, and report throughput (and energy for TomoGAN):

```shell
# PtychoNN two-stage
cd examples/ptychonn
python benchmark_two_stages.py --batches 256 --runs 1 --num-frames 10000 \
    --threads 4 --rate-hz 1000 --nats-url nats://127.0.0.1:4222

# TomoGAN (uses the bundled config.nats with max_payload=8MB)
cd examples/tomogan
python benchmark.py --batches 2,4,8,16 --thread-list 2,4,8 \
    --num-frames 512 --runs 3 --rate-hz 0 --gpu-sample-interval-s 0.2
```

## Socket transport

Set `transport.type: socket` in the example's `pipeline.yaml`, create the FIFO,
and bridge it to a Unix socket with `socat`:

```shell
mkfifo /tmp/drava_in 2>/dev/null || true
socat /tmp/drava_in UNIX-LISTEN:/tmp/accel_2048.sock,fork
# then run app.py and publisher_socket.py as above
```

## Datasets and models

- **PtychoNN** — `python examples/ptychonn/download_partial.py` fetches the test
  frames and one weight file from the
  [PtychoNN_data](https://huggingface.co/datasets/mcherukara/PtychoNN_data)
  Hugging Face dataset into `examples/ptychonn/PtychoNN_data_partial/`.
- **TomoGAN** — expects `examples/tomogan/dataset/demo-dataset-real.h5` (input)
  and `examples/tomogan/dataset/testjob-it00500.h5` (generator checkpoint).
  Override with `TOMOGAN_DATASET_PATH` / `DRAVA_TOMOGAN_MODEL_PATH`. See
  [docs/jlse.md](jlse.md#7-tomogan-dataset--model-weights).

Each example directory has its own README with app-specific details.
