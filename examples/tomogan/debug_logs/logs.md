- Benchmark
```shell
(no-gil-3.13) (base) ➜  ~/drava/examples/tomogan git:(feature/tomogan) ✗ python benchmark.py --nats-command ~/nats_binary/nats-server --nats-config ~/nats_binary/config.nats --stage-config pipeline.yaml 
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running threads=yaml batch=1 run=1 ...
[batch=1 run=1] starting app.py
[batch=1 run=1] starting publisher_jetstream.py
  done: stage_fps=23.47 overhead_pct=62.05 gpu_j_per_frame=4.9274
Running threads=yaml batch=2 run=1 ...
[batch=2 run=1] starting app.py
[batch=2 run=1] starting publisher_jetstream.py
  done: stage_fps=31.99 overhead_pct=68.52 gpu_j_per_frame=4.2840
Running threads=yaml batch=4 run=1 ...
[batch=4 run=1] starting app.py
[batch=4 run=1] starting publisher_jetstream.py
  done: stage_fps=35.82 overhead_pct=70.86 gpu_j_per_frame=4.6201
Running threads=yaml batch=8 run=1 ...
[batch=8 run=1] starting app.py
[batch=8 run=1] starting publisher_jetstream.py
  done: stage_fps=94.19 overhead_pct=88.53 gpu_j_per_frame=5.9433
Running threads=yaml batch=16 run=1 ...
[batch=16 run=1] starting app.py
[batch=16 run=1] starting publisher_jetstream.py
  done: stage_fps=37.84 overhead_pct=73.78 gpu_j_per_frame=5.6122

| Batch | Threads | Frames | Stage Time (s) | Stage FPS | E2E (s) | Overhead (s) | Overhead (%) | GPU Power (W) | GPU Energy (J) | GPU J/frame | CPU RAPL (J) | Total J/frame |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4 | 16 | 0.68 | 23.47 | 1.80 | 1.11 | 62.05 | 50.64 | 78.84 | 4.9274 | n/a | 4.9274 |
| 2 | 4 | 16 | 0.50 | 31.99 | 1.59 | 1.09 | 68.52 | 53.81 | 68.54 | 4.2840 | n/a | 4.2840 |
| 4 | 4 | 16 | 0.45 | 35.82 | 1.53 | 1.09 | 70.86 | 59.58 | 73.92 | 4.6201 | n/a | 4.6201 |
| 8 | 4 | 16 | 0.17 | 94.19 | 1.48 | 1.31 | 88.53 | 80.60 | 95.09 | 5.9433 | n/a | 5.9433 |
| 16 | 4 | 16 | 0.42 | 37.84 | 1.61 | 1.19 | 73.78 | 71.82 | 89.79 | 5.6122 | n/a | 5.6122 |

| Batch | Threads | Runs | Frames | Stage FPS mean +/- std | E2E mean (s) | Overhead mean (%) | Total J/frame mean |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4 | 1 | 16 | 23.47 +/- 0.00 | 1.80 | 62.05 | 4.9274 |
| 2 | 4 | 1 | 16 | 31.99 +/- 0.00 | 1.59 | 68.52 | 4.2840 |
| 4 | 4 | 1 | 16 | 35.82 +/- 0.00 | 1.53 | 70.86 | 4.6201 |
| 8 | 4 | 1 | 16 | 94.19 +/- 0.00 | 1.48 | 88.53 | 5.9433 |
| 16 | 4 | 1 | 16 | 37.84 +/- 0.00 | 1.61 | 73.78 | 5.6122 |

Logs and summary written to: /home/ashovon/drava/examples/tomogan/bench_logs/20260513_211728
[global] stopping nats-server



python benchmark.py --nats-command ~/nats_binary/nats-server --nats-config ~/nats_binary/config.nats --batches 1,2,4,8 --runs 2


| Batch | Threads | Frames | Stage Time (s) | Stage FPS | E2E (s) | GPU Power (W) | GPU Energy (J) | GPU J/frame | CPU RAPL (J) | Total J/frame |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4 | 16 | 3.19 | 5.01 | 4.27 | 41.63 | 172.37 | 10.7732 | n/a | 10.7732 |
| 1 | 4 | 16 | 3.13 | 5.11 | 4.20 | 44.10 | 182.38 | 11.3988 | n/a | 11.3988 |
| 2 | 4 | 16 | 2.96 | 5.40 | 4.07 | 45.61 | 178.88 | 11.1799 | n/a | 11.1799 |
| 2 | 4 | 16 | 3.20 | 5.00 | 4.35 | 52.22 | 228.13 | 14.2584 | n/a | 14.2584 |
| 4 | 4 | 16 | 2.88 | 5.56 | 4.00 | 51.73 | 198.57 | 12.4109 | n/a | 12.4109 |
| 4 | 4 | 16 | 2.85 | 5.61 | 3.95 | 52.05 | 201.93 | 12.6203 | n/a | 12.6203 |
| 8 | 4 | 16 | 2.62 | 6.11 | 3.96 | 58.76 | 227.00 | 14.1873 | n/a | 14.1873 |
| 8 | 4 | 16 | 2.62 | 6.12 | 4.02 | 65.10 | 256.36 | 16.0227 | n/a | 16.0227 |

```