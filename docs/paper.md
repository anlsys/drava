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

## Known issue: intermittent crash during long sweeps

During long multi-configuration sweeps (many stage processes launched back to
back), a stage occasionally crashes during XKRT team startup — observed as
`pure virtual method called` / `terminate called without an active exception`, or
a SIGSEGV — before any frames are processed. It is **intermittent**: rerunning
the same configuration on its own succeeds and matches the reference data
(including the 8-thread points, which reproduce the paper). The likely cause is a
transient during rapid process churn / accumulated transport state across runs,
under investigation.

Workarounds: run configurations in smaller groups (e.g. one thread count at a
time), or rerun a failed cell individually. This does not affect the correctness
of the numbers that do complete, and is not a benchmark or configuration error.

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

The submitted energy figure was measured at **2 worker threads** across batch
sizes; that is the configuration to reproduce:

```shell
cd examples/tomogan
python benchmark.py \
  --batches 2,4,8,16 --thread-list 2 \
  --num-frames 512 --runs 5 --rate-hz 0 \
  --gpu-sample-interval-s 0.2
```

To also sweep higher thread counts (not part of the submitted figure), extend
`--thread-list`, e.g. `--thread-list 2,4,8`.

Regenerate the figure:

```shell
python experiments/figures/tomogan_energy/plot_tomogan_energy_efficiency.py
```

---

## 3. Baseline comparison with PvaPy

- Drava benchmark: `examples/ptychonn/benchmark_two_stages.py`
  (the archived single-stage driver used originally is at
  `examples/ptychonn/archive/rough/benchmark.py`)
- PvaPy benchmarks: `examples/ptychonn/pvapy_baseline/` (`benchmark.py`,
  `benchmark_two_stage.py`, `benchmark_hpc_two_stage.py`)
- Log: `experiments/logs/pvapy_drava_comparison.md`
- Figure package: `experiments/figures/pvapy_drava_comparison/`
- Submitted figures: `docs/figures/paper_figs/pvapy_drava_ptychonn.pdf`,
  `pvapy_drava_two_stage.pdf`, `pvapy_distributor_scaling.pdf`

**Finding.** The comparison sweeps the publisher rate. A single PvaPy consumer
keeps up and stays loss-free up to about 2000 Hz; beyond that it drops frames
(e.g. at 2500 Hz it misses frames and effective throughput collapses). Drava
completes the same stream loss-free across all tested rates, including the
uncapped (max-rate) case. The PvaPy **HPC distributor** (multiple consumers
behind a distributor plugin) sustains higher rates by fanning frames across
consumers, at the cost of added consumers; its scaling is reported separately.

Reproducing the sweep requires running each rate. The reference data used rates
`1000, 2000, 2500, 3000` Hz (plus uncapped for Drava) and `--runs 5`.

Drava arm (per rate; loop the rate values):

```shell
cd examples/ptychonn
for r in 1000 2000 2500 3000; do
  python benchmark_two_stages.py --batches 128,256,512 --runs 5 --num-frames 3600 \
    --threads 4 --timeout-ms 200 --rate-hz "$r" --nats-url nats://127.0.0.1:4222
done
```

PvaPy single-consumer arm (per rate):

```shell
cd examples/ptychonn/pvapy_baseline
for r in 1000 2000 2500 3000; do
  python benchmark.py --batches 128,256,512 --runs 5 --num-frames 3600 \
    --rate-hz "$r" --monitor-queue 1024 --start-settle-s 2
done
```

PvaPy HPC distributor scaling (consumer and rate sweep):

```shell
cd examples/ptychonn/pvapy_baseline
python benchmark_hpc_two_stage.py \
  --n-consumers 1,2,4,8 --rate-hz 1000,2000,2500,3000 \
  --num-frames 3600 --runs 3
```

Regenerate the figures:

```shell
python experiments/figures/pvapy_drava_comparison/plot_pvapy_drava_ptychonn.py
python experiments/figures/pvapy_drava_comparison/plot_pvapy_drava_two_stage.py
python experiments/figures/pvapy_drava_comparison/plot_pvapy_distributor_scaling.py
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
