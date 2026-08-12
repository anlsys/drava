# Artifact Description (AD): Drava

This Artifact Description follows the SC reproducibility-initiative structure. It
describes how to obtain, build, run, and reproduce the results in the paper
"Drava: An Event-Driven Runtime for Scientific Pipelines" (XLOOP @ SC26).

> Double-blind note: this AD is anonymized. Repository and dataset links are
> given as anonymized artifact links; do not add the de-anonymizing GitHub or
> institutional URLs until the paper is de-anonymized.

---

## 1. Abstract

Drava is an event-driven runtime for scientific streaming pipelines at the edge.
The artifact contains the Drava runtime (C/C++ on top of XKRT with Python
bindings), two representative applications (PtychoNN two-stage ptychography and
TomoGAN tomographic denoising), a pvaPy baseline for the PtychoNN pipeline, and
the benchmark/plot scripts that regenerate every figure and table in the paper.
Experiments run on a single GPU node (representative edge / near-facility
inference node) and measure throughput, end-to-end latency, GPU + CPU energy,
and an agentic (ytopt) configuration search.

## 2. Artifact check-list (meta-information)

- **Program:** Drava runtime; PtychoNN and TomoGAN inference pipelines; pvaPy baseline.
- **Compilation:** LLVM/Clang >= 20 (C++20), CMake.
- **Runtime environment:** Linux; CUDA 12.3; free-threaded CPython 3.13; NATS server (JetStream).
- **Hardware:** 1 GPU node. Paper used a JLSE node: dual-socket AMD EPYC 7532, 256 GB DDR4, 1x NVIDIA A100-PCIE-40GB.
- **Metrics:** frames/s (throughput), end-to-end latency (s), GPU energy (J and frames/J), CPU package energy (J), GPU+CPU total energy (frames/J).
- **Output:** per-run CSV summaries, power-vs-time traces, and PDF/PNG figures.
- **Experiments:** runtime message-rate ceiling; PvaPy vs Drava (single + two-stage); manual config sweep; observability sweep; agentic (ytopt) search; TomoGAN energy.
- **How much disk:** ~5 GB (models, datasets, build).
- **How much time to prepare:** ~1-2 h (build + deps + data).
- **How much time to run (full):** ~4-8 h for all sweeps at `--runs 10`.
- **Publicly available:** Yes (anonymized artifact link).
- **Code license:** see `LICENSE`.
- **Workflow framework:** none required; plain Python/bash drivers.

## 3. Description

### 3.1 How to access
Clone the anonymized artifact and check out the paper branch:

```shell
git clone <ANONYMIZED-ARTIFACT-URL> drava
cd drava
git checkout paper/xloop
```

### 3.2 Hardware dependencies
- One node with an NVIDIA A100 (or comparable) GPU.
- x86-64 CPU with the `power/energy-pkg/` perf event (AMD EPYC or Intel) for CPU
  energy. `perf` must be usable (`kernel.perf_event_paranoid <= 1`).

### 3.3 Software dependencies
- LLVM/Clang >= 20, CMake, CUDA 12.3, cuDNN 9.19.
- XKRT runtime, `yaml-cpp`, NATS C client + `nats-server` (v2.11+), SWIG 4.4.1.
- Python 3.13 (free-threaded), TensorFlow 2.20, Keras 3.12, NumPy 2.3, h5py, nats-py, PyYAML.
- For the pvaPy baseline: `pvapy==5.6.0` (module name `pvaccess`).
- For autotuning: `ytopt`.

### 3.4 Datasets / models
- PtychoNN: pretrained Keras/HDF5 weights + partial data via
  `examples/ptychonn/download_partial.py` (public dataset).
- TomoGAN: pretrained generator + 16 preprocessed 1024x1024 slice pairs.
- Throughput runs use deterministic PRNG-generated frames of the real shapes.

## 4. Installation

Follow the top-level `README.md` (Build Drava) and, on JLSE, the module setup
in that README. Summary:

