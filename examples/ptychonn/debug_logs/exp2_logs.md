```shell
(no-gil-3.13) (base) ➜  ~/drava git:(main) ✗ python experiments/exp2_callback_inference_batch.py --callback-batches 64,128,256,256,512 --infer-batches 64,128,256 --num-frames 10000 --runs 1
[exp2-cb-infer] writing to /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913
[exp2-cb-infer] pair callback_batch=64 infer_batch=64
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 64 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 64 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb64_ib64
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=64 run=1 ...
[batch=64 run=1] starting app_stage2.py
[batch=64 run=1] starting app.py
[batch=64 run=1] starting publisher_jetstream.py
  done: publisher_fps=20728.36 stage1_fps=1834.68 stage2_fps=1820.56

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 4/4 | 10000 | 0.48 | 20728.36 | 5.45 | 1834.68 | 5.49 | 1820.56 | 5.94 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb64_ib64/20260603_161913
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=128 infer_batch=64
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 64 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 128 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb128_ib64
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=64 run=1 ...
[batch=64 run=1] starting app_stage2.py
[batch=64 run=1] starting app.py
[batch=64 run=1] starting publisher_jetstream.py
  done: publisher_fps=20020.00 stage1_fps=1687.12 stage2_fps=1677.01

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 4/4 | 10000 | 0.50 | 20020.00 | 5.93 | 1687.12 | 5.96 | 1677.01 | 6.42 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb128_ib64/20260603_161935
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=128 infer_batch=128
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 128 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 128 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb128_ib128
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=128 run=1 ...
[batch=128 run=1] starting app_stage2.py
[batch=128 run=1] starting app.py
[batch=128 run=1] starting publisher_jetstream.py
  done: publisher_fps=19541.72 stage1_fps=2854.83 stage2_fps=2820.06

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4/4 | 10000 | 0.51 | 19541.72 | 3.50 | 2854.83 | 3.55 | 2820.06 | 3.98 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb128_ib128/20260603_161954
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=256 infer_batch=64
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 64 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 256 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb256_ib64
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=64 run=1 ...
[batch=64 run=1] starting app_stage2.py
[batch=64 run=1] starting app.py
[batch=64 run=1] starting publisher_jetstream.py
  done: publisher_fps=20040.35 stage1_fps=1692.68 stage2_fps=1686.20

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 4/4 | 10000 | 0.50 | 20040.35 | 5.91 | 1692.68 | 5.93 | 1686.20 | 6.44 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb256_ib64/20260603_162011
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=256 infer_batch=128
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 128 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 256 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb256_ib128
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=128 run=1 ...
[batch=128 run=1] starting app_stage2.py
[batch=128 run=1] starting app.py
[batch=128 run=1] starting publisher_jetstream.py
  done: publisher_fps=20326.08 stage1_fps=2880.67 stage2_fps=2850.18

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4/4 | 10000 | 0.49 | 20326.08 | 3.47 | 2880.67 | 3.51 | 2850.18 | 3.97 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb256_ib128/20260603_162031
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=256 infer_batch=256
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 256 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 256 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb256_ib256
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=19901.90 stage1_fps=4098.06 stage2_fps=1782.71

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4/4 | 10000 | 0.50 | 19901.90 | 2.44 | 4098.06 | 5.61 | 1782.71 | 6.05 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb256_ib256/20260603_162048
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=256 infer_batch=64
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 64 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 256 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb256_ib64
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=64 run=1 ...
[batch=64 run=1] starting app_stage2.py
[batch=64 run=1] starting app.py
[batch=64 run=1] starting publisher_jetstream.py
  done: publisher_fps=19972.86 stage1_fps=1800.07 stage2_fps=1787.99

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 4/4 | 10000 | 0.50 | 19972.86 | 5.56 | 1800.07 | 5.59 | 1787.99 | 6.05 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb256_ib64/20260603_162107
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=256 infer_batch=128
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 128 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 256 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb256_ib128
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=128 run=1 ...
[batch=128 run=1] starting app_stage2.py
[batch=128 run=1] starting app.py
[batch=128 run=1] starting publisher_jetstream.py
  done: publisher_fps=19808.72 stage1_fps=2860.65 stage2_fps=2827.95

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4/4 | 10000 | 0.51 | 19808.72 | 3.50 | 2860.65 | 3.54 | 2827.95 | 3.99 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb256_ib128/20260603_162127
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=256 infer_batch=256
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 256 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 256 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb256_ib256
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=20138.14 stage1_fps=4146.31 stage2_fps=2242.29

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4/4 | 10000 | 0.50 | 20138.14 | 2.41 | 4146.31 | 4.46 | 2242.29 | 4.93 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb256_ib256/20260603_162143
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=512 infer_batch=64
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 64 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 512 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb512_ib64
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=64 run=1 ...
[batch=64 run=1] starting app_stage2.py
[batch=64 run=1] starting app.py
[batch=64 run=1] starting publisher_jetstream.py
  done: publisher_fps=19610.56 stage1_fps=1883.77 stage2_fps=1865.96

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 4/4 | 10000 | 0.51 | 19610.56 | 5.31 | 1883.77 | 5.36 | 1865.96 | 5.81 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb512_ib64/20260603_162202
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=512 infer_batch=128
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 128 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 512 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb512_ib128
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=128 run=1 ...
[batch=128 run=1] starting app_stage2.py
[batch=128 run=1] starting app.py
[batch=128 run=1] starting publisher_jetstream.py
  done: publisher_fps=19590.40 stage1_fps=2873.41 stage2_fps=2837.51

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4/4 | 10000 | 0.51 | 19590.40 | 3.48 | 2873.41 | 3.52 | 2837.51 | 4.02 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb512_ib128/20260603_162221
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=512 infer_batch=256
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 256 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 512 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb512_ib256
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=19515.81 stage1_fps=4161.90 stage2_fps=4126.36

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4/4 | 10000 | 0.51 | 19515.81 | 2.40 | 4161.90 | 2.42 | 4126.36 | 2.92 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/cb512_ib256/20260603_162238
[global] stopping nats-server
[exp2-cb-infer] wrote 12 rows -> /home/ashovon/drava/experiments/results/exp2_cb_infer_20260603_161913/exp2_cb_infer_summary.csv
```