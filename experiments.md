# Drava Paper Experiment Index

This file is the top-level map for reproducing and auditing the submitted-paper
experiments. Experiment drivers live in `experiments/`, application code lives
under `examples/`, captured command/output logs live in `experiments/logs/`,
and figure-generation packages live in `experiments/figures/`.

Final submitted figures are collected in `figs/paper_figs/`. Drafts,
presentation-only assets, and older exploratory material are preserved under
`figs/archive/` and `experiments/archive/`.

## Runtime Message-Rate Ceiling

- Driver: `experiments/sc5_bare_runtime_ceiling.py`
- App: `examples/bare_runtime/`
- Captured log: `experiments/logs/sc5_bare_runtime_ceiling.md`
- Figure package: `experiments/figures/sc5_bare_runtime_ceiling/`
- Submitted figure: `figs/paper_figs/bare_runtime_ceiling.pdf`

Bare runtime, CPU/no-op callback path:

```shell
python experiments/sc5_bare_runtime_ceiling.py \
  --batches 8,32,128,256,512 \
  --thread-list 2,4,8 \
  --payload-bytes 1 \
  --gpu-backend none \
  --kernel-launches 1 \
  --num-frames 100000 \
  --runs 1
```

Bare runtime with blank GPU work:

```shell
python experiments/sc5_bare_runtime_ceiling.py \
  --batches 8,32,128,256,512 \
  --thread-list 2,4,8 \
  --payload-bytes 1 \
  --gpu-backend cupy \
  --kernel-launches 1 \
  --num-frames 100000 \
  --runs 1
```

Regenerate the figure:

```shell
python experiments/figures/sc5_bare_runtime_ceiling/plot_bare_runtime_ceiling.py
```

## Baseline Comparison With PvaPy

- Drava benchmark: `examples/ptychonn/archive/rough/benchmark.py`
  (single-stage driver, archived; the maintained driver is
  `examples/ptychonn/benchmark_two_stages.py`)
- PvaPy benchmark: `examples/ptychonn/pvapy_baseline/benchmark.py`
- Captured log: `experiments/logs/pvapy_drava_comparison.md`
- Figure package: `experiments/figures/pvapy_drava_comparison/`
- Submitted figure: `figs/paper_figs/pvapy_drava_ptychonn.pdf`

Example PvaPy benchmark from `examples/ptychonn/pvapy_baseline/`:

```shell
python benchmark.py \
  --batches 128,256,512 \
  --runs 1 \
  --num-frames 3600 \
  --rate-hz 1000 \
  --monitor-queue 1024 \
  --start-settle-s 2
```

Regenerate the comparison figure:

```shell
python experiments/figures/pvapy_drava_comparison/plot_pvapy_drava_ptychonn.py
```

## Manual Configuration Throughput-Latency Trade-Off

- Captured log: `experiments/logs/manual_config_throughput_latency.md`
- Figure package: `experiments/figures/manual_config/`
- Submitted figure: `figs/paper_figs/throughput_vs_latency.pdf`

Regenerate the figure package:

```shell
python experiments/figures/manual_config/plot_manual_config.py
```

The plotting script embeds the selected manual-configuration rows used for the
submitted figure.

## Observability-Guided Runtime Tuning

- Driver: `experiments/exp1_runtime_overhead.py`
- App benchmark: `examples/ptychonn/benchmark_two_stages.py`
- Captured log: `experiments/logs/exp1_runtime_observability.md`
- Result CSV: `experiments/results/exp1_20260513_205018/exp1_summary.csv`
- Figure package: `experiments/figures/exp1_runtime_observability/`
- Submitted figure: `figs/paper_figs/exp1_runtime_observability.pdf`

Example benchmark:

```shell
python experiments/exp1_runtime_overhead.py \
  --workload ptychonn \
  --runs 1 \
  --ptychonn-num-frames 10000
```

Regenerate the figure:

```shell
python experiments/figures/exp1_runtime_observability/plot_exp1_runtime_observability.py \
  experiments/results/exp1_20260513_205018/exp1_summary.csv
```

## Agentic Configuration Search

- Tuning driver: `examples/ptychonn/tune_two_stage_ytopt.py`
- Captured log: `experiments/logs/agentic_config_search.md`
- Figure package: `experiments/figures/agentic_config_search/`
- Submitted figure: `figs/paper_figs/convergence.pdf`
- Older agent prototype archive: `experiments/archive/ptychonn_agents_old/`

Example benchmark from `examples/ptychonn/`:

```shell
python tune_two_stage_ytopt.py \
  --max-evals 64 \
  --initial-points 12 \
  --batch-size 1 \
  --batches 128,256,512,1024 \
  --stage1-threads 4,8,12,16 \
  --stage2-threads 2,4,8,12 \
  --stage1-callback-batches 128,256,512,1024 \
  --stage2-callback-batches 32,64,128,256 \
  --rates 0,1000,2000,4000 \
  --timeouts-ms 100,200,500 \
  --objective pipeline_e2e_s \
  --runs 1 \
  --num-frames 10000
```

Regenerate search figures from an `aggregate.csv`:

```shell
python experiments/figures/agentic_config_search/plot_agentic_search.py \
  examples/ptychonn/tune_logs_two_stages_ytopt/<timestamp>/aggregate.csv
```

## TomoGAN GPU Energy Efficiency

- App benchmark: `examples/tomogan/benchmark.py`
- Captured energy log: `experiments/logs/tomogan_energy.md`
- Captured baseline log: `experiments/logs/tomogan_baseline.md`
- Figure package: `experiments/figures/tomogan_energy/`
- Submitted figure: `figs/paper_figs/tomogan_energy_efficiency.pdf`

The captured log records a previous run through a top-level
`experiments/sc4_tomogan_gpu_energy.py` wrapper. That wrapper is not present in
this clean checkout, so rerun through the tracked TomoGAN benchmark directly:

```shell
cd examples/tomogan
python benchmark.py \
  --batches 2,4,8,16 \
  --thread-list 2,4,8 \
  --num-frames 512 \
  --runs 3 \
  --rate-hz 0 \
  --gpu-sample-interval-s 0.2
```

Regenerate the figure:

```shell
python experiments/figures/tomogan_energy/plot_tomogan_energy_efficiency.py
```
