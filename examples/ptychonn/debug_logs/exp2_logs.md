```shell
(no-gil-3.13) (base) ➜  ~/drava git:(main) ✗ python experiments/exp2_callback_inference_batch.py --callback-batches 64,128,256,256,512 --infer-batches 64,128,256 --num-frames 10000 --runs 1
[exp2-cb-infer] writing to /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740
[exp2-cb-infer] pair callback_batch=64 infer_batch=64
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 64 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 64 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0.0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb64_ib64
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=64 run=1 ...
[batch=64 run=1] starting app_stage2.py
[batch=64 run=1] starting app.py
[batch=64 run=1] starting publisher_jetstream.py
  done: publisher_fps=17867.10 stage1_fps=2024.83 stage2_fps=2009.97

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 4/4 | 10000 | 0.56 | 17867.10 | 4.94 | 2024.83 | 4.98 | 2009.97 | 5.39 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb64_ib64/20260602_195740
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=128 infer_batch=64
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 64 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 128 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0.0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb128_ib64
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=64 run=1 ...
[batch=64 run=1] starting app_stage2.py
[batch=64 run=1] starting app.py
[batch=64 run=1] starting publisher_jetstream.py
  done: publisher_fps=18563.43 stage1_fps=2109.11 stage2_fps=2089.18

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 4/4 | 10000 | 0.54 | 18563.43 | 4.74 | 2109.11 | 4.79 | 2089.18 | 5.27 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb128_ib64/20260602_195759
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=128 infer_batch=128
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 128 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 128 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0.0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb128_ib128
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=128 run=1 ...
[batch=128 run=1] starting app_stage2.py
[batch=128 run=1] starting app.py
[batch=128 run=1] starting publisher_jetstream.py
  done: publisher_fps=18818.85 stage1_fps=3166.64 stage2_fps=3141.68

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4/4 | 10000 | 0.53 | 18818.85 | 3.16 | 3166.64 | 3.18 | 3141.68 | 3.62 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb128_ib128/20260602_195817
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=256 infer_batch=64
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 64 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 256 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0.0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb256_ib64
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=64 run=1 ...
[batch=64 run=1] starting app_stage2.py
[batch=64 run=1] starting app.py
[batch=64 run=1] starting publisher_jetstream.py
  done: publisher_fps=17820.62 stage1_fps=2092.68 stage2_fps=2075.00

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 4/4 | 10000 | 0.56 | 17820.62 | 4.78 | 2092.68 | 4.82 | 2075.00 | 5.25 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb256_ib64/20260602_195834
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=256 infer_batch=128
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 128 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 256 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0.0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb256_ib128
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=128 run=1 ...
[batch=128 run=1] starting app_stage2.py
[batch=128 run=1] starting app.py
[batch=128 run=1] starting publisher_jetstream.py
  done: publisher_fps=18054.69 stage1_fps=3219.23 stage2_fps=3188.64

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4/4 | 10000 | 0.55 | 18054.69 | 3.11 | 3219.23 | 3.14 | 3188.64 | 3.58 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb256_ib128/20260602_195852
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=256 infer_batch=256
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 256 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 256 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0.0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb256_ib256
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py
[batch=256 run=1] starting publisher_jetstream.py
  done: publisher_fps=18157.11 stage1_fps=4770.07 stage2_fps=1704.37

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 4/4 | 10000 | 0.55 | 18157.11 | 2.10 | 4770.07 | 5.87 | 1704.37 | 6.32 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb256_ib256/20260602_195908
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=256 infer_batch=64
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 64 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 256 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0.0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb256_ib64
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=64 run=1 ...
[batch=64 run=1] starting app_stage2.py
[batch=64 run=1] starting app.py
[batch=64 run=1] starting publisher_jetstream.py
  done: publisher_fps=17630.65 stage1_fps=2072.50 stage2_fps=2056.20

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 4/4 | 10000 | 0.57 | 17630.65 | 4.83 | 2072.50 | 4.86 | 2056.20 | 5.30 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb256_ib64/20260602_195927
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=256 infer_batch=128
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 128 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 256 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0.0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb256_ib128
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=128 run=1 ...
[batch=128 run=1] starting app_stage2.py
[batch=128 run=1] starting app.py
[batch=128 run=1] starting publisher_jetstream.py
  done: publisher_fps=18151.71 stage1_fps=3292.81 stage2_fps=3248.02

| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4/4 | 10000 | 0.55 | 18151.71 | 3.04 | 3292.81 | 3.08 | 3248.02 | 3.50 |

Logs and summary written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb256_ib128/20260602_195945
[global] stopping nats-server
[exp2-cb-infer] pair callback_batch=256 infer_batch=256
[exp] $ cd /home/ashovon/drava/examples/ptychonn && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark_two_stages.py --batches 256 --stage1-threads 4 --stage2-threads 4 --stage1-callback-batch 256 --stage2-callback-batch 8 --timeout-ms 200 --rate-hz 0.0 --num-frames 10000 --runs 1 --out-dir /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb256_ib256
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=256 run=1 ...
[batch=256 run=1] starting app_stage2.py
[batch=256 run=1] starting app.py

Logs written to: /home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb256_ib256/20260602_200001
[global] stopping nats-server
Traceback (most recent call last):
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 712, in <module>
    main()
    ~~~~^^
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 675, in main
    row = run_one(args, base_env, run_dir, b, run_idx)
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 542, in run_one
    fail_with_logs(run_dir, f"stage1 exited early\n--- stage1 tail ---\n{tail_text(stage1_log)}")
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 290, in fail_with_logs
    raise RuntimeError(f"{message}\n--- logs ---\n{run_dir}")
RuntimeError: stage1 exited early
--- stage1 tail ---
[2.459119][TID=11725] [LOGGER] [IMPL] 'XKAAPI_CACHE_LIMIT' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[2.459123][TID=11725] [LOGGER] [IMPL] 'XKAAPI_DEFAULT_MATH' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[2.459129][TID=11725] [LOGGER] [IMPL] 'XKAAPI_PRECISION' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[2.459147][TID=11725] [LOGGER] [INFO] Created new task format `0` named `(null)`
[2.459149][TID=11725] [LOGGER] [INFO] Created new task format `1` named `host_capture`
[2.459152][TID=11725] [LOGGER] [INFO] Created new task format `2` named `memory_register_async`
[2.459154][TID=11725] [LOGGER] [INFO] Created new task format `3` named `memory_unregister_async`
[2.459155][TID=11725] [LOGGER] [INFO] Created new task format `4` named `memory_touch_async`
[2.459157][TID=11725] [LOGGER] [INFO] Created new task format `5` named `file_read_async`
[2.459159][TID=11725] [LOGGER] [INFO] Created new task format `6` named `file_write_async`
[2.459162][TID=11725] [LOGGER] [INFO] Built with support for `host, cuda`
[2.459165][TID=11725] [LOGGER] [INFO] Loading driver `HOST`
[2.466225][TID=12129] [LOGGER] [INFO]   global id =  0 | Unknown CPU
[2.466232][TID=12129] [LOGGER] [INFO] Found memory `RAM` of capacity 269GB
[2.466239][TID=12129] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 31 of node 0
[2.466243][TID=12130] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 21 of node 0
[2.466258][TID=12131] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 24 of node 0
[2.466281][TID=12132] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 27 of node 0
[2.466318][TID=11725] [LOGGER] [INFO] Loading driver `CUDA`
[2.466320][TID=11725] [LOGGER] [INFO] Calling cuInit(0) ...
[2.466327][TID=11725] [LOGGER] [INFO] Returned from cuInit(0)
[2.466583][TID=12133] [LOGGER] [INFO]   global id =  1 | NVIDIA A40, cu device: 1, pci: 42:00, 47.70 (GB)
[2.466629][TID=12133] [LOGGER] [INFO] Found memory `(null)` of capacity 47GB
[2.466635][TID=12133] [LOGGER] [INFO] Starting thread for CUDA device (device_driver_id=0, device_global_id=1) on cpu 17 of node 0
[2.488639][TID=11725] [LOGGER] [INFO] Found 2 devices (with 2 requested)
[2.488647][TID=11725] [LOGGER] [INFO] drava_init: selected transport=nats
[2.488660][TID=11725] [LOGGER] [INFO] [stage1] callback_batch=256 infer_batch=256
[2.488664][TID=11725] [LOGGER] [INFO] drava_register_frame_routine: routine=0x7efe96e31240 user_data=(nil)
[2.488668][TID=11725] [LOGGER] [INFO] team->desc.nthreads: 4
[2.488861][TID=12134] [LOGGER] [INFO] Starting thread 0 on device 1
[2.488881][TID=12134] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=0
[2.488886][TID=12134] [LOGGER] [INFO] JetStream trying to connect
[2.488889][TID=12134] [LOGGER] [INFO] JetStream fetch config: batch=256 timeout_ms=200 callback_batch=256 callback_flush_timeout_ms=0
[2.488893][TID=12136] [LOGGER] [INFO] Starting thread 1 on device 1
[2.488910][TID=12136] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=1
free(): invalid size
[2.488922][TID=12135] [LOGGER] [INFO] Starting thread 2 on device 1
[2.488941][TID=12135] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=2
[2.488948][TID=12137] [LOGGER] [INFO] Starting thread 3 on device 1
[2.488963][TID=12137] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=3
--- logs ---
/home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb256_ib256/20260602_200001
Traceback (most recent call last):
  File "/home/ashovon/drava/experiments/exp2_callback_inference_batch.py", line 239, in <module>
    main()
    ~~~~^^
  File "/home/ashovon/drava/experiments/exp2_callback_inference_batch.py", line 216, in main
    rows.extend(collect_pair(args, run_dir, callback_batch, infer_batch))
                ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ashovon/drava/experiments/exp2_callback_inference_batch.py", line 115, in collect_pair
    ts = run_ptychonn_benchmark(
        run_dir / tag,
    ...<12 lines>...
        },
    )
  File "/home/ashovon/drava/experiments/_common.py", line 232, in run_ptychonn_benchmark
    subprocess.run(cmd, cwd=PTYCHO_DIR, env=env, check=True)
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ashovon/miniconda3/lib/python3.13/subprocess.py", line 577, in run
    raise CalledProcessError(retcode, process.args,
                             output=stdout, stderr=stderr)
subprocess.CalledProcessError: Command '['/home/ashovon/venvs/no-gil-3.13/bin/python', 'benchmark_two_stages.py', '--batches', '256', '--stage1-threads', '4', '--stage2-threads', '4', '--stage1-callback-batch', '256', '--stage2-callback-batch', '8', '--timeout-ms', '200', '--rate-hz', '0.0', '--num-frames', '10000', '--runs', '1', '--out-dir', '/home/ashovon/drava/experiments/results/exp2_cb_infer_20260602_195740/cb256_ib256']' returned non-zero exit status 1.
(no-gil-3.13) (base) ➜  ~/drava git:(main) ✗ 
```