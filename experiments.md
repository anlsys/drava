### Runtime message-rate ceiling
- Experiment code and docs: [experiments/sc5_bare_runtime_ceiling.py](experiments/sc5_bare_runtime_ceiling.py)
- App code, docs, logs: [examples/bare_runtime](examples/bare_runtime)
- Logs: [examples/bare_runtime/logs/bare.md](examples/bare_runtime/logs/bare.md)
- Chart generation: [experiments/figures/sc5_bare_runtime_ceiling](experiments/figures/sc5_bare_runtime_ceiling)
- Bare runtime (no-op)
```shell
python experiments/sc5_bare_runtime_ceiling.py \
  --batches 8,32,128,256,512 \
  --thread-list 2,4,8 \
  --payload-bytes 1 \
  --gpu-backend auto \
  --kernel-launches 1 \
  --num-frames 100000 \
  --runs 1
```
- Bare runtime (cupy)
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
- Figure: [figs/paper_figs/bare_runtime_ceiling.pdf](figs/paper_figs/bare_runtime_ceiling.pdf)


### Baseline comparison with PvaPy (single- and two-stage)

Throughput vs. publisher rate, PvaPy vs. Drava, for both the single-stage
PtychoNN inference stream and the full two-stage pipeline (inference + stitch).
Combined into one figure with two panels.

- pvaPy code: [examples/ptychonn/pvapy_baseline/](examples/ptychonn/pvapy_baseline/)
  (`benchmark.py` single-stage; `benchmark_two_stage.py` + `consumer_stage2.py` two-stage)
- Drava two-stage: [examples/ptychonn/benchmark_two_stages.py](examples/ptychonn/benchmark_two_stages.py)
- Curated data: `experiments/figures/pvapy_drava_comparison/`
  (`pvapy_drava_ptychonn.csv` single-stage; `pvapy_two_stage_summary.csv` and
  `drava_two_stage_summary.csv` two-stage)
- Combined plot: [experiments/figures/pvapy_drava_comparison/plot_pvapy_drava_combined.py](experiments/figures/pvapy_drava_comparison/plot_pvapy_drava_combined.py)
- Figure: [figs/paper_figs/pvapy_drava_combined.pdf](figs/paper_figs/pvapy_drava_combined.pdf)
- Findings: PvaPy's single overwrite-record path is loss-free only up to 2 kHz in
  both configs; above that it drops frames (single stage) or drops stage-boundary
  messages so the stitch never completes (two stage). Drava is loss-free and
  scales through the unpaced ("max") rate in both.

Single-stage sweep (pvaPy + Drava written to one CSV via the harness):
```shell
cd examples/ptychonn/pvapy_baseline
for R in 1000 2000 2500 3000 0; do
  python benchmark.py --batches 128,256,512 --runs 5 \
    --num-frames 3600 --rate-hz $R --monitor-queue 1024 --start-settle-s 2
done
```
Note: the single-stage metric (`stage_total_fps`) is measured inside the consumer
(first-receive to last-callback) and is independent of harness/publisher startup,
so it did not need re-running after the two-stage end-to-end timing fix.

Two-stage sweep, fixed batch 128 (the figure panel (b) sweep):
```shell
# pvaPy
cd examples/ptychonn/pvapy_baseline
for R in 1000 2000 2500 3000 0; do
  python benchmark_two_stage.py --batches 128 --runs 5 \
    --num-frames 3600 --rate-hz $R --monitor-queue 1024 --start-settle-s 2
done
# Drava
cd examples/ptychonn
for R in 1000 2000 2500 3000 0; do
  python benchmark_two_stages.py --batches 128 --runs 5 \
    --num-frames 3600 --rate-hz $R --threads 4 --timeout-ms 200 --stage-config pipeline.yaml
done
```
Regenerate the combined figure:
```shell
python experiments/figures/pvapy_drava_comparison/plot_pvapy_drava_combined.py --batch 128
```

### Manual configurations throughput-latency trade-off
- Chart generation: [examples/ptychonn/visualize_manual_config.py](examples/ptychonn/visualize_manual_config.py)
- Figure: [figs/paper_figs/throughput_vs_latency.pdf](figs/paper_figs/throughput_vs_latency.pdf)

### Observability guided runtime tuning
- Logs: [examples/ptychonn/debug_logs/exp_logs.md](examples/ptychonn/debug_logs/exp_logs.md)
- Benchmark code: [experiments/exp1_runtime_overhead.py](experiments/exp1_runtime_overhead.py)
- Example benchmark:
```shell
python experiments/exp1_runtime_overhead.py --workload ptychonn --runs 1 --ptychonn-num-frames 10000
```
- Chart generation: [experiments/visualize_exp1_runtime_observability.py](experiments/visualize_exp1_runtime_observability.py)
- Figure: [figs/paper_figs/exp1_runtime_observability.pdf](figs/paper_figs/exp1_runtime_observability.pdf)


### Agentic configuration search
- Logs: [examples/ptychonn/debug_logs/ytopt_logs.md](examples/ptychonn/debug_logs/ytopt_logs.md)
- App code: [examples/ptychonn/tune_two_stage_ytopt.py](examples/ptychonn/tune_two_stage_ytopt.py)
- Example benchmark:
```shell
cd examples/ptychonn
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
- Chart generation: [examples/ptychonn/visualize_agentic_search.py](examples/ptychonn/visualize_agentic_search.py)
- Figure: [figs/paper_figs/convergence.pdf](figs/paper_figs/convergence.pdf)


### Energy efficiency
- Logs: [examples/tomogan/debug_logs/energy_logs.md](examples/tomogan/debug_logs/energy_logs.md)
- App/benchmark code: [examples/tomogan/benchmark.py](examples/tomogan/benchmark.py)
- Measures **GPU energy** by integrating `nvidia-smi` power samples, and **CPU
  package energy** via `perf stat -e power/energy-pkg/` (default
  `--cpu-energy-source auto`, which prefers `perf` and falls back to RAPL
  powercap sysfs). On JLSE AMD EPYC nodes the RAPL sysfs is not readable, so
  `perf` is required for CPU energy; `perf` needs
  `kernel.perf_event_paranoid <= 1` (verify with
  `perf stat -e power/energy-pkg/ sleep 1`).
- Example benchmark (GPU + CPU energy, 10 runs, with power-vs-time trace):
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
- Efficiency chart: [experiments/figures/tomogan_energy/plot_tomogan_energy_efficiency.py](experiments/figures/tomogan_energy/plot_tomogan_energy_efficiency.py)
  (auto-uses GPU+CPU `total_energy_j_per_frame` when present, else GPU-only;
  bars/line show mean +/- std over the runs)
- Power-vs-time chart: [experiments/figures/tomogan_energy/plot_tomogan_power_trace.py](experiments/figures/tomogan_energy/plot_tomogan_power_trace.py)
  (input: `power_trace_*.csv` from `--save-power-trace`)
- Figure: [figs/paper_figs/tomogan_energy_efficiency.pdf](figs/paper_figs/tomogan_energy_efficiency.pdf)
