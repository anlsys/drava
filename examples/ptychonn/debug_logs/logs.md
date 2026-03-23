### A 100
- Tuner
```shell
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/multi-stage) ✗ python3 tune_two_stage.py \
  --batches 256,512 \
  --stage1-threads 4,8 \
  --stage2-threads 4 \  
  --stage1-callback-batches 256 \    
  --stage2-callback-batches 32,64 \ 
  --rates 0 \
  --runs 1 \
  --timeout-ms 200 \
  --num-frames 10000 \
  --objective pipeline_e2e_s \
  --top-k 10 \
  --keep-going
Running 8 configurations serially.

[1/8] batch=256 s1_threads=4 s2_threads=4 s1_cb=256 s2_cb=32 rate_hz=0.0
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=17140.16 stage1_fps=3911.09 stage2_fps=1703.22

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4/4 | 10000 | 0.58 | 17140.16 | 2.56 | 3911.09 | 5.87 | 1703.22 | 6.45 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165334
[global] stopping nats-server

[2/8] batch=256 s1_threads=4 s2_threads=4 s1_cb=256 s2_cb=64 rate_hz=0.0
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=16844.53 stage1_fps=4090.01 stage2_fps=1726.54

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4/4 | 10000 | 0.59 | 16844.53 | 2.44 | 4090.01 | 5.79 | 1726.54 | 6.41 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165356
[global] stopping nats-server

[3/8] batch=256 s1_threads=8 s2_threads=4 s1_cb=256 s2_cb=32 rate_hz=0.0
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=16056.66 stage1_fps=4341.31 stage2_fps=941.69

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 8/4 | 10000 | 0.62 | 16056.66 | 2.30 | 4341.31 | 10.62 | 941.69 | 11.22 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165415
[global] stopping nats-server

[4/8] batch=256 s1_threads=8 s2_threads=4 s1_cb=256 s2_cb=64 rate_hz=0.0
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=16936.74 stage1_fps=4320.34 stage2_fps=1066.13

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 8/4 | 10000 | 0.59 | 16936.74 | 2.31 | 4320.34 | 9.38 | 1066.13 | 10.06 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165439
[global] stopping nats-server

[5/8] batch=512 s1_threads=4 s2_threads=4 s1_cb=256 s2_cb=32 rate_hz=0.0
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=512 run=1 ...
[batch=512 run=1] starting app_stage2.py
[batch=512 run=1] starting app.py
[batch=512 run=1] starting publisher_jetstream.py
  done: publisher_fps=16041.55 stage1_fps=5560.56 stage2_fps=828.03

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 512 | 4/4 | 10000 | 0.62 | 16041.55 | 1.80 | 5560.56 | 12.08 | 828.03 | 12.67 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165503
[global] stopping nats-server

[6/8] batch=512 s1_threads=4 s2_threads=4 s1_cb=256 s2_cb=64 rate_hz=0.0
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=512 run=1 ...
[batch=512 run=1] starting app_stage2.py
[batch=512 run=1] starting app.py
[batch=512 run=1] starting publisher_jetstream.py
  done: publisher_fps=16285.13 stage1_fps=5402.49 stage2_fps=1016.21

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 512 | 4/4 | 10000 | 0.61 | 16285.13 | 1.85 | 5402.49 | 9.84 | 1016.21 | 10.48 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165528
[global] stopping nats-server

[7/8] batch=512 s1_threads=8 s2_threads=4 s1_cb=256 s2_cb=32 rate_hz=0.0
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=512 run=1 ...
[batch=512 run=1] starting app_stage2.py
[batch=512 run=1] starting app.py
[batch=512 run=1] starting publisher_jetstream.py
  done: publisher_fps=15814.64 stage1_fps=4870.20 stage2_fps=1146.80

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 512 | 8/4 | 10000 | 0.63 | 15814.64 | 2.05 | 4870.20 | 8.72 | 1146.80 | 9.42 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165551
[global] stopping nats-server

[8/8] batch=512 s1_threads=8 s2_threads=4 s1_cb=256 s2_cb=64 rate_hz=0.0
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=512 run=1 ...
[batch=512 run=1] starting app_stage2.py
[batch=512 run=1] starting app.py
[batch=512 run=1] starting publisher_jetstream.py

Logs written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165614
[global] stopping nats-server

Recorded 1 failures in: /home/ashovon/drava/examples/ptychonn/tune_logs_two_stages/20260323_165334/failures.csv

| Rank | Batch | Threads S1/S2 | Callback S1/S2 | Rate Hz | Publisher FPS | Stage1 FPS | Stage2 FPS | Pipeline E2E (s) | Summary |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 256 | 4/4 | 256/64 | 0.00 | 16844.53 | 4090.01 | 1726.54 | 6.41 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165356 |
| 2 | 256 | 4/4 | 256/32 | 0.00 | 17140.16 | 3911.09 | 1703.22 | 6.45 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165334 |
| 3 | 512 | 8/4 | 256/32 | 0.00 | 15814.64 | 4870.20 | 1146.80 | 9.42 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165551 |
| 4 | 256 | 8/4 | 256/64 | 0.00 | 16936.74 | 4320.34 | 1066.13 | 10.06 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165439 |
| 5 | 512 | 4/4 | 256/64 | 0.00 | 16285.13 | 5402.49 | 1016.21 | 10.48 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165528 |
| 6 | 256 | 8/4 | 256/32 | 0.00 | 16056.66 | 4341.31 | 941.69 | 11.22 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165415 |
| 7 | 512 | 4/4 | 256/32 | 0.00 | 16041.55 | 5560.56 | 828.03 | 12.67 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_165503 |

Sorted by `pipeline_e2e_s`.

Chart generation skipped: matplotlib unavailable (No module named 'matplotlib')

Aggregate CSV written to: /home/ashovon/drava/examples/ptychonn/tune_logs_two_stages/20260323_165334/aggregate.csv
Tuner logs written to: /home/ashovon/drava/examples/ptychonn/tune_logs_two_stages/20260323_165334
```
- async publish
```shell

| Batch | Threads | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4 | 10000 | 0.59 | 16847.42 | 2.56 | 3904.28 | 5.57 | 1795.66 | 7.05 |
| 256 | 20 | 10000 | 0.60 | 16650.72 | 2.52 | 3962.59 | 6.15 | 1626.81 | 7.50 |
| 512 | 4 | 10000 | 0.61 | 16513.94 | 1.84 | 5439.77 | 11.30 | 885.06 | 13.43 |
| 512 | 20 | 10000 | 0.62 | 16094.58 | 2.07 | 4821.92 | 11.15 | 897.07 | 12.77 |


(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/multi-stage) ✗ python3 benchmark_two_stages.py \
  --batches 256 \
  --runs 1 \
  --threads 4 \
  --timeout-ms 200 \
  --num-frames 10000 \
  --rate-hz 0
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=16847.42 stage1_fps=3904.28 stage2_fps=1795.66

| Batch | Threads | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4 | 10000 | 0.59 | 16847.42 | 2.56 | 3904.28 | 5.57 | 1795.66 | 7.05 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_151538
[global] stopping nats-server
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/multi-stage) ✗ python3 benchmark_two_stages.py \
  --batches 256 \
  --runs 1 \
  --threads 20 \
  --timeout-ms 200 \
  --num-frames 10000 \
  --rate-hz 0
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=16650.72 stage1_fps=3962.59 stage2_fps=1626.81

| Batch | Threads | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 20 | 10000 | 0.60 | 16650.72 | 2.52 | 3962.59 | 6.15 | 1626.81 | 7.50 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260323_151613
[global] stopping nats-server

```
- Main file, publish memory
```shell
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/multi-stage) ✗ python3 benchmark_two_stages.py \
  --batches 256 \
  --runs 1 \
  --threads 4 \
  --timeout-ms 200 \
  --num-frames 10000 \
  --rate-hz 5000
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=4995.92 stage1_fps=1798.17 stage2_fps=707.13

| Batch | Threads | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage1 Compute (s) | Stage1 Publish (s) | Stage2 Time (s) | Stage2 FPS | Stage2 Callback (s) | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4 | 10000 | 2.00 | 4995.92 | 5.56 | 1798.17 | 4.87 | 0.48 | 14.14 | 707.13 | 14.02 | 16.34 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260319_191003
[global] stopping nats-server
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/multi-stage) ✗ python3 benchmark_two_stages.py \
  --batches 256 \
  --runs 1 \
  --threads 4 \
  --timeout-ms 200 \
  --num-frames 10000 \
  --rate-hz 10000
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=9980.63 stage1_fps=1821.61 stage2_fps=714.51

| Batch | Threads | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage1 Compute (s) | Stage1 Publish (s) | Stage2 Time (s) | Stage2 FPS | Stage2 Callback (s) | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4 | 10000 | 1.00 | 9980.63 | 5.49 | 1821.61 | 4.84 | 0.45 | 14.00 | 714.51 | 13.87 | 16.17 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260319_191112
[global] stopping nats-server
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/multi-stage) ✗ python3 benchmark_two_stages.py \
  --batches 256 \
  --runs 1 \
  --threads 4 \
  --timeout-ms 200 \
  --num-frames 10000 \
  --rate-hz 0    
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=21182.63 stage1_fps=1833.21 stage2_fps=718.41

| Batch | Threads | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage1 Compute (s) | Stage1 Publish (s) | Stage2 Time (s) | Stage2 FPS | Stage2 Callback (s) | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4 | 10000 | 0.47 | 21182.63 | 5.45 | 1833.21 | 4.81 | 0.45 | 13.92 | 718.41 | 13.80 | 16.12 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260319_192025
[global] stopping nats-server

```
- Bench config + batch on drava
```shell
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/multi-stage) ✗ python3 benchmark_two_stages.py \
  --batches 256 \
  --runs 1 \
  --threads 4 \
  --timeout-ms 200 \
  --num-frames 10000 \
  --rate-hz 1500
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=1499.50 stage1_fps=1295.30 stage2_fps=701.72

| Batch | Threads | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage1 Compute (s) | Stage1 Publish (s) | Stage2 Time (s) | Stage2 FPS | Stage2 Callback (s) | Stage2 Side | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4 | 10000 | 6.67 | 1499.50 | 7.72 | 1295.30 | 4.87 | 0.47 | 14.25 | 701.72 | 14.13 | 100 | 17.46 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260317_184122
[global] stopping nats-server
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/multi-stage) ✗ python3 benchmark_two_stages.py \
  --batches 256 \
  --runs 1 \
  --threads 4 \
  --timeout-ms 200 \
  --num-frames 10000 \
  --rate-hz 5000
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=4995.72 stage1_fps=1814.73 stage2_fps=708.00

| Batch | Threads | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage1 Compute (s) | Stage1 Publish (s) | Stage2 Time (s) | Stage2 FPS | Stage2 Callback (s) | Stage2 Side | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4 | 10000 | 2.00 | 4995.72 | 5.51 | 1814.73 | 4.87 | 0.44 | 14.12 | 708.00 | 14.00 | 100 | 16.32 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260317_184312
[global] stopping nats-server
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/multi-stage) ✗ python3 benchmark_two_stages.py \
  --batches 256 \
  --runs 1 \
  --threads 4 \
  --timeout-ms 200 \
  --num-frames 10000 \
  --rate-hz 10000
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=9978.74 stage1_fps=1817.24 stage2_fps=702.93

| Batch | Threads | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage1 Compute (s) | Stage1 Publish (s) | Stage2 Time (s) | Stage2 FPS | Stage2 Callback (s) | Stage2 Side | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4 | 10000 | 1.00 | 9978.74 | 5.50 | 1817.24 | 4.85 | 0.45 | 14.23 | 702.93 | 14.10 | 100 | 16.42 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260317_184516
[global] stopping nats-server


python3 benchmark_two_stages.py \
  --batches 256 \
  --runs 1 \
  --threads 4 \
  --timeout-ms 200 \
  --rate-hz 1000


(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/multi-stage) ✗ python3 benchmark_two_stages.py \
  --batches 256 \
  --runs 1 \
  --duration-s 8 \
  --threads 4 \
  --timeout-ms 200 \
  --rate-hz 1000
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=1011.56 stage1_fps=911.24 stage2_fps=706.06

| Batch | Threads | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage1 Compute (s) | Stage1 Publish (s) | Stage2 Time (s) | Stage2 FPS | Stage2 Callback (s) | Stage2 Side | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4 | 8100 | 8.01 | 1011.56 | 8.89 | 911.24 | 4.09 | 0.28 | 11.47 | 706.06 | 9.05 | 90 | 16.03 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260317_155653
[global] stopping nats-server
```
- Bench (with config)
```shell
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/multi-stage) ✗ python3 benchmark_two_stages.py \
  --batches 256 \
  --runs 1 \
  --duration-s 8 \
  --threads 4 \
  --timeout-ms 200 \
  --rate-hz 1000
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=1011.60 stage1_rx_fps=909.97 stage2_frame_fps=841.30

| Batch | Threads | Timeout (ms) | Frames | Publisher FPS | Stage1 RX FPS | Stage1 Stage Avg (ms) | Stage2 Frame FPS | Stage2 Stage Avg (ms) | Stage2 RX Msgs | Stage2 Side | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4 | 200 | 8100 | 1011.60 | 909.97 | 123.05 | 841.30 | 0.00 | 496 | 90 | 13.10 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260314_225604
[global] stopping nats-server
```
- New bench (without config)
```shell
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/multi-stage) ✗ python3 benchmark.py \
  --batches 256 \
  --runs 1 \
  --duration-s 10 \
  --threads 4 \
  --timeout-ms 200 \
  --rate-hz 1000 \
  --nats-url nats://127.0.0.1:4222

[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app.py
[batch=256 run=1] app ready
[batch=256 run=1] starting publisher_jetstream.py
[batch=256 run=1] publisher finished
[batch=256 run=1] waiting for app final (timeout=120.0s)
[batch=256 run=1] app final received
  done: publisher_avg_fps=999.81 stage1_infer_avg_fps=904.28

| Batch | Threads | Timeout (ms) | Total Frames | Publisher Avg FPS | Stage1 Infer FPS | Stage1 Publish FPS | Stage1 E2E FPS | Publisher Time (s) | Stage1 E2E (s) | GPU Avg (%) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4 | 200 | 10000 | 999.81 | 904.28 | 911.24 | 904.21 | 10.00 | 11.06 | 10.00 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs/20260314_163327
[global] stopping nats-server


(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/multi-stage) ✗ python3 benchmark_two_stages.py \
  --batches 256 \
  --runs 1 \
  --duration-s 8 \
  --threads 4 \
  --timeout-ms 200 \
  --nats-url nats://127.0.0.1:4222 \
  --rate-hz 1000 \
  --input-stream FRAMES \
  --input-subject frames.raw \
  --output-stream PREDICTIONS \
  --output-subject frames.stage1

[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=1011.54 stage1_infer_fps=898.20 stage2_consume_fps=851.59

| Batch | Threads | Timeout (ms) | Frames | Publisher FPS | Stage1 Infer FPS | Stage1 Publish FPS | Stage1 E2E FPS | Stage2 Consume FPS | Stage2 Stitch (s) | Stage2 Side | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4 | 200 | 8100 | 1011.54 | 898.20 | 906.20 | 898.11 | 851.59 | 0.12 | 90 | 10.50 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260314_163608
[global] stopping nats-server


```
- 2 stage
```shell
Published count=175104 seq=208121 win_fps=21774.55 avg_fps=21856.69
Square completion: n_raw=175104 side=419 n_square=175561 extra=457
Done: published 175561 frames in 8.033s (avg_fps=21855.41) seq=208578 eos_seq=208579 Last frame sent at: 2853307.117681778

[81.900096] [TID=44040] [LOGGER] [INFO] [stage1] frames=175561 batch=256 step_ms=303.30 infer_avg_fps=2423.20 published_frames=175561 published_msgs=10973 publish_avg_fps=2426.42
[81.900129] [TID=44040] [LOGGER] [INFO] [stage1-final] frames=175561 expected_frames=175561 frame0_arrival_s=2853299.129231 last_infer_done_s=2853371.580180 end_to_end_latency_s=72.450949 infer_avg_fps=2423.20 publish_avg_fps=2426.42 e2e_fps=2423.17


=175353 capacity=175561 finalized=0
[78.489554] [TID=44122] [LOGGER] [INFO] [stage2] received=175369/175561 consume_avg_fps=2463.61
[78.489859] [TID=44122] [LOGGER] [INFO] [stage2] waiting_for_expected job_id=1 expected=175561 unique_received=175385 total_received=175385 capacity=175561 finalized=0
[78.489964] [TID=44122] [LOGGER] [INFO] [stage2] waiting_for_expected job_id=1 expected=175561 unique_received=175401 total_received=175401 capacity=175561 finalized=0
[78.490066] [TID=44122] [LOGGER] [INFO] [stage2] waiting_for_expected job_id=1 expected=175561 unique_received=175417 total_received=175417 capacity=175561 finalized=0
[78.490162] [TID=44122] [LOGGER] [INFO] [stage2] waiting_for_expected job_id=1 expected=175561 unique_received=175433 total_received=175433 capacity=175561 finalized=0
[78.490324] [TID=44122] [LOGGER] [INFO] [stage2] waiting_for_expected job_id=1 expected=175561 unique_received=175449 total_received=175449 capacity=175561 finalized=0
[78.490469] [TID=44122] [LOGGER] [INFO] [stage2] waiting_for_expected job_id=1 expected=175561 unique_received=175465 total_received=175465 capacity=175561 finalized=0
[78.490616] [TID=44122] [LOGGER] [INFO] [stage2] waiting_for_expected job_id=1 expected=175561 unique_received=175481 total_received=175481 capacity=175561 finalized=0
[78.490764] [TID=44122] [LOGGER] [INFO] [stage2] waiting_for_expected job_id=1 expected=175561 unique_received=175497 total_received=175497 capacity=175561 finalized=0
[78.490914] [TID=44122] [LOGGER] [INFO] [stage2] waiting_for_expected job_id=1 expected=175561 unique_received=175513 total_received=175513 capacity=175561 finalized=0
[78.491093] [TID=44122] [LOGGER] [INFO] [stage2] waiting_for_expected job_id=1 expected=175561 unique_received=175529 total_received=175529 capacity=175561 finalized=0
[78.491287] [TID=44122] [LOGGER] [INFO] [stage2] waiting_for_expected job_id=1 expected=175561 unique_received=175545 total_received=175545 capacity=175561 finalized=0
[81.050336] [TID=44122] [LOGGER] [INFO] [stage2-final] frames=175561 stitched_frames=175561 stitch_side=419 consume_avg_fps=2466.24 stitch_time_s=2.559 amp_shape=(1257, 1257) phi_shape=(1257, 1257)

---
Published count=9216 seq=30600 win_fps=999.91 avg_fps=999.92
Square completion: n_raw=10000 side=100 n_square=10000 extra=0
Done: published 10000 frames in 10.002s (avg_fps=999.81) seq=31395 eos_seq=31396 Last frame sent at: 2851374.15498543

[57.054146] [TID=13113] [LOGGER] [INFO] [stage1] frames=10000 batch=16 step_ms=205.48 infer_avg_fps=227.67 published_frames=10000 published_msgs=625 publish_avg_fps=228.03
[57.054178] [TID=13113] [LOGGER] [INFO] [stage1-final] frames=10000 expected_frames=10000 frame0_arrival_s=2851364.169312 last_infer_done_s=2851408.093473 end_to_end_latency_s=43.924161 infer_avg_fps=227.67 publish_avg_fps=228.03 e2e_fps=227.67

[48.051626] [TID=13213] [LOGGER] [INFO] [stage2] received=9968/10000 consume_avg_fps=233.62
[48.674307] [TID=13212] [LOGGER] [INFO] [stage2] received=9984/10000 consume_avg_fps=230.63
[48.674551] [TID=13212] [LOGGER] [INFO] [stage2] received=10000/10000 consume_avg_fps=230.99
[48.820188] [TID=13212] [LOGGER] [INFO] [stage2-final] frames=10000 stitched_frames=10000 stitch_side=100 consume_avg_fps=230.99 stitch_time_s=0.146 amp_shape=(300, 300) phi_shape=(300, 300)


```
- Using asycn publish
```shell
python benchmark.py \
  --batches 128 \
  --timeout-ms 100 \
  --threads 24 \
  --xkaapi-verbose 4 \
  --rate-hz 0 \
  --duration-s 30 \
  --runs 1
```
| Batch | Threads | Timeout (ms) | Total Frames | Publisher Avg FPS | Drava Avg FPS | Publisher Time (s) | Drava E2E (s) | GPU Avg (%) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 24 | 100 | 592896 | 19733.71 | 4624.33 | 30.05 | 128.21 | 28.13 |
| 256 | 24 | 100 | 582656 | 19395.97 | 7662.66 | 30.04 | 76.04 | 30.05 |
| 512 | 24 | 100 | 602112 | 20064.40 | 11489.34 | 30.01 | 52.41 | 40.10 |
| 1024 | 24 | 100 | 653312 | 21774.68 | 9803.00 | 30.00 | 66.64 | 28.97 |
| 1024 | 64 | 100 | 670720 | 22329.43 | 9841.97 | 30.04 | 68.15 | 28.89 |
| 512 | 16 | 100 | 613376 | 20420.18 | 11452.87 | 30.04 | 53.56 | 36.24 |
| 512 | 4 | 100 | 653312 | 21753.58 | 7930.69 | 30.03 | 82.38 | 26.64 |
| 512 | 16 | 100 | 591872 | 19702.36 | 11612.68 | 30.04 | 50.97 | 33.30 |
| 512 | 20 | 100 | 586752 | 19548.77 | 11487.21 | 30.02 | 51.08 | 43.86 |
| 512 | 24 | 100 | 602112 | 20064.40 | 11489.34 | 30.01 | 52.41 | 40.10 |
| 512 | 32 | 100 | 608357 | 20275.02 | 11294.76 | 30.00 | 53.86 | 33.13 |
| 512 | 40 | 100 | 587776 | 19560.77 | 11146.73 | 30.05 | 52.73 | 34.15 |
| 512 | 48 | 100 | 605184 | 20146.84 | 11134.94 | 30.04 | 54.35 | 43.05 |

