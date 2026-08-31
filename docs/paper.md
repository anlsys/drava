# Drava Paper Experiments

Top-level map for reproducing and auditing the submitted-paper experiments.
Experiment drivers live in `experiments/`, application code under `examples/`,
captured command/output logs in `experiments/logs/`, and figure-generation
packages in `experiments/figures/`. Final submitted figures are collected in
`docs/figures/paper_figs/`; drafts and older exploratory material are under
`docs/figures/archive/` and `experiments/archive/`.

All commands assume Drava is built and importable (see [docs/jlse.md](jlse.md))
and are run from the repository root unless noted. Each stage's runtime knobs
(threads, batch sizes, streams) come from `pipeline.yaml`; benchmark CLI flags
override them per run.

The paper results were measured on a **single GPU node** (dual-socket AMD EPYC
7532, 256 GB, one NVIDIA A100-PCIE-40GB), representative of a near-facility or
edge inference node. Absolute numbers depend on the node; small run-to-run and
node-to-node variation is expected.

## Verifying a run against the paper

The paper's per-run measurements are committed under
`experiments/figures/<experiment>/`. To compare a fresh benchmark's `summary.csv`
against that reference and print the percent difference per configuration:

```shell
python experiments/compare_to_paper.py tomogan-energy \
    examples/tomogan/bench_logs/<timestamp>/summary.csv
```

This is a reproducibility check, not a pass/fail gate: differences within roughly
10–15% are normal across nodes and runs.

---

## 1. Runtime message-rate ceiling

- Driver: `experiments/bare_runtime_ceiling.py`
- App: `examples/bare_runtime/`
- Log: `experiments/logs/sc5_bare_runtime_ceiling.md`
- Figure package: `experiments/figures/sc5_bare_runtime_ceiling/`
- Submitted figure: `docs/figures/paper_figs/bare_runtime_ceiling.pdf`

Bare runtime, CPU / no-op callback path:

```shell
python experiments/bare_runtime_ceiling.py \
  --batches 8,32,128,256,512 --thread-list 2,4,8 \
  --payload-bytes 1 --gpu-backend none --kernel-launches 1 \
  --num-frames 100000 --runs 1
```

Bare runtime with blank GPU work:

```shell
python experiments/bare_runtime_ceiling.py \
  --batches 8,32,128,256,512 --thread-list 2,4,8 \
  --payload-bytes 1 --gpu-backend cupy --kernel-launches 1 \
  --num-frames 100000 --runs 1
```

Regenerate the figure:

```shell
python experiments/figures/sc5_bare_runtime_ceiling/plot_bare_runtime_ceiling.py
```

---

## 2. TomoGAN GPU energy efficiency

- App benchmark: `examples/tomogan/benchmark.py`
- Logs: `experiments/logs/tomogan_energy.md`, `experiments/logs/tomogan_baseline.md`
- Figure package: `experiments/figures/tomogan_energy/`
- Submitted figure: `docs/figures/paper_figs/tomogan_energy_efficiency.pdf`

```shell
cd examples/tomogan
python benchmark.py \
  --batches 2,4,8,16 --thread-list 2,4,8 \
  --num-frames 512 --runs 3 --rate-hz 0 \
  --gpu-sample-interval-s 0.2
```

If the benchmark cannot find NATS automatically, pass it explicitly:

```shell
python benchmark.py --batches 2,4,8,16 --thread-list 2,4,8 --num-frames 512 \
  --runs 3 --rate-hz 0 --gpu-sample-interval-s 0.2 \
  --nats-command ~/nats_binary/nats-server --nats-config ~/nats_binary/config.nats
```

Regenerate the figure:

```shell
python experiments/figures/tomogan_energy/plot_tomogan_energy_efficiency.py
```

---

## 3. Baseline comparison with PvaPy

- Drava benchmark: `examples/ptychonn/benchmark_two_stages.py`
  (the archived single-stage driver used originally is at
  `examples/ptychonn/archive/rough/benchmark.py`)
- PvaPy benchmark: `examples/ptychonn/pvapy_baseline/benchmark.py`
- Log: `experiments/logs/pvapy_drava_comparison.md`
- Figure package: `experiments/figures/pvapy_drava_comparison/`
- Submitted figure: `docs/figures/paper_figs/pvapy_drava_ptychonn.pdf`

Drava arm (two-stage):

```shell
cd examples/ptychonn
python benchmark_two_stages.py \
  --batches 128,256,512 --runs 1 --num-frames 3600 \
  --threads 4 --timeout-ms 200 --rate-hz 1000 \
  --nats-url nats://127.0.0.1:4222
```

PvaPy arm:

```shell
cd examples/ptychonn/pvapy_baseline
python benchmark.py \
  --batches 128,256,512 --runs 1 --num-frames 3600 \
  --rate-hz 1000 --monitor-queue 1024 --start-settle-s 2
```

Regenerate the figure:

```shell
python experiments/figures/pvapy_drava_comparison/plot_pvapy_drava_ptychonn.py
```

---

## 4. Observability-guided runtime tuning

- Driver: `experiments/runtime_overhead.py`
- App benchmark: `examples/ptychonn/benchmark_two_stages.py`
- Log: `experiments/logs/exp1_runtime_observability.md`
- Result CSV: `experiments/results/exp1_20260513_205018/exp1_summary.csv`
- Figure package: `experiments/figures/exp1_runtime_observability/`
- Submitted figure: `docs/figures/paper_figs/exp1_runtime_observability.pdf`

```shell
python experiments/runtime_overhead.py \
  --workload ptychonn --runs 1 --ptychonn-num-frames 10000
```

Regenerate the figure:

```shell
python experiments/figures/exp1_runtime_observability/plot_exp1_runtime_observability.py \
  experiments/results/exp1_20260513_205018/exp1_summary.csv
```

---

## 5. Agentic configuration search

- Tuning driver: `examples/ptychonn/tune_two_stage_ytopt.py`
- Log: `experiments/logs/agentic_config_search.md`
- Figure package: `experiments/figures/agentic_config_search/`
- Submitted figure: `docs/figures/paper_figs/convergence.pdf`
- Older agent prototype: `experiments/archive/ptychonn_agents_old/`

```shell
cd examples/ptychonn
python tune_two_stage_ytopt.py \
  --max-evals 64 --initial-points 12 --batch-size 1 \
  --batches 128,256,512,1024 \
  --stage1-threads 4,8,12,16 --stage2-threads 2,4,8,12 \
  --stage1-callback-batches 128,256,512,1024 \
  --stage2-callback-batches 32,64,128,256 \
  --rates 0,1000,2000,4000 --timeouts-ms 100,200,500 \
  --objective pipeline_e2e_s --runs 1 --num-frames 10000
```

Regenerate search figures from an `aggregate.csv`:

```shell
python experiments/figures/agentic_config_search/plot_agentic_search.py \
  examples/ptychonn/tune_logs_two_stages_ytopt/<timestamp>/aggregate.csv
```

---

## 6. Manual configuration throughput–latency trade-off

- Log: `experiments/logs/manual_config_throughput_latency.md`
- Figure package: `experiments/figures/manual_config/`
- Submitted figure: `docs/figures/paper_figs/throughput_vs_latency.pdf`

The plotting script embeds the selected manual-configuration rows used for the
submitted figure:

```shell
python experiments/figures/manual_config/plot_manual_config.py
```