```shell
# Modules (JLSE)
module use /soft/modulefiles
module load spack/gcc-0.6.1
module use /home/<user>/shared/modules   # XKRT modules
module load llvm/master-nightly cmake intel/oneapi/release/2024.1 cuda/12.3.0 hwloc
module load xkaapi/<hash>/Debug-cuda swig/4.4.1 python/3.13-no-gil

# yaml-cpp and NATS C client: see README.md

# Build Drava
export NATS_ROOT=$HOME/opt/nats
mkdir build-debug-nats && cd build-debug-nats
CC=clang CXX=clang++ cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j
export PYTHONPATH="$(pwd):$PYTHONPATH"
```

## 5. Experiment workflow

All experiments and their exact commands are indexed in `experiments.md`. Each
benchmark writes a timestamped `bench_logs*/` (or `experiments/results/`)
directory with per-run logs and a `summary.csv`; plot scripts consume those CSVs
and emit PDF/PNG into `figs/paper_figs/`.

Reproducibility policy: the bulky per-run run directories (`bench_logs*/`,
`experiments/results/`) are git-ignored. The curated figure-source CSVs that
regenerate every plot are committed under `experiments/figures/<experiment>/`
(e.g., `tomogan_energy/tomogan_energy_efficiency_data.csv` and
`tomogan_energy/sample_power_trace_b*.csv`). To refresh a figure after a new
run, copy the relevant `summary.csv`/`power_trace_*.csv` from the run directory
into the matching `experiments/figures/<experiment>/` file and re-run the plot
script.

The two experiments highlighted for this revision are detailed in
Sections 7.1 (TomoGAN energy) and 7.2 (two-stage PvaPy) below.

## 6. Evaluation and expected results

- PvaPy vs Drava: Drava is loss-free at publisher rates where PvaPy drops
  frames, and reaches up to ~2.36x higher unpaced throughput.
- Runtime message-rate ceiling: ~31k frames/s once callback batches are large.
- Observability sweep: end-to-end optimum differs from the GPU-inference optimum
  (up to ~2.44x throughput improvement from batching-aware tuning).
- Agentic search: ytopt finds a config ~2.24x faster than the best manual one
  while sampling 0.52% of the space.
- TomoGAN energy: throughput and energy efficiency (frames/J) do not scale
  identically with batch size (non-monotonic efficiency).

Small run-to-run variation is expected; report mean +/- std over `--runs 10`.

## 7. Detailed re-run instructions (this revision)

### 7.1 TomoGAN energy (GPU + CPU), 10 runs, with power traces

Measures **GPU energy** (integrated `nvidia-smi` power) and **CPU package
energy** (`perf stat -e power/energy-pkg/`). On JLSE AMD EPYC the RAPL powercap
sysfs is not readable, so `perf` is required for CPU energy.

Preflight (must print Joules):

```shell
perf stat -e power/energy-pkg/ sleep 1
nvidia-smi -L
# If perf shows <not supported>: sudo sysctl -w kernel.perf_event_paranoid=1
```

Run (from `examples/tomogan`, NATS + venv active):

```shell
cd examples/tomogan
python benchmark.py \
  --batches 2,4,8,16 \
  --thread-list 2 \
  --num-frames 512 \
  --runs 10 \
  --rate-hz 0 \
  --cpu-energy-source perf \
  --perf-interval-ms 200 \
  --save-power-trace
```

Outputs (under `bench_logs/<timestamp>/`):
- `summary.csv` with per-run `gpu_energy_j_per_frame`, `cpu_energy_j`,
  `cpu_energy_j_per_frame`, `total_energy_j_per_frame`, `stage_fps`, and
  `cpu_energy_source`.
- `power_trace_b<batch>_r<run>.csv`: GPU/CPU power-vs-time samples.

Regenerate figures:

```shell
# Efficiency bars (frames/J, GPU+CPU if present) + throughput line, mean +/- std.
# Point the plot's data CSV at the new summary (or copy the needed columns into
# experiments/figures/tomogan_energy/tomogan_energy_efficiency_data.csv).
python experiments/figures/tomogan_energy/plot_tomogan_energy_efficiency.py

# Power-vs-time line chart for one representative run:
python experiments/figures/tomogan_energy/plot_tomogan_power_trace.py \
  examples/tomogan/bench_logs/<timestamp>/power_trace_b16_r1.csv
```

### 7.2 Two-stage PvaPy vs Drava (PtychoNN), 10 runs

Runs the full PtychoNN pipeline (stage 1 GPU inference + stage 2 stitching) on
both runtimes with identical science, for end-to-end latency and per-stage
throughput.

PvaPy side (`examples/ptychonn/pvapy_baseline`, venv active):

```shell
cd examples/ptychonn/pvapy_baseline
# Single-stage ingest curve (paced), loss point appears near 3 kHz:
for R in 100 200 1000 2000 2500 3000; do
  python benchmark.py --batches 128,256,512 --runs 10 --num-frames 3600 \
    --rate-hz $R --monitor-queue 1024 --start-settle-s 2
done
# Two-stage pipeline:
python benchmark_two_stage.py --batches 128,256,512 --runs 10 \
  --num-frames 3600 --rate-hz 1000 --monitor-queue 1024 --start-settle-s 2
```

Drava side (`examples/ptychonn`, NATS running), matching sweep + unpaced:

```shell
cd examples/ptychonn
for R in 100 200 1000 2000 2500 3000 0; do
  python benchmark.py --batches 128,256,512 --runs 10 --num-frames 3600 \
    --rate-hz $R --threads 4 --timeout-ms 200 --stage-config pipeline.yaml
done
```

Aggregate both `summary.csv` files by `batch`/`rate`, take mean/std of
`stage1_total_fps`, `stage2_total_fps`, and `pipeline_e2e_s`, and plot with
error bars. Chart script referenced in `experiments.md` (Baseline comparison
with PvaPy).

## 8. Notes / caveats

- Single-node scope is deliberate (isolates runtime behavior from network
  variability); multi-node transport is future work.
- The simple pvaPy `PvaServer` record path overwrites the current PV value under
  load; use paced `--rate-hz` (and/or `--monitor-queue`) for loss-free points.
- ytopt search is a one-time offline cost that amortizes over production runs.

## 9. How the AD maps to paper artifacts

| Paper item | Driver | Plot | Output figure |
|---|---|---|---|
| Runtime ceiling | `experiments/sc5_bare_runtime_ceiling.py` | `experiments/figures/sc5_bare_runtime_ceiling` | `bare_runtime_ceiling.pdf` |
| PvaPy vs Drava (1-stage) | `pvapy_baseline/benchmark.py` + `ptychonn/benchmark.py` | `experiments/figures/pvapy_drava_comparison` | `pvapy_drava_ptychonn.pdf` |
| PvaPy vs Drava (2-stage) | `pvapy_baseline/benchmark_two_stage.py` | (aggregate summary.csv) | (revision) |
| Manual config sweep | `ptychonn/visualize_manual_config.py` | same | `throughput_vs_latency.pdf` |
| Observability sweep | `experiments/exp1_runtime_overhead.py` | `experiments/visualize_exp1_runtime_observability.py` | `exp1_runtime_observability.pdf` |
| Agentic search | `ptychonn/tune_two_stage_ytopt.py` | `ptychonn/visualize_agentic_search.py` | `convergence.pdf` |
| TomoGAN energy | `tomogan/benchmark.py` | `tomogan_energy/plot_tomogan_energy_efficiency.py` | `tomogan_energy_efficiency.pdf` |
| TomoGAN power trace | `tomogan/benchmark.py --save-power-trace` | `tomogan_energy/plot_tomogan_power_trace.py` | (revision) |
