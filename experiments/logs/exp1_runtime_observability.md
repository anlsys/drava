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

cat /home/ashovon/drava/experiments/results/exp1_20260513_205018/exp1_summary.csv                 
workload,stage,batch,run,frames,end_to_end_s,callback_compute_s,publish_s,microbatching_wait_s,dispatch_overhead_s,transport_lumped_s,runtime_overhead_pct,stage_total_fps,cb_avg_ms
ptychonn,stage1,32,1,10000,9.965191589028109,28.235087,0.097444,1.0000000004450893e-06,0.0,0.4780055890281094,5.7746063774799214,1054.05,90.519
ptychonn,stage2,32,1,625,9.965191589028109,0.527378,0.0,0.0,8.607719999999999,0.8300935890281096,94.70779868817921,68.42,26.369
ptychonn,stage1,64,1,10000,6.419802650052588,17.551251,0.087836,0.0,0.0,0.48676965005258843,8.950518908052127,1685.48,112.351
ptychonn,stage2,64,1,625,6.419802650052588,1.057862,0.0,0.0,4.487557,0.8743836500525886,83.52189221904922,112.71,105.786
ptychonn,stage1,128,1,10000,4.087824793998152,10.49994,0.086856,0.0,0.0,0.5179517939981522,14.795345311426907,2801.22,134.01
ptychonn,stage2,128,1,625,4.087824793998152,1.797069,0.0,0.0,1.3149509999999998,0.9758047939981522,56.038502368337745,200.83,359.414
ptychonn,stage1,256,1,10000,7.089642476988956,6.931823,0.082476,6.661338147750939e-16,0.0,4.717473476988957,67.70368876242043,4215.55,175.357
ptychonn,stage2,256,1,625,7.089642476988956,5.563054,0.0,0.0,0.11697099999999949,1.4096174769889567,21.532658126892088,110.03,1854.351
ptychonn,stage1,512,1,10000,13.988321128999814,5.230311,0.083439,0.0,0.0,12.172077128999815,87.61248770299072,5505.87,265.687
ptychonn,stage2,512,1,625,13.988321128999814,11.876835,0.0,0.0,0.02811299999999939,2.083373128999815,15.094635800306287,52.5,5938.417
```