- Using Memory storage for JS

| Batch | Threads | Timeout (ms) | Total Frames | Publisher Avg FPS | Drava Avg FPS | Publisher Time (s) | Drava E2E (s) | GPU Avg (%) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4 | 200 | 198242 | 6607.96 | 3066.53 | 30.00 | 64.65 | 10.48 |
| 256 | 4 | 200 | 199579 | 6652.49 | 5179.74 | 30.00 | 38.53 | 15.92 |
| 512 | 4 | 200 | 199990 | 6666.20 | 6414.30 | 30.00 | 31.18 | 21.17 |
| 128 | 8 | 200 | 198152 | 6604.94 | 4067.66 | 30.00 | 48.71 | 12.86 |
| 256 | 8 | 200 | 200513 | 6683.63 | 6435.24 | 30.00 | 31.16 | 12.78 |
| 512 | 8 | 200 | 199194 | 6639.65 | 6390.47 | 30.00 | 31.17 | 18.86 |
| 128 | 16 | 200 | 197666 | 6588.73 | 4528.53 | 30.00 | 43.65 | 7.00 |
| 256 | 16 | 200 | 197901 | 6596.57 | 6321.22 | 30.00 | 31.31 | 12.52 |
| 512 | 16 | 200 | 200344 | 6677.99 | 6362.96 | 30.00 | 31.49 | 18.07 |


- If I run app.py and publisher together:

| BATCH SIZE | TIMEOUT (ms) | PUBLISHER AVG FPS | DRAVA AVG FPS | DRAVA END-TO-END LATENCY (s) | GPU USAGE |
|---|---:|---:|---:|---:|----------:|
| 128 | 500 | 3233.44 | 3016.56 | 53.595563 |    ~5–10% |
| 256 | 500 | 3201.78 | 3129.66 | 51.152798 |    ~5–10% |
| 512 | 500 | 3246.82 | 3150.06 | 51.536503 |   ~5–10%  |


- If I run app.py after publishing the frames:

  | BATCH SIZE | TIMEOUT (ms) | PUBLISHER AVG FPS | DRAVA AVG FPS | DRAVA END-TO-END LATENCY (s) | GPU USAGE |
  |---|---:|---:|---:|---:|---:|
  | 128 | 500 | 3372.10 | 2982.18 | 33.923193 | ~16% |
  | 256 | 500 | 3335.92 | 5098.45 | 19.629492 | ~27% |
  | 512 (Run 1) | 500 | 3329.63 | 7813.42 | 12.792471 | ~70% |
  | 512 (Run 2) | 500 | 3308.55 | 7802.35 | 12.732826 | ~50% |
  | 1024 | 500 | 3291.23 | 1973.82 | 50.024287 | ~18% |



- Random
```shell
# after
export DRAVA_THREADS=2
export DRAVA_INFER_BATCH=512
export DRAVA_JS_FETCH_BATCH=512
export DRAVA_FETCH_TIMEOUT_MS=200
export DRAVA_PUBLISH_RATE_HZ=0
export DRAVA_PUBLISH_SYNTHETIC=1
export DRAVA_PUBLISH_DURATION_S=30


# together
export XKAAPI_VERBOSE=4
export DRAVA_TRANSPORT=nats
export DRAVA_THREADS=64         
export DRAVA_INFER_BATCH=512
export DRAVA_JS_FETCH_BATCH=512
export DRAVA_FETCH_TIMEOUT_MS=200
export DRAVA_PUBLISH_RATE_HZ=0
export DRAVA_PUBLISH_SYNTHETIC=1
export DRAVA_PUBLISH_DURATION_S=30


export DRAVA_THREADS=20         
export DRAVA_INFER_BATCH=512
export DRAVA_JS_FETCH_BATCH=512
export DRAVA_FETCH_TIMEOUT_MS=250
export DRAVA_PUBLISH_RATE_HZ=0
export DRAVA_PUBLISH_SYNTHETIC=1
export DRAVA_PUBLISH_DURATION_S=30

Done: published 199148 frames in 30.001s (avg_fps=6638.16) seq=199148 eos_seq=199149 Last frame sent at: 347099.663557688

[99.504014] [TID=1857] [LOGGER] [INFO] [final] frames=199148 expected_frames=199148 frame0_arrival_s=347069.757444 frame199148_done_s=347101.295638 end_to_end_latency_s=31.538194 final_wall_avg_fps=6314.50


python benchmark.py \
  --batches 512 \
  --timeout-ms 200 \
  --threads 20 \
  --xkaapi-verbose 4 \
  --rate-hz 0 \
  --duration-s 30 \
  --runs 1

  done: publisher_avg_fps=6674.02 drava_avg_fps=6420.27
[global] stopping nats-server

| Batch | Timeout (ms) | Total Frames | Publisher Avg FPS | Drava Avg FPS | Publisher Time (s) | Drava E2E (s) | GPU Avg (%) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 512 | 200 | 200226 | 6674.02 | 6420.27 | 30.00 | 31.19 | 18.86 |






export DRAVA_THREADS=20
export DRAVA_INFER_BATCH=512
export DRAVA_JS_FETCH_BATCH=512
export DRAVA_FETCH_TIMEOUT_MS=250
export DRAVA_PUBLISH_RATE_HZ=0
export DRAVA_PUBLISH_SYNTHETIC=1
export DRAVA_PUBLISH_DURATION_S=30

Published count=94208 seq=2137065 win_fps=6172.72 avg_fps=3194.48
Published count=94464 seq=2137321 win_fps=2296.72 avg_fps=3191.10
Published count=94720 seq=2137577 win_fps=6154.71 avg_fps=3195.25
Published count=94976 seq=2137833 win_fps=2267.27 avg_fps=3191.73
Published count=95232 seq=2138089 win_fps=5986.09 avg_fps=3195.74
Published count=95488 seq=2138345 win_fps=2266.76 avg_fps=3192.24
Published count=95744 seq=2138601 win_fps=6082.47 avg_fps=3196.30
Done: published 95880 frames in 30.045s (avg_fps=3191.17) seq=2138737 eos_seq=2138738 Last frame sent at: 265402.833048442

[62.715094] [TID=43561] [LOGGER] [INFO] [frames]=91421 batch=512 step_ms=105.23 wall_avg_fps=3194.58
[62.866393] [TID=43574] [LOGGER] [INFO] [frames]=91933 batch=512 step_ms=101.68 wall_avg_fps=3195.58
[63.019415] [TID=43559] [LOGGER] [INFO] [frames]=92445 batch=512 step_ms=101.94 wall_avg_fps=3196.37
[63.377777] [TID=43577] [LOGGER] [INFO] [frames]=92957 batch=512 step_ms=303.20 wall_avg_fps=3174.74
[63.378328] [TID=43575] [LOGGER] [INFO] [frames]=93469 batch=512 step_ms=147.70 wall_avg_fps=3192.17
[63.484496] [TID=43573] [LOGGER] [INFO] [frames]=93981 batch=512 step_ms=100.79 wall_avg_fps=3198.06
[63.635704] [TID=43562] [LOGGER] [INFO] [frames]=94493 batch=512 step_ms=99.49 wall_avg_fps=3199.02
[63.788635] [TID=43567] [LOGGER] [INFO] [frames]=95005 batch=512 step_ms=99.05 wall_avg_fps=3199.79
[63.946723] [TID=43563] [LOGGER] [INFO] [frames]=95517 batch=512 step_ms=100.69 wall_avg_fps=3199.99
[64.962891] [TID=43566] [LOGGER] [INFO] EOS received: expected_frames=95880
[64.962920] [TID=43566] [LOGGER] [INFO] [frames]=95880 batch=363 step_ms=750.30 wall_avg_fps=3106.40
[64.962928] [TID=43566] [LOGGER] [INFO] [final] frames=95880 expected_frames=95880 frame0_arrival_s=265372.961375 frame95880_done_s=265403.828244 end_to_end_latency_s=30.866869 final_wall_avg_fps=3106.24

# GPU ~18%

# after

export DRAVA_THREADS=20
export DRAVA_INFER_BATCH=512
export DRAVA_JS_FETCH_BATCH=512
export DRAVA_FETCH_TIMEOUT_MS=250
export DRAVA_PUBLISH_RATE_HZ=0
export DRAVA_PUBLISH_SYNTHETIC=1
export DRAVA_PUBLISH_DURATION_S=30
Published count=99328 seq=2238066 win_fps=6290.12 avg_fps=3337.72
Published count=99584 seq=2238322 win_fps=2302.26 avg_fps=3333.87
Published count=99840 seq=2238578 win_fps=6221.38 avg_fps=3337.84
Done: published 99965 frames in 30.001s (avg_fps=3332.10) seq=2238703 eos_seq=2238704 Last frame sent at: 265663.889583642

[11.810099] [TID=7918] [LOGGER] [INFO] [frames]=97405 batch=512 step_ms=524.14 wall_avg_fps=10773.42
[11.810507] [TID=7919] [LOGGER] [INFO] [frames]=97917 batch=512 step_ms=506.03 wall_avg_fps=10829.56
[11.811707] [TID=7933] [LOGGER] [INFO] [frames]=98429 batch=512 step_ms=517.73 wall_avg_fps=10884.75
[11.811932] [TID=7931] [LOGGER] [INFO] [frames]=98941 batch=512 step_ms=504.41 wall_avg_fps=10941.10
[11.812121] [TID=7922] [LOGGER] [INFO] [frames]=99453 batch=512 step_ms=540.08 wall_avg_fps=10997.46
[11.812511] [TID=7928] [LOGGER] [INFO] [frames]=99965 batch=512 step_ms=342.08 wall_avg_fps=11053.63
[11.812544] [TID=7928] [LOGGER] [INFO] [final] frames=99965 expected_frames=99965 frame0_arrival_s=265733.372232 frame99965_done_s=265742.417675 end_to_end_latency_s=9.045443 final_wall_avg_fps=11051.42

# GPU 97%

---
export DRAVA_THREADS=4
export DRAVA_INFER_BATCH=128
export DRAVA_JS_FETCH_BATCH=128
export DRAVA_FETCH_TIMEOUT_MS=500
export DRAVA_PUBLISH_RATE_HZ=0 # 0 for max
export DRAVA_PUBLISH_SYNTHETIC=1
export DRAVA_PUBLISH_DURATION_S=50

Published count=158720 seq=1019276 win_fps=6165.88 avg_fps=3233.62
Published count=158976 seq=1019532 win_fps=2259.59 avg_fps=3231.38
Published count=159232 seq=1019788 win_fps=2274.33 avg_fps=3229.20
Published count=159488 seq=1020044 win_fps=5980.19 avg_fps=3231.58
Published count=159744 seq=1020300 win_fps=2278.42 avg_fps=3229.42
Published count=160000 seq=1020556 win_fps=6024.02 avg_fps=3231.82
Published count=160256 seq=1020812 win_fps=2299.83 avg_fps=3229.73
Published count=160512 seq=1021068 win_fps=6094.58 avg_fps=3232.15
Published count=160768 seq=1021324 win_fps=2285.28 avg_fps=3230.02
Published count=161024 seq=1021580 win_fps=5306.20 avg_fps=3232.03
Published count=161280 seq=1021836 win_fps=2259.09 avg_fps=3229.82
Published count=161536 seq=1022092 win_fps=5817.05 avg_fps=3232.10
Done: published 161674 frames in 50.001s (avg_fps=3233.44) seq=1022230 eos_seq=1022231 Last frame sent at: 1560327.613818294



[59.409815] [TID=13637] [LOGGER] [INFO] [frames]=159754 batch=128 step_ms=91.94 wall_avg_fps=3025.90
[59.519392] [TID=13636] [LOGGER] [INFO] [frames]=159882 batch=128 step_ms=114.00 wall_avg_fps=3022.06
[59.525809] [TID=13637] [LOGGER] [INFO] [frames]=160010 batch=128 step_ms=114.02 wall_avg_fps=3024.11
[59.527916] [TID=13638] [LOGGER] [INFO] [frames]=160138 batch=128 step_ms=123.49 wall_avg_fps=3026.41
[59.840071] [TID=13636] [LOGGER] [INFO] [frames]=160266 batch=128 step_ms=318.89 wall_avg_fps=3011.06
[59.873999] [TID=13637] [LOGGER] [INFO] [frames]=160394 batch=128 step_ms=344.65 wall_avg_fps=3011.55
[59.875326] [TID=13638] [LOGGER] [INFO] [frames]=160522 batch=128 step_ms=345.05 wall_avg_fps=3013.88
[59.936265] [TID=13636] [LOGGER] [INFO] [frames]=160650 batch=128 step_ms=94.50 wall_avg_fps=3012.83
[59.979660] [TID=13637] [LOGGER] [INFO] [frames]=160778 batch=128 step_ms=102.63 wall_avg_fps=3012.78
[59.980987] [TID=13638] [LOGGER] [INFO] [frames]=160906 batch=128 step_ms=103.48 wall_avg_fps=3015.11
[60.033907] [TID=13636] [LOGGER] [INFO] [frames]=161034 batch=128 step_ms=95.91 wall_avg_fps=3014.52
[60.087722] [TID=13638] [LOGGER] [INFO] [frames]=161162 batch=128 step_ms=104.65 wall_avg_fps=3013.87
[60.089878] [TID=13637] [LOGGER] [INFO] [frames]=161290 batch=128 step_ms=107.30 wall_avg_fps=3016.15
[60.133242] [TID=13636] [LOGGER] [INFO] [frames]=161418 batch=128 step_ms=97.53 wall_avg_fps=3016.10
[60.207906] [TID=13637] [LOGGER] [INFO] [frames]=161546 batch=128 step_ms=115.23 wall_avg_fps=3014.28
[60.209251] [TID=13638] [LOGGER] [INFO] [frames]=161674 batch=128 step_ms=119.70 wall_avg_fps=3016.59
[60.209265] [TID=13638] [LOGGER] [INFO] [final] frames=161674 expected_frames=161674 frame0_arrival_s=1560277.657793 frame161674_done_s=1560331.253356 end_to_end_latency_s=53.595563 final_wall_avg_fps=3016.56



export DRAVA_INFER_BATCH=256
export DRAVA_JS_FETCH_BATCH=256
export DRAVA_FETCH_TIMEOUT_MS=500
export DRAVA_PUBLISH_RATE_HZ=0 # 0 for max
export DRAVA_PUBLISH_SYNTHETIC=1
export DRAVA_PUBLISH_DURATION_S=50


Published count=157952 seq=1180183 win_fps=2264.32 avg_fps=3200.14
Published count=158208 seq=1180439 win_fps=2285.36 avg_fps=3198.07
Published count=158464 seq=1180695 win_fps=5680.55 avg_fps=3200.33
Published count=158720 seq=1180951 win_fps=2269.26 avg_fps=3198.21
Published count=158976 seq=1181207 win_fps=6020.26 avg_fps=3200.63
Published count=159232 seq=1181463 win_fps=2232.01 avg_fps=3198.40
Published count=159488 seq=1181719 win_fps=5531.88 avg_fps=3200.57
Published count=159744 seq=1181975 win_fps=2240.74 avg_fps=3198.37
Published count=160000 seq=1182231 win_fps=6255.64 avg_fps=3200.87
Done: published 160091 frames in 50.001s (avg_fps=3201.78) seq=1182322 eos_seq=1182323 Last frame sent at: 1560452.864794835

[53.438789] [TID=53862] [LOGGER] [INFO] [frames]=156535 batch=256 step_ms=88.58 wall_avg_fps=3198.76
[53.555758] [TID=53861] [LOGGER] [INFO] [frames]=156791 batch=256 step_ms=93.00 wall_avg_fps=3196.35
[53.595292] [TID=53860] [LOGGER] [INFO] [frames]=157047 batch=256 step_ms=89.22 wall_avg_fps=3198.99
[53.709736] [TID=53862] [LOGGER] [INFO] [frames]=157303 batch=256 step_ms=91.47 wall_avg_fps=3196.75
[53.752929] [TID=53861] [LOGGER] [INFO] [frames]=157559 batch=256 step_ms=90.71 wall_avg_fps=3199.15
[53.863276] [TID=53860] [LOGGER] [INFO] [frames]=157815 batch=256 step_ms=89.04 wall_avg_fps=3197.18
[54.131668] [TID=53862] [LOGGER] [INFO] [frames]=158071 batch=256 step_ms=314.47 wall_avg_fps=3185.05
[54.179625] [TID=53860] [LOGGER] [INFO] [frames]=158327 batch=256 step_ms=204.57 wall_avg_fps=3187.13
[54.182929] [TID=53861] [LOGGER] [INFO] [frames]=158583 batch=256 step_ms=252.32 wall_avg_fps=3192.07
[54.231492] [TID=53862] [LOGGER] [INFO] [frames]=158839 batch=256 step_ms=98.04 wall_avg_fps=3194.10
[54.280792] [TID=53860] [LOGGER] [INFO] [frames]=159095 batch=256 step_ms=98.91 wall_avg_fps=3196.08
[54.342152] [TID=53861] [LOGGER] [INFO] [frames]=159351 batch=256 step_ms=95.30 wall_avg_fps=3197.28
[54.382273] [TID=53862] [LOGGER] [INFO] [frames]=159607 batch=256 step_ms=89.85 wall_avg_fps=3199.84
[54.488224] [TID=53860] [LOGGER] [INFO] [frames]=159863 batch=256 step_ms=83.76 wall_avg_fps=3198.18
[55.654401] [TID=53861] [LOGGER] [INFO] EOS received: expected_frames=160091
[55.654432] [TID=53861] [LOGGER] [INFO] [frames]=160091 batch=228 step_ms=722.52 wall_avg_fps=3129.73
[55.654438] [TID=53861] [LOGGER] [INFO] [final] frames=160091 expected_frames=160091 frame0_arrival_s=1560402.929271 frame160091_done_s=1560454.082069 end_to_end_latency_s=51.152798 final_wall_avg_fps=3129.66


export DRAVA_INFER_BATCH=512
export DRAVA_JS_FETCH_BATCH=512
export DRAVA_FETCH_TIMEOUT_MS=500
export DRAVA_PUBLISH_RATE_HZ=0 # 0 for max
export DRAVA_PUBLISH_SYNTHETIC=1
export DRAVA_PUBLISH_DURATION_S=50

Published count=160512 seq=1342835 win_fps=2267.24 avg_fps=3248.18
Published count=160768 seq=1343091 win_fps=6071.78 avg_fps=3250.59
Published count=161024 seq=1343347 win_fps=2258.43 avg_fps=3248.32
Published count=161280 seq=1343603 win_fps=5954.48 avg_fps=3250.66
Published count=161536 seq=1343859 win_fps=2310.48 avg_fps=3248.57
Published count=161792 seq=1344115 win_fps=5885.38 avg_fps=3250.87
Published count=162048 seq=1344371 win_fps=2251.76 avg_fps=3248.60
Published count=162304 seq=1344627 win_fps=6197.11 avg_fps=3251.03
Done: published 162343 frames in 50.001s (avg_fps=3246.82) seq=1344666 eos_seq=1344667 Last frame sent at: 1560589.836294279

[54.555664] [TID=9222] [LOGGER] [INFO] [frames]=157184 batch=512 step_ms=101.77 wall_avg_fps=3251.32
[54.712224] [TID=9221] [LOGGER] [INFO] [frames]=157696 batch=512 step_ms=104.58 wall_avg_fps=3251.38
[54.873136] [TID=9223] [LOGGER] [INFO] [frames]=158208 batch=512 step_ms=109.49 wall_avg_fps=3251.15
[55.027746] [TID=9222] [LOGGER] [INFO] [frames]=158720 batch=512 step_ms=104.08 wall_avg_fps=3251.34
[55.319958] [TID=9221] [LOGGER] [INFO] [frames]=159232 batch=512 step_ms=226.15 wall_avg_fps=3242.42
[55.352983] [TID=9223] [LOGGER] [INFO] [frames]=159744 batch=512 step_ms=109.43 wall_avg_fps=3250.66
[55.501224] [TID=9222] [LOGGER] [INFO] [frames]=160256 batch=512 step_ms=100.95 wall_avg_fps=3251.27
[55.658196] [TID=9221] [LOGGER] [INFO] [frames]=160768 batch=512 step_ms=102.61 wall_avg_fps=3251.31
[55.814070] [TID=9223] [LOGGER] [INFO] [frames]=161280 batch=512 step_ms=101.55 wall_avg_fps=3251.41
[55.969775] [TID=9222] [LOGGER] [INFO] [frames]=161792 batch=512 step_ms=103.22 wall_avg_fps=3251.53
[56.126834] [TID=9221] [LOGGER] [INFO] [frames]=162304 batch=512 step_ms=105.05 wall_avg_fps=3251.55
[57.745874] [TID=9223] [LOGGER] [INFO] EOS received: expected_frames=162343
[57.745905] [TID=9223] [LOGGER] [INFO] [final] frames=162343 expected_frames=162343 frame0_arrival_s=1560539.953207 frame162343_done_s=1560591.489710 end_to_end_latency_s=51.536503 final_wall_avg_fps=3150.06

# After running the publisher
export DRAVA_INFER_BATCH=128
export DRAVA_JS_FETCH_BATCH=128
export DRAVA_FETCH_TIMEOUT_MS=500
export DRAVA_PUBLISH_RATE_HZ=0
export DRAVA_PUBLISH_SYNTHETIC=1
export DRAVA_PUBLISH_DURATION_S=30

Published count=99328 seq=1742770 win_fps=6040.87 avg_fps=3374.69
Published count=99584 seq=1743026 win_fps=2307.83 avg_fps=3370.68
Published count=99840 seq=1743282 win_fps=6357.40 avg_fps=3374.75
Published count=100096 seq=1743538 win_fps=2357.57 avg_fps=3371.03
Published count=100352 seq=1743794 win_fps=6253.81 avg_fps=3374.99
Published count=100608 seq=1744050 win_fps=2338.20 avg_fps=3371.19
Published count=100864 seq=1744306 win_fps=6563.05 avg_fps=3375.36
Published count=101120 seq=1744562 win_fps=2324.05 avg_fps=3371.50
Done: published 101165 frames in 30.001s (avg_fps=3372.10) seq=1744607 eos_seq=1744608 Last frame sent at: 262788.732798513

[36.128773] [TID=23935] [LOGGER] [INFO] [frames]=99885 batch=128 step_ms=100.44 wall_avg_fps=2973.52
[36.129963] [TID=23934] [LOGGER] [INFO] [frames]=100013 batch=128 step_ms=98.03 wall_avg_fps=2977.22
[36.171975] [TID=23936] [LOGGER] [INFO] [frames]=100141 batch=128 step_ms=98.04 wall_avg_fps=2977.31
[36.239470] [TID=23935] [LOGGER] [INFO] [frames]=100269 batch=128 step_ms=108.07 wall_avg_fps=2975.14
[36.240590] [TID=23934] [LOGGER] [INFO] [frames]=100397 batch=128 step_ms=108.69 wall_avg_fps=2978.84
[36.279282] [TID=23936] [LOGGER] [INFO] [frames]=100525 batch=128 step_ms=105.70 wall_avg_fps=2979.22
[36.355268] [TID=23934] [LOGGER] [INFO] [frames]=100653 batch=128 step_ms=112.66 wall_avg_fps=2976.31
[36.355961] [TID=23935] [LOGGER] [INFO] [frames]=100781 batch=128 step_ms=113.94 wall_avg_fps=2980.03
[36.394643] [TID=23936] [LOGGER] [INFO] [frames]=100909 batch=128 step_ms=112.99 wall_avg_fps=2980.41
[36.458774] [TID=23935] [LOGGER] [INFO] [frames]=101037 batch=128 step_ms=100.28 wall_avg_fps=2978.55
[36.459838] [TID=23934] [LOGGER] [INFO] [frames]=101165 batch=128 step_ms=101.85 wall_avg_fps=2982.23
[36.459853] [TID=23934] [LOGGER] [INFO] [final] frames=101165 expected_frames=101165 frame0_arrival_s=262801.496850 frame101165_done_s=262835.420044 end_to_end_latency_s=33.923193 final_wall_avg_fps=2982.18
# GPU USAGE ~16%

export DRAVA_INFER_BATCH=256
export DRAVA_JS_FETCH_BATCH=256
export DRAVA_FETCH_TIMEOUT_MS=500
export DRAVA_PUBLISH_RATE_HZ=0 # 0 for max
export DRAVA_PUBLISH_SYNTHETIC=1
export DRAVA_PUBLISH_DURATION_S=30
Published count=97792 seq=1641153 win_fps=2332.44 avg_fps=3332.51
Published count=98048 seq=1641409 win_fps=6486.98 avg_fps=3336.75
Published count=98304 seq=1641665 win_fps=2274.85 avg_fps=3332.70
Published count=98560 seq=1641921 win_fps=5891.70 avg_fps=3336.46
Published count=98816 seq=1642177 win_fps=2271.35 avg_fps=3332.41
Published count=99072 seq=1642433 win_fps=5961.34 avg_fps=3336.21
Published count=99328 seq=1642689 win_fps=2276.51 avg_fps=3332.22
Published count=99584 seq=1642945 win_fps=5841.77 avg_fps=3335.90
Published count=99840 seq=1643201 win_fps=2310.57 avg_fps=3332.11
Done: published 100080 frames in 30.001s (avg_fps=3335.92) seq=1643441 eos_seq=1643442 Last frame sent at: 262629.47119317

[21.434781] [TID=34968] [LOGGER] [INFO] [frames]=97520 batch=256 step_ms=110.85 wall_avg_fps=5115.63
[21.474466] [TID=34966] [LOGGER] [INFO] [frames]=97776 batch=256 step_ms=106.15 wall_avg_fps=5118.40
[21.514195] [TID=34967] [LOGGER] [INFO] [frames]=98032 batch=256 step_ms=111.16 wall_avg_fps=5121.15
[21.546112] [TID=34968] [LOGGER] [INFO] [frames]=98288 batch=256 step_ms=109.43 wall_avg_fps=5125.98
[21.585781] [TID=34966] [LOGGER] [INFO] [frames]=98544 batch=256 step_ms=109.47 wall_avg_fps=5128.72
[21.627629] [TID=34967] [LOGGER] [INFO] [frames]=98800 batch=256 step_ms=111.09 wall_avg_fps=5130.87
[21.660814] [TID=34968] [LOGGER] [INFO] [frames]=99056 batch=256 step_ms=112.72 wall_avg_fps=5135.31
[21.699044] [TID=34966] [LOGGER] [INFO] [frames]=99312 batch=256 step_ms=111.60 wall_avg_fps=5138.40
[21.960763] [TID=34967] [LOGGER] [INFO] [frames]=99568 batch=256 step_ms=330.85 wall_avg_fps=5082.82
[21.968600] [TID=34968] [LOGGER] [INFO] [frames]=99824 batch=256 step_ms=306.02 wall_avg_fps=5093.85
[22.000047] [TID=34966] [LOGGER] [INFO] [frames]=100080 batch=256 step_ms=298.97 wall_avg_fps=5098.73
[22.000081] [TID=34966] [LOGGER] [INFO] [final] frames=100080 expected_frames=100080 frame0_arrival_s=262642.935727 frame100080_done_s=262662.565219 end_to_end_latency_s=19.629492 final_wall_avg_fps=5098.45

# GPU USAGE ~27%


export DRAVA_INFER_BATCH=512
export DRAVA_JS_FETCH_BATCH=512
export DRAVA_FETCH_TIMEOUT_MS=500
export DRAVA_PUBLISH_RATE_HZ=0
export DRAVA_PUBLISH_SYNTHETIC=1
export DRAVA_PUBLISH_DURATION_S=30


Published count=98048 seq=1442715 win_fps=2283.20 avg_fps=3331.30
Published count=98304 seq=1442971 win_fps=6310.25 avg_fps=3335.40
Published count=98560 seq=1443227 win_fps=2332.50 avg_fps=3331.68
Published count=98816 seq=1443483 win_fps=6407.37 avg_fps=3335.83
Published count=99072 seq=1443739 win_fps=2292.87 avg_fps=3331.92
Published count=99328 seq=1443995 win_fps=5964.51 avg_fps=3335.71
Published count=99584 seq=1444251 win_fps=2292.55 avg_fps=3331.81
Published count=99840 seq=1444507 win_fps=6149.82 avg_fps=3335.73
Done: published 99953 frames in 30.019s (avg_fps=3329.63) seq=1444620 eos_seq=1444621 Last frame sent at: 261856.448405589

[14.589192] [TID=53659] [LOGGER] [INFO] [frames]=94321 batch=512 step_ms=388.18 wall_avg_fps=7749.68
[14.755697] [TID=53658] [LOGGER] [INFO] [frames]=94833 batch=512 step_ms=163.24 wall_avg_fps=7686.58
[14.785513] [TID=53659] [LOGGER] [INFO] [frames]=95345 batch=512 step_ms=191.49 wall_avg_fps=7709.45
[14.785821] [TID=53661] [LOGGER] [INFO] [frames]=95857 batch=512 step_ms=195.11 wall_avg_fps=7750.65
[14.884762] [TID=53658] [LOGGER] [INFO] [frames]=96369 batch=512 step_ms=126.33 wall_avg_fps=7730.22
[14.950045] [TID=53661] [LOGGER] [INFO] [frames]=96881 batch=512 step_ms=159.66 wall_avg_fps=7730.80
[14.952424] [TID=53659] [LOGGER] [INFO] [frames]=97393 batch=512 step_ms=162.60 wall_avg_fps=7770.18
[15.021536] [TID=53658] [LOGGER] [INFO] [frames]=97905 batch=512 step_ms=133.83 wall_avg_fps=7768.20
[15.100066] [TID=53659] [LOGGER] [INFO] [frames]=98417 batch=512 step_ms=144.78 wall_avg_fps=7760.47
[15.103625] [TID=53661] [LOGGER] [INFO] [frames]=98929 batch=512 step_ms=148.94 wall_avg_fps=7798.65
[15.146079] [TID=53658] [LOGGER] [INFO] [frames]=99441 batch=512 step_ms=121.79 wall_avg_fps=7812.86
[15.208561] [TID=53659] [LOGGER] [INFO] [frames]=99953 batch=512 step_ms=105.66 wall_avg_fps=7814.73
[15.208590] [TID=53659] [LOGGER] [INFO] [final] frames=99953 expected_frames=99953 frame0_arrival_s=261969.675041 frame99953_done_s=261982.467512 end_to_end_latency_s=12.792471 final_wall_avg_fps=7813.42
# GPU USAGE ~70%


Published count=97024 seq=1841632 win_fps=2338.42 avg_fps=3310.87
Published count=97280 seq=1841888 win_fps=6003.23 avg_fps=3314.78
Published count=97536 seq=1842144 win_fps=2267.58 avg_fps=3310.77
Published count=97792 seq=1842400 win_fps=6276.98 avg_fps=3314.87
Published count=98048 seq=1842656 win_fps=2369.02 avg_fps=3311.41
Published count=98304 seq=1842912 win_fps=6581.71 avg_fps=3315.71
Published count=98560 seq=1843168 win_fps=2303.88 avg_fps=3311.93
Published count=98816 seq=1843424 win_fps=6448.90 avg_fps=3316.11
Published count=99072 seq=1843680 win_fps=2290.45 avg_fps=3312.27
Published count=99328 seq=1843936 win_fps=5906.18 avg_fps=3316.03
Done: published 99346 frames in 30.027s (avg_fps=3308.55) seq=1843954 eos_seq=1843955 Last frame sent at: 262924.232339312

[14.963083] [TID=1432] [LOGGER] [INFO] [frames]=94226 batch=512 step_ms=167.41 wall_avg_fps=7818.77
[14.976206] [TID=1430] [LOGGER] [INFO] [frames]=94738 batch=512 step_ms=185.35 wall_avg_fps=7852.70
[14.978788] [TID=1431] [LOGGER] [INFO] [frames]=95250 batch=512 step_ms=183.97 wall_avg_fps=7893.45
[15.309055] [TID=1432] [LOGGER] [INFO] [frames]=95762 batch=512 step_ms=343.34 wall_avg_fps=7724.46
[15.368821] [TID=1430] [LOGGER] [INFO] [frames]=96274 batch=512 step_ms=389.11 wall_avg_fps=7728.51
[15.371226] [TID=1431] [LOGGER] [INFO] [frames]=96786 batch=512 step_ms=388.70 wall_avg_fps=7768.11
[15.435418] [TID=1432] [LOGGER] [INFO] [frames]=97298 batch=512 step_ms=123.96 wall_avg_fps=7769.17
[15.530525] [TID=1430] [LOGGER] [INFO] [frames]=97810 batch=512 step_ms=157.94 wall_avg_fps=7751.19
[15.531231] [TID=1431] [LOGGER] [INFO] [frames]=98322 batch=512 step_ms=155.76 wall_avg_fps=7791.33
[15.569343] [TID=1432] [LOGGER] [INFO] [frames]=98834 batch=512 step_ms=131.15 wall_avg_fps=7808.32
[15.642574] [TID=1430] [LOGGER] [INFO] [frames]=99346 batch=512 step_ms=108.43 wall_avg_fps=7803.63
[15.642607] [TID=1430] [LOGGER] [INFO] [final] frames=99346 expected_frames=99346 frame0_arrival_s=262957.769565 frame99346_done_s=262970.502390 end_to_end_latency_s=12.732826 final_wall_avg_fps=7802.35

# GPU USAGE ~50%

export DRAVA_INFER_BATCH=1024
export DRAVA_JS_FETCH_BATCH=1024
export DRAVA_FETCH_TIMEOUT_MS=500
export DRAVA_PUBLISH_RATE_HZ=0 # 0 for max
export DRAVA_PUBLISH_SYNTHETIC=1
export DRAVA_PUBLISH_DURATION_S=30

Published count=96768 seq=1541389 win_fps=6422.03 avg_fps=3291.34
Published count=97024 seq=1541645 win_fps=2280.01 avg_fps=3287.49
Published count=97280 seq=1541901 win_fps=6134.28 avg_fps=3291.51
Published count=97536 seq=1542157 win_fps=2301.26 avg_fps=3287.80
Published count=97792 seq=1542413 win_fps=6166.67 avg_fps=3291.82
Published count=98048 seq=1542669 win_fps=2305.10 avg_fps=3288.15
Published count=98304 seq=1542925 win_fps=6090.72 avg_fps=3292.09
Published count=98560 seq=1543181 win_fps=2314.61 avg_fps=3288.48
Done: published 98739 frames in 30.001s (avg_fps=3291.23) seq=1543360 eos_seq=1543361 Last frame sent at: 262147.970633303

[48.313163] [TID=19657] [LOGGER] [INFO] [frames]=89088 batch=1024 step_ms=138.81 wall_avg_fps=2012.56
[48.816740] [TID=19656] [LOGGER] [INFO] [frames]=90112 batch=1024 step_ms=141.16 wall_avg_fps=2012.80
[49.314125] [TID=19655] [LOGGER] [INFO] [frames]=91136 batch=1024 step_ms=137.75 wall_avg_fps=2013.30
[49.814487] [TID=19657] [LOGGER] [INFO] [frames]=92160 batch=1024 step_ms=137.38 wall_avg_fps=2013.66
[50.412114] [TID=19656] [LOGGER] [INFO] [frames]=93184 batch=1024 step_ms=233.57 wall_avg_fps=2009.79
[50.816796] [TID=19655] [LOGGER] [INFO] [frames]=94208 batch=1024 step_ms=137.07 wall_avg_fps=2014.30
[51.320241] [TID=19657] [LOGGER] [INFO] [frames]=95232 batch=1024 step_ms=139.23 wall_avg_fps=2014.51
[51.825396] [TID=19656] [LOGGER] [INFO] [frames]=96256 batch=1024 step_ms=141.80 wall_avg_fps=2014.64
[52.353731] [TID=19655] [LOGGER] [INFO] [frames]=97280 batch=1024 step_ms=168.49 wall_avg_fps=2013.80
[52.373308] [TID=19657] [LOGGER] [INFO] [frames]=98304 batch=1024 step_ms=166.53 wall_avg_fps=2034.18
[54.068122] [TID=19656] [LOGGER] [INFO] EOS received: expected_frames=98739
[54.068153] [TID=19656] [LOGGER] [INFO] [final] frames=98739 expected_frames=98739 frame0_arrival_s=262438.835748 frame98739_done_s=262488.860034 end_to_end_latency_s=50.024287 final_wall_avg_fps=1973.82
# GPU USAGE ~18%

```

- Batch, js fetch, end to end, js publisher
```shell
export DRAVA_INFER_BATCH=128
export DRAVA_JS_FETCH_BATCH=8
export DRAVA_PUBLISH_RATE_HZ=1000
[87.224235] [TID=19256] [LOGGER] [INFO] [final] frames=3600 frame0_arrival_s=1213645.789674 frame3600_done_s=1213651.461921 end_to_end_latency_s=5.672248 final_wall_avg_fps=634.67

export DRAVA_INFER_BATCH=128
export DRAVA_JS_FETCH_BATCH=8
export DRAVA_PUBLISH_RATE_HZ=0 # max: ~3000Hz
[12.259951] [TID=25566] [LOGGER] [INFO] [final] frames=3600 frame0_arrival_s=1213745.673409 frame3600_done_s=1213748.863608 end_to_end_latency_s=3.190199 final_wall_avg_fps=1128.46

export DRAVA_INFER_BATCH=128
export DRAVA_JS_FETCH_BATCH=128
export DRAVA_PUBLISH_RATE_HZ=0 # max: ~3000Hz
[27.076115] [TID=30953] [LOGGER] [INFO] [final] frames=3600 frame0_arrival_s=1213832.375703 frame3600_done_s=1213835.565085 end_to_end_latency_s=3.189382 final_wall_avg_fps=1128.75

export DRAVA_INFER_BATCH=128
export DRAVA_JS_FETCH_BATCH=256
export DRAVA_PUBLISH_RATE_HZ=0 # max: ~3000Hz
[7.200151] [TID=47215] [LOGGER] [INFO] [final] frames=3600 frame0_arrival_s=1214497.331669 frame3600_done_s=1214500.502883 end_to_end_latency_s=3.171214 final_wall_avg_fps=1135.21


export DRAVA_INFER_BATCH=256
export DRAVA_JS_FETCH_BATCH=128
export DRAVA_PUBLISH_RATE_HZ=0 # max: ~3000Hz
[7.574742] [TID=43320] [LOGGER] [INFO] [final] frames=3600 frame0_arrival_s=1214386.315988 frame3600_done_s=1214389.531104 end_to_end_latency_s=3.215116 final_wall_avg_fps=1119.71

export DRAVA_INFER_BATCH=256
export DRAVA_JS_FETCH_BATCH=256
export DRAVA_PUBLISH_RATE_HZ=0 # max: ~3000Hz
[10.730398] [TID=36622] [LOGGER] [INFO] [final] frames=3600 frame0_arrival_s=1213916.095199 frame3600_done_s=1213919.276029 end_to_end_latency_s=3.180830 final_wall_avg_fps=1131.78


[2.528245] [TID=30950] [LOGGER] [INFO] JetStream fetch config: batch=128 timeout_ms=1000 callback_batch=128
[2.528253] [TID=30951] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=2
[2.533672] [TID=30950] [LOGGER] [INFO] JetStream ready: url=nats://127.0.0.1:4222 stream=FRAMES subject=frames.raw durable=drava_consumer
[23.970943] [TID=30952] [LOGGER] [INFO] [frames]=128 batch=128 step_ms=83.51 wall_avg_fps=1532.78
[24.001097] [TID=30953] [LOGGER] [INFO] [frames]=256 batch=128 step_ms=88.61 wall_avg_fps=2252.32
[24.072949] [TID=30951] [LOGGER] [INFO] [frames]=384 batch=128 step_ms=89.83 wall_avg_fps=2069.86
[24.099148] [TID=30952] [LOGGER] [INFO] [frames]=512 batch=128 step_ms=90.51 wall_avg_fps=2418.35
[24.116408] [TID=30953] [LOGGER] [INFO] [frames]=640 batch=128 step_ms=84.72 wall_avg_fps=2795.08
[24.466803] [TID=30951] [LOGGER] [INFO] [frames]=768 batch=128 step_ms=393.05 wall_avg_fps=1325.57
[24.503545] [TID=30953] [LOGGER] [INFO] [frames]=896 batch=128 step_ms=325.98 wall_avg_fps=1454.29
[24.504468] [TID=30952] [LOGGER] [INFO] [frames]=1024 batch=128 step_ms=351.86 wall_avg_fps=1659.56
[24.567469] [TID=30951] [LOGGER] [INFO] [frames]=1152 batch=128 step_ms=99.49 wall_avg_fps=1694.02
[24.610015] [TID=30953] [LOGGER] [INFO] [frames]=1280 batch=128 step_ms=104.16 wall_avg_fps=1771.43
[24.611486] [TID=30952] [LOGGER] [INFO] [frames]=1408 batch=128 step_ms=105.16 wall_avg_fps=1944.62
[24.661941] [TID=30951] [LOGGER] [INFO] [frames]=1536 batch=128 step_ms=92.83 wall_avg_fps=1983.19
[24.707829] [TID=30952] [LOGGER] [INFO] [frames]=1664 batch=128 step_ms=94.45 wall_avg_fps=2028.29
[24.714245] [TID=30953] [LOGGER] [INFO] [frames]=1792 batch=128 step_ms=102.01 wall_avg_fps=2167.37
[24.756051] [TID=30951] [LOGGER] [INFO] [frames]=1920 batch=128 step_ms=92.92 wall_avg_fps=2210.43
[24.799493] [TID=30952] [LOGGER] [INFO] [frames]=2048 batch=128 step_ms=89.87 wall_avg_fps=2245.46
[24.830355] [TID=30953] [LOGGER] [INFO] [frames]=2176 batch=128 step_ms=113.10 wall_avg_fps=2307.72
[24.859310] [TID=30951] [LOGGER] [INFO] [frames]=2304 batch=128 step_ms=101.89 wall_avg_fps=2370.66
[24.894692] [TID=30952] [LOGGER] [INFO] [frames]=2432 batch=128 step_ms=93.82 wall_avg_fps=2414.49
[24.932167] [TID=30953] [LOGGER] [INFO] [frames]=2560 batch=128 step_ms=99.90 wall_avg_fps=2450.40
[24.963855] [TID=30951] [LOGGER] [INFO] [frames]=2688 batch=128 step_ms=102.80 wall_avg_fps=2497.15
[24.984947] [TID=30952] [LOGGER] [INFO] [frames]=2816 batch=128 step_ms=88.70 wall_avg_fps=2565.80
[25.027470] [TID=30953] [LOGGER] [INFO] [frames]=2944 batch=128 step_ms=93.78 wall_avg_fps=2582.39
[25.057420] [TID=30951] [LOGGER] [INFO] [frames]=3072 batch=128 step_ms=91.91 wall_avg_fps=2625.68
[25.075818] [TID=30952] [LOGGER] [INFO] [frames]=3200 batch=128 step_ms=88.56 wall_avg_fps=2692.72
[25.118074] [TID=30953] [LOGGER] [INFO] [frames]=3328 batch=128 step_ms=89.29 wall_avg_fps=2704.28
[25.145569] [TID=30951] [LOGGER] [INFO] [frames]=3456 batch=128 step_ms=87.25 wall_avg_fps=2746.92
[25.158587] [TID=30952] [LOGGER] [INFO] [frames]=3584 batch=128 step_ms=80.30 wall_avg_fps=2819.48
[27.076115] [TID=30953] [LOGGER] [INFO] [final] frames=3600 frame0_arrival_s=1213832.375703 frame3600_done_s=1213835.565085 end_to_end_latency_s=3.189382 final_wall_avg_fps=1128.75
```
- Batch size
```shell
# 32
[5.801730] [TID=7054] [LOGGER] [INFO] [frames]=256 batch=32 step_ms=64.67 wall_avg_fps=884.91 first_arrival_s=1209077.358696 last_arrival_s=1209077.583435 first_done_s=1209077.423941 last_done_s=1209077.648176
[6.057312] [TID=7055] [LOGGER] [INFO] [frames]=512 batch=32 step_ms=64.39 wall_avg_fps=939.66 first_arrival_s=1209077.358696 last_arrival_s=1209077.839297 first_done_s=1209077.423941 last_done_s=1209077.903761
[6.568872] [TID=7056] [LOGGER] [INFO] [frames]=768 batch=32 step_ms=93.14 wall_avg_fps=726.97 first_arrival_s=1209077.358696 last_arrival_s=1209078.322097 first_done_s=1209077.423941 last_done_s=1209078.415317
[6.758190] [TID=7056] [LOGGER] [INFO] [frames]=1024 batch=32 step_ms=94.50 wall_avg_fps=821.99 first_arrival_s=1209077.358696 last_arrival_s=1209078.510081 first_done_s=1209077.423941 last_done_s=1209078.604638
[7.016057] [TID=7054] [LOGGER] [INFO] [frames]=1280 batch=32 step_ms=83.36 wall_avg_fps=851.28 first_arrival_s=1209077.358696 last_arrival_s=1209078.779076 first_done_s=1209077.423941 last_done_s=1209078.862505
[7.315461] [TID=7055] [LOGGER] [INFO] [frames]=1536 batch=32 step_ms=76.28 wall_avg_fps=851.90 first_arrival_s=1209077.358696 last_arrival_s=1209079.085565 first_done_s=1209077.423941 last_done_s=1209079.161910
[7.794709] [TID=7056] [LOGGER] [INFO] [frames]=1792 batch=32 step_ms=80.77 wall_avg_fps=785.18 first_arrival_s=1209077.358696 last_arrival_s=1209079.560316 first_done_s=1209077.423941 last_done_s=1209079.641157
[7.993695] [TID=7054] [LOGGER] [INFO] [frames]=2048 batch=32 step_ms=76.41 wall_avg_fps=825.38 first_arrival_s=1209077.358696 last_arrival_s=1209079.763663 first_done_s=1209077.423941 last_done_s=1209079.840152
[8.194212] [TID=7055] [LOGGER] [INFO] [frames]=2304 batch=32 step_ms=67.41 wall_avg_fps=859.13 first_arrival_s=1209077.358696 last_arrival_s=1209079.973160 first_done_s=1209077.423941 last_done_s=1209080.040648
[8.375230] [TID=7056] [LOGGER] [INFO] [frames]=2560 batch=32 step_ms=67.91 wall_avg_fps=894.23 first_arrival_s=1209077.358696 last_arrival_s=1209080.153706 first_done_s=1209077.423941 last_done_s=1209080.221679
[8.563962] [TID=7054] [LOGGER] [INFO] [frames]=2816 batch=32 step_ms=72.89 wall_avg_fps=922.82 first_arrival_s=1209077.358696 last_arrival_s=1209080.337448 first_done_s=1209077.423941 last_done_s=1209080.410403
[8.968253] [TID=7055] [LOGGER] [INFO] [frames]=3072 batch=32 step_ms=279.68 wall_avg_fps=888.93 first_arrival_s=1209077.358696 last_arrival_s=1209080.534954 first_done_s=1209077.423941 last_done_s=1209080.814702
[9.202387] [TID=7055] [LOGGER] [INFO] [frames]=3328 batch=32 step_ms=71.61 wall_avg_fps=901.91 first_arrival_s=1209077.358696 last_arrival_s=1209080.977150 first_done_s=1209077.423941 last_done_s=1209081.048833
[9.377686] [TID=7054] [LOGGER] [INFO] [frames]=3584 batch=32 step_ms=72.80 wall_avg_fps=927.23 first_arrival_s=1209077.358696 last_arrival_s=1209081.151263 first_done_s=1209077.423941 last_done_s=1209081.224138
[11.182134] [TID=7055] [LOGGER] [INFO] [final] frames=3600 frame0_arrival_s=1209077.358696 frame3600_done_s=1209083.028585 end_to_end_latency_s=5.669888 final_wall_avg_fps=634.93

# 64

[5.667528] [TID=63049] [LOGGER] [INFO] [frames]=256 batch=64 step_ms=69.11 wall_avg_fps=984.92 first_arrival_s=1209003.375814 last_arrival_s=1209003.566862 first_done_s=1209003.448817 last_done_s=1209003.636086
[6.030346] [TID=63049] [LOGGER] [INFO] [frames]=512 batch=64 step_ms=92.30 wall_avg_fps=822.18 first_arrival_s=1209003.375814 last_arrival_s=1209003.906377 first_done_s=1209003.448817 last_done_s=1209003.998903
[6.179634] [TID=63047] [LOGGER] [INFO] [frames]=768 batch=64 step_ms=68.67 wall_avg_fps=994.78 first_arrival_s=1209003.375814 last_arrival_s=1209004.079394 first_done_s=1209003.448817 last_done_s=1209004.148194
[6.433554] [TID=63048] [LOGGER] [INFO] [frames]=1024 batch=64 step_ms=66.32 wall_avg_fps=998.10 first_arrival_s=1209003.375814 last_arrival_s=1209004.335664 first_done_s=1209003.448817 last_done_s=1209004.402117
[6.691312] [TID=63049] [LOGGER] [INFO] [frames]=1280 batch=64 step_ms=68.52 wall_avg_fps=997.11 first_arrival_s=1209003.375814 last_arrival_s=1209004.591206 first_done_s=1209003.448817 last_done_s=1209004.659872
[7.176716] [TID=63048] [LOGGER] [INFO] [frames]=1536 batch=64 step_ms=166.06 wall_avg_fps=868.24 first_arrival_s=1209003.375814 last_arrival_s=1209004.979092 first_done_s=1209003.448817 last_done_s=1209005.145271
[7.267381] [TID=63047] [LOGGER] [INFO] [frames]=1792 batch=64 step_ms=89.07 wall_avg_fps=963.56 first_arrival_s=1209003.375814 last_arrival_s=1209005.146665 first_done_s=1209003.448817 last_done_s=1209005.235939
[7.459955] [TID=63049] [LOGGER] [INFO] [frames]=2048 batch=64 step_ms=69.08 wall_avg_fps=997.88 first_arrival_s=1209003.375814 last_arrival_s=1209005.359312 first_done_s=1209003.448817 last_done_s=1209005.428515
[7.715292] [TID=63048] [LOGGER] [INFO] [frames]=2304 batch=64 step_ms=68.41 wall_avg_fps=998.40 first_arrival_s=1209003.375814 last_arrival_s=1209005.615317 first_done_s=1209003.448817 last_done_s=1209005.683854
[7.973863] [TID=63047] [LOGGER] [INFO] [frames]=2560 batch=64 step_ms=70.77 wall_avg_fps=997.56 first_arrival_s=1209003.375814 last_arrival_s=1209005.871520 first_done_s=1209003.448817 last_done_s=1209005.942426
[8.432724] [TID=63048] [LOGGER] [INFO] [frames]=2816 batch=64 step_ms=209.45 wall_avg_fps=930.87 first_arrival_s=1209003.375814 last_arrival_s=1209006.191716 first_done_s=1209003.448817 last_done_s=1209006.401283
[8.522043] [TID=63048] [LOGGER] [INFO] [frames]=3072 batch=64 step_ms=88.36 wall_avg_fps=986.37 first_arrival_s=1209003.375814 last_arrival_s=1209006.401642 first_done_s=1209003.448817 last_done_s=1209006.490605
[8.787943] [TID=63047] [LOGGER] [INFO] [frames]=3328 batch=64 step_ms=73.82 wall_avg_fps=984.52 first_arrival_s=1209003.375814 last_arrival_s=1209006.682565 first_done_s=1209003.448817 last_done_s=1209006.756497
[8.997234] [TID=63049] [LOGGER] [INFO] [frames]=3584 batch=64 step_ms=70.87 wall_avg_fps=998.43 first_arrival_s=1209003.375814 last_arrival_s=1209006.894762 first_done_s=1209003.448817 last_done_s=1209006.965796
[10.974005] [TID=63048] [LOGGER] [INFO] [final] frames=3600 frame0_arrival_s=1209003.375814 frame3600_done_s=1209008.942563 end_to_end_latency_s=5.566749 final_wall_avg_fps=646.70




#128
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/data-model) ✗ python app.py
2026-02-19 16:59:43.487669: I tensorflow/core/platform/cpu_feature_guard.cc:210] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
To enable the following instructions: AVX2 FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
[0.000000] [TID=51698] [LOGGER] [INFO] Visible GPUs: 1, [PhysicalDevice(name='/physical_device:GPU:0', device_type='GPU')]
[0.000064] [TID=51698] [LOGGER] [INFO] Built with CUDA: True
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1771520388.248049   51698 gpu_device.cc:2020] Created device /job:localhost/replica:0/task:0/device:GPU:0 with 38482 MB memory:  -> device: 0, name: NVIDIA A100-PCIE-40GB, pci bus id: 0000:43:00.0, compute capability: 8.0
WARNING:absl:No training configuration found in the save file, so the model was *not* compiled. Compile it manually.
[1.051704] [TID=51698] [LOGGER] [INFO] Loaded model: PtychoNN_data_partial/wts4/weights.66.hdf5
2026-02-19 16:59:49.500113: I external/local_xla/xla/service/service.cc:163] XLA service 0x7f129c00b560 initialized for platform CUDA (this does not guarantee that XLA will be used). Devices:
2026-02-19 16:59:49.500141: I external/local_xla/xla/service/service.cc:171]   StreamExecutor device (0): NVIDIA A100-PCIE-40GB, Compute Capability 8.0
2026-02-19 16:59:49.532554: I tensorflow/compiler/mlir/tensorflow/utils/dump_mlir_util.cc:269] disabling MLIR crash reproducer, set env var `MLIR_CRASH_REPRODUCER_DIRECTORY` to enable.
2026-02-19 16:59:49.615752: I external/local_xla/xla/stream_executor/cuda/cuda_dnn.cc:473] Loaded cuDNN version 91900
I0000 00:00:1771520390.604689   51972 device_compiler.h:196] Compiled cluster using XLA!  This line is logged at most once for the lifetime of the process.
[2.652582] [TID=51698] [LOGGER] [INFO] Warmup done: runs=2, batch=128
[2.652616] [TID=51698] [LOGGER] [INFO] drava_init: selected transport=nats
[2.652633] [TID=51698] [LOGGER] [INFO] Initializing XKRT
[2.663635] [TID=51698] [LOGGER] [WARN] Unknown environment variable 'XKAAPI_HOME=/home/rpereira/shared/install/xkaapi/502226c375a8/Debug-cuda'
[2.663649] [TID=51698] [LOGGER] [IMPL] 'XKAAPI_CACHE_LIMIT' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[2.663655] [TID=51698] [LOGGER] [IMPL] 'XKAAPI_DEFAULT_MATH' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[2.663663] [TID=51698] [LOGGER] [IMPL] 'XKAAPI_PRECISION' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[2.663678] [TID=51698] [LOGGER] [INFO] Created new task format `0` named `(null)`
[2.663682] [TID=51698] [LOGGER] [INFO] Created new task format `1` named `host_capture`
[2.663691] [TID=51698] [LOGGER] [INFO] Created new task format `2` named `memory_register_async`
[2.663695] [TID=51698] [LOGGER] [INFO] Created new task format `3` named `memory_unregister_async`
[2.663703] [TID=51698] [LOGGER] [INFO] Created new task format `4` named `memory_touch_async`
[2.663712] [TID=51698] [LOGGER] [INFO] Created new task format `5` named `file_read_async`
[2.663715] [TID=51698] [LOGGER] [INFO] Created new task format `6` named `file_write_async`
[2.663725] [TID=51698] [LOGGER] [INFO] Built with support for `host, cuda`
[2.663730] [TID=51698] [LOGGER] [INFO] Loading driver `HOST`
[2.674653] [TID=52358] [LOGGER] [INFO]   global id =  0 | Unknown CPU
[2.674663] [TID=52358] [LOGGER] [INFO] Found memory `RAM` of capacity 269GB
[2.674672] [TID=52358] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 63 of node 0
[2.674686] [TID=52360] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 37 of node 0
[2.674914] [TID=52359] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 59 of node 0
[2.674935] [TID=52361] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 47 of node 0
[2.674986] [TID=51698] [LOGGER] [INFO] Loading driver `CUDA`
[2.674999] [TID=51698] [LOGGER] [INFO] Calling cuInit(0) ...
[2.675009] [TID=51698] [LOGGER] [INFO] Returned from cuInit(0)
[2.675184] [TID=52362] [LOGGER] [INFO]   global id =  1 | NVIDIA A100-PCIE-40GB, cu device: 1, pci: 43:00, 42.41 (GB)
[2.675237] [TID=52362] [LOGGER] [INFO] Found memory `(null)` of capacity 42GB
[2.675245] [TID=52362] [LOGGER] [INFO] Starting thread for CUDA device (device_driver_id=0, device_global_id=1) on cpu 55 of node 0
[2.689571] [TID=51698] [LOGGER] [INFO] Found 2 devices (with 2 requested)
[2.689589] [TID=51698] [LOGGER] [INFO] drava_register_frame_routine: routine=0x7f1708420d50 user_data=(nil)
[2.689596] [TID=51698] [LOGGER] [INFO] team->desc.nthreads: 4
[2.689807] [TID=52363] [LOGGER] [INFO] Starting thread 0 on device 1
[2.689831] [TID=52363] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=0
[2.689835] [TID=52363] [LOGGER] [INFO] JetStream trying to connect
[2.689843] [TID=52363] [LOGGER] [INFO] JetStream fetch config: batch=8 timeout_ms=1000 callback_batch=128
[2.689863] [TID=52364] [LOGGER] [INFO] Starting thread 2 on device 1
[2.689886] [TID=52366] [LOGGER] [INFO] Starting thread 3 on device 1
[2.689902] [TID=52364] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=2
[2.689909] [TID=52366] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=3
[2.690338] [TID=52365] [LOGGER] [INFO] Starting thread 1 on device 1
[2.690367] [TID=52365] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=1
[2.697893] [TID=52363] [LOGGER] [INFO] JetStream ready: url=nats://127.0.0.1:4222 stream=FRAMES subject=frames.raw durable=drava_consumer
[54.966599] [TID=52366] [LOGGER] [INFO] [frames]=256 batch=128 step_ms=74.46 wall_avg_fps=1597.95 first_arrival_s=1208710.193633 last_arrival_s=1208710.279443 first_done_s=1208710.268551 last_done_s=1208710.354519
[55.221782] [TID=52364] [LOGGER] [INFO] [frames]=512 batch=128 step_ms=73.79 wall_avg_fps=1232.57 first_arrival_s=1208710.193633 last_arrival_s=1208710.535714 first_done_s=1208710.268551 last_done_s=1208710.609705
[55.480520] [TID=52365] [LOGGER] [INFO] [frames]=768 batch=128 step_ms=76.79 wall_avg_fps=1139.25 first_arrival_s=1208710.193633 last_arrival_s=1208710.791366 first_done_s=1208710.268551 last_done_s=1208710.868442
[55.732801] [TID=52366] [LOGGER] [INFO] [frames]=1024 batch=128 step_ms=73.03 wall_avg_fps=1105.34 first_arrival_s=1208710.193633 last_arrival_s=1208711.047272 first_done_s=1208710.268551 last_done_s=1208711.120725
[56.119911] [TID=52364] [LOGGER] [INFO] [frames]=1280 batch=128 step_ms=204.53 wall_avg_fps=974.48 first_arrival_s=1208710.193633 last_arrival_s=1208711.303097 first_done_s=1208710.268551 last_done_s=1208711.507841
[56.246013] [TID=52365] [LOGGER] [INFO] [frames]=1536 batch=128 step_ms=74.39 wall_avg_fps=1066.95 first_arrival_s=1208710.193633 last_arrival_s=1208711.559351 first_done_s=1208710.268551 last_done_s=1208711.633937
[56.505446] [TID=52366] [LOGGER] [INFO] [frames]=1792 batch=128 step_ms=76.65 wall_avg_fps=1054.71 first_arrival_s=1208710.193633 last_arrival_s=1208711.816273 first_done_s=1208710.268551 last_done_s=1208711.893367
[56.758649] [TID=52364] [LOGGER] [INFO] [frames]=2048 batch=128 step_ms=74.35 wall_avg_fps=1049.04 first_arrival_s=1208710.193633 last_arrival_s=1208712.071948 first_done_s=1208710.268551 last_done_s=1208712.146573
[57.020677] [TID=52365] [LOGGER] [INFO] [frames]=2304 batch=128 step_ms=80.92 wall_avg_fps=1040.52 first_arrival_s=1208710.193633 last_arrival_s=1208712.327473 first_done_s=1208710.268551 last_done_s=1208712.408600
[57.363388] [TID=52366] [LOGGER] [INFO] [frames]=2560 batch=128 step_ms=166.27 wall_avg_fps=1001.17 first_arrival_s=1208710.193633 last_arrival_s=1208712.584494 first_done_s=1208710.268551 last_done_s=1208712.751313
[57.529800] [TID=52364] [LOGGER] [INFO] [frames]=2816 batch=128 step_ms=78.04 wall_avg_fps=1034.00 first_arrival_s=1208710.193633 last_arrival_s=1208712.839476 first_done_s=1208710.268551 last_done_s=1208712.917723
[57.783054] [TID=52365] [LOGGER] [INFO] [frames]=3072 batch=128 step_ms=75.45 wall_avg_fps=1032.03 first_arrival_s=1208710.193633 last_arrival_s=1208713.095325 first_done_s=1208710.268551 last_done_s=1208713.170978
[58.040118] [TID=52366] [LOGGER] [INFO] [frames]=3328 batch=128 step_ms=75.90 wall_avg_fps=1029.15 first_arrival_s=1208710.193633 last_arrival_s=1208713.351930 first_done_s=1208710.268551 last_done_s=1208713.428041
[58.296921] [TID=52364] [LOGGER] [INFO] [frames]=3584 batch=128 step_ms=77.17 wall_avg_fps=1026.78 first_arrival_s=1208710.193633 last_arrival_s=1208713.607472 first_done_s=1208710.268551 last_done_s=1208713.684845
[60.296415] [TID=52366] [LOGGER] [INFO] [final] frames=3600 frame0_arrival_s=1208710.193633 frame3600_done_s=1208715.684338 end_to_end_latency_s=5.490705 final_wall_avg_fps=655.65

# 256
[6.422959] [TID=58681] [LOGGER] [INFO] [frames]=256 batch=256 step_ms=88.99 wall_avg_fps=2876.78 first_arrival_s=1208827.386419 last_arrival_s=1208827.386419 first_done_s=1208827.476341 last_done_s=1208827.476341
[6.677576] [TID=58683] [LOGGER] [INFO] [frames]=512 batch=256 step_ms=87.72 wall_avg_fps=1490.07 first_arrival_s=1208827.386419 last_arrival_s=1208827.642243 first_done_s=1208827.476341 last_done_s=1208827.730961
[7.022737] [TID=58682] [LOGGER] [INFO] [frames]=768 batch=256 step_ms=176.85 wall_avg_fps=1115.03 first_arrival_s=1208827.386419 last_arrival_s=1208827.898443 first_done_s=1208827.476341 last_done_s=1208828.076123
[7.182613] [TID=58681] [LOGGER] [INFO] [frames]=1024 batch=256 step_ms=81.95 wall_avg_fps=1206.63 first_arrival_s=1208827.386419 last_arrival_s=1208828.153647 first_done_s=1208827.476341 last_done_s=1208828.235999
[7.439458] [TID=58683] [LOGGER] [INFO] [frames]=1280 batch=256 step_ms=82.98 wall_avg_fps=1157.86 first_arrival_s=1208827.386419 last_arrival_s=1208828.409429 first_done_s=1208827.476341 last_done_s=1208828.492845
[7.695766] [TID=58682] [LOGGER] [INFO] [frames]=1536 batch=256 step_ms=83.11 wall_avg_fps=1127.92 first_arrival_s=1208827.386419 last_arrival_s=1208828.665447 first_done_s=1208827.476341 last_done_s=1208828.749152
[7.951622] [TID=58681] [LOGGER] [INFO] [frames]=1792 batch=256 step_ms=83.25 wall_avg_fps=1107.78 first_arrival_s=1208827.386419 last_arrival_s=1208828.921300 first_done_s=1208827.476341 last_done_s=1208829.005007
[8.264929] [TID=58683] [LOGGER] [INFO] [frames]=2048 batch=256 step_ms=139.62 wall_avg_fps=1060.61 first_arrival_s=1208827.386419 last_arrival_s=1208829.178230 first_done_s=1208827.476341 last_done_s=1208829.318317
[8.463396] [TID=58682] [LOGGER] [INFO] [frames]=2304 batch=256 step_ms=82.72 wall_avg_fps=1081.98 first_arrival_s=1208827.386419 last_arrival_s=1208829.433680 first_done_s=1208827.476341 last_done_s=1208829.516782
[8.718779] [TID=58681] [LOGGER] [INFO] [frames]=2560 batch=256 step_ms=82.41 wall_avg_fps=1073.46 first_arrival_s=1208827.386419 last_arrival_s=1208829.689303 first_done_s=1208827.476341 last_done_s=1208829.772165
[8.978065] [TID=58683] [LOGGER] [INFO] [frames]=2816 batch=256 step_ms=85.62 wall_avg_fps=1065.01 first_arrival_s=1208827.386419 last_arrival_s=1208829.945387 first_done_s=1208827.476341 last_done_s=1208830.031452
[9.235971] [TID=58682] [LOGGER] [INFO] [frames]=3072 batch=256 step_ms=87.39 wall_avg_fps=1058.58 first_arrival_s=1208827.386419 last_arrival_s=1208830.201556 first_done_s=1208827.476341 last_done_s=1208830.289356
[9.590385] [TID=58681] [LOGGER] [INFO] [frames]=3328 batch=256 step_ms=185.80 wall_avg_fps=1021.98 first_arrival_s=1208827.386419 last_arrival_s=1208830.457576 first_done_s=1208827.476341 last_done_s=1208830.643771
[9.744777] [TID=58683] [LOGGER] [INFO] [frames]=3584 batch=256 step_ms=84.48 wall_avg_fps=1050.78 first_arrival_s=1208827.386419 last_arrival_s=1208830.713303 first_done_s=1208827.476341 last_done_s=1208830.798164
[11.800396] [TID=58682] [LOGGER] [INFO] [final] frames=3600 frame0_arrival_s=1208827.386419 frame3600_done_s=1208832.853783 end_to_end_latency_s=5.467365 final_wall_avg_fps=658.45


---
# JS BATCH 128

[13.983721] [TID=50258] [LOGGER] [INFO] [frames]=256 batch=128 step_ms=91.36 wall_avg_fps=2228.08 first_arrival_s=1211048.895937 last_arrival_s=1211048.919490 first_done_s=1211048.988042 last_done_s=1211049.011463
[14.095445] [TID=50259] [LOGGER] [INFO] [frames]=512 batch=128 step_ms=89.57 wall_avg_fps=2259.29 first_arrival_s=1211048.895937 last_arrival_s=1211049.033402 first_done_s=1211048.988042 last_done_s=1211049.123186
[14.152396] [TID=50260] [LOGGER] [INFO] [frames]=768 batch=128 step_ms=94.42 wall_avg_fps=2708.27 first_arrival_s=1211048.895937 last_arrival_s=1211049.085487 first_done_s=1211048.988042 last_done_s=1211049.180141
[14.273821] [TID=50258] [LOGGER] [INFO] [frames]=1024 batch=128 step_ms=89.17 wall_avg_fps=2528.40 first_arrival_s=1211048.895937 last_arrival_s=1211049.212153 first_done_s=1211048.988042 last_done_s=1211049.301565
[14.331639] [TID=50259] [LOGGER] [INFO] [frames]=1280 batch=128 step_ms=97.76 wall_avg_fps=2765.68 first_arrival_s=1211048.895937 last_arrival_s=1211049.261399 first_done_s=1211048.988042 last_done_s=1211049.359382
[14.453706] [TID=50260] [LOGGER] [INFO] [frames]=1536 batch=128 step_ms=89.39 wall_avg_fps=2626.17 first_arrival_s=1211048.895937 last_arrival_s=1211049.391848 first_done_s=1211048.988042 last_done_s=1211049.481449
[14.506040] [TID=50258] [LOGGER] [INFO] [frames]=1792 batch=128 step_ms=91.16 wall_avg_fps=2812.22 first_arrival_s=1211048.895937 last_arrival_s=1211049.442398 first_done_s=1211048.988042 last_done_s=1211049.533785
[14.625082] [TID=50259] [LOGGER] [INFO] [frames]=2048 batch=128 step_ms=87.36 wall_avg_fps=2708.05 first_arrival_s=1211048.895937 last_arrival_s=1211049.565241 first_done_s=1211048.988042 last_done_s=1211049.652830
[14.675205] [TID=50260] [LOGGER] [INFO] [frames]=2304 batch=128 step_ms=89.27 wall_avg_fps=2857.20 first_arrival_s=1211048.895937 last_arrival_s=1211049.613471 first_done_s=1211048.988042 last_done_s=1211049.702949
[14.803644] [TID=50258] [LOGGER] [INFO] [frames]=2560 batch=128 step_ms=93.63 wall_avg_fps=2738.48 first_arrival_s=1211048.895937 last_arrival_s=1211049.737553 first_done_s=1211048.988042 last_done_s=1211049.831392
[14.853102] [TID=50259] [LOGGER] [INFO] [frames]=2816 batch=128 step_ms=91.77 wall_avg_fps=2860.96 first_arrival_s=1211048.895937 last_arrival_s=1211049.788845 first_done_s=1211048.988042 last_done_s=1211049.880850
[14.975929] [TID=50260] [LOGGER] [INFO] [frames]=3072 batch=128 step_ms=86.94 wall_avg_fps=2774.80 first_arrival_s=1211048.895937 last_arrival_s=1211049.916518 first_done_s=1211048.988042 last_done_s=1211050.003672
[15.024329] [TID=50258] [LOGGER] [INFO] [frames]=3328 batch=128 step_ms=86.24 wall_avg_fps=2880.12 first_arrival_s=1211048.895937 last_arrival_s=1211049.965604 first_done_s=1211048.988042 last_done_s=1211050.052073
[15.139610] [TID=50259] [LOGGER] [INFO] [frames]=3584 batch=128 step_ms=81.53 wall_avg_fps=2820.30 first_arrival_s=1211048.895937 last_arrival_s=1211050.085610 first_done_s=1211048.988042 last_done_s=1211050.167353
[17.159910] [TID=50258] [LOGGER] [INFO] [final] frames=3600 frame0_arrival_s=1211048.895937 frame3600_done_s=1211052.187651 end_to_end_latency_s=3.291714 final_wall_avg_fps=1093.66

```