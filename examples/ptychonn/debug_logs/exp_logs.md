```shell
(no-gil-3.13) (base) ➜  ~/drava/experiments git:(feature/tomogan) ✗ python exp1_runtime_overhead.py --workload ptychonn --runs 1 --ptychonn-num-frames 10000
[exp1] writing to /home/ashovon/drava/experiments/results/exp1_20260513_205018
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 32 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 32 --stage2-callback-batch 32 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp1_20260513_205018/ptychonn_bench/b32
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=32 run=1 ...
[batch=32 run=1] starting app_stage2.py
[batch=32 run=1] starting app.py
[batch=32 run=1] starting publisher_jetstream.py
  done: publisher_fps=16867.45 stage1_fps=1054.05 stage2_fps=1094.68

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 4/4 | 10000 | 0.59 | 16867.45 | 9.49 | 1054.05 | 9.14 | 1094.68 | 9.97 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp1_20260513_205018/ptychonn_bench/b32/20260513_205018
[global] stopping nats-server
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 64 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 64 --stage2-callback-batch 64 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp1_20260513_205018/ptychonn_bench/b64
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=64 run=1 ...
[batch=64 run=1] starting app_stage2.py
[batch=64 run=1] starting app.py
[batch=64 run=1] starting publisher_jetstream.py
  done: publisher_fps=17273.41 stage1_fps=1685.48 stage2_fps=1803.29

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 4/4 | 10000 | 0.58 | 17273.41 | 5.93 | 1685.48 | 5.55 | 1803.29 | 6.42 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp1_20260513_205018/ptychonn_bench/b64/20260513_205045
[global] stopping nats-server
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 128 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 128 --stage2-callback-batch 128 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp1_20260513_205018/ptychonn_bench/b128
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=128 run=1 ...
[batch=128 run=1] starting app_stage2.py
[batch=128 run=1] starting app.py
[batch=128 run=1] starting publisher_jetstream.py
  done: publisher_fps=17363.14 stage1_fps=2801.22 stage2_fps=3213.35

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4/4 | 10000 | 0.58 | 17363.14 | 3.57 | 2801.22 | 3.11 | 3213.35 | 4.09 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp1_20260513_205018/ptychonn_bench/b128/20260513_205105
[global] stopping nats-server
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 256 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 256 --stage2-callback-batch 256 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp1_20260513_205018/ptychonn_bench/b256
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=17038.01 stage1_fps=4215.55 stage2_fps=1760.56

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4/4 | 10000 | 0.59 | 17038.01 | 2.37 | 4215.55 | 5.68 | 1760.56 | 7.09 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp1_20260513_205018/ptychonn_bench/b256/20260513_205122
[global] stopping nats-server
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 512 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 512 --stage2-callback-batch 512 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp1_20260513_205018/ptychonn_bench/b512
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=512 run=1 ...
[batch=512 run=1] starting app_stage2.py
[batch=512 run=1] starting app.py
[batch=512 run=1] starting publisher_jetstream.py
  done: publisher_fps=16603.94 stage1_fps=5505.87 stage2_fps=839.99

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 512 | 4/4 | 10000 | 0.60 | 16603.94 | 1.82 | 5505.87 | 11.90 | 839.99 | 13.99 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp1_20260513_205018/ptychonn_bench/b512/20260513_205143
[global] stopping nats-server
[exp1] wrote 10 rows -> /home/ashovon/drava/experiments/results/exp1_20260513_205018/exp1_summary.csv
```