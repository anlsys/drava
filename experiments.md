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


### Baseline comparison with PvaPy
- Logs: [examples/ptychonn/debug_logs/pvapy_logs.md](examples/ptychonn/debug_logs/pvapy_logs.md)
- App code: [examples/ptychonn/pvapy_baseline/benchmark.py](examples/ptychonn/pvapy_baseline/benchmark.py)
- Example benchmark from [examples/ptychonn/pvapy_baseline/](examples/ptychonn/pvapy_baseline/) folder:
- Chart generation: [experiments/figures/pvapy_drava_comparison](experiments/figures/pvapy_drava_comparison)
- Example benchmark
```shell
python benchmark.py \
  --batches 128,256,512 \
  --runs 1 \
  --num-frames 3600 \
  --rate-hz 1000 \
  --monitor-queue 1024 \
  --start-settle-s 2
```
- Figure: [figs/paper_figs/pvapy_drava_ptychonn.pdf](figs/paper_figs/pvapy_drava_ptychonn.pdf)

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
- Example benchmark:
```shell
python experiments/sc4_tomogan_gpu_energy.py \
--batches 2,4,8,16 \
--thread-list 2,4,8 \
--num-frames 512 \
--runs 3 \
--rate-hz 0
```
- Chart generation: [experiments/figures/tomogan_energy/plot_tomogan_energy_efficiency.py](experiments/figures/tomogan_energy/plot_tomogan_energy_efficiency.py)
- Figure: [figs/paper_figs/tomogan_energy_efficiency.pdf](figs/paper_figs/tomogan_energy_efficiency.pdf)
