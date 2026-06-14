(no-gil-3.13) (base) ➜  ~/drava git:(main) ✗ python experiments/sc4_tomogan_gpu_energy.py \
--batches 2,4,8,16 \
--thread-list 2,4,8 \
--num-frames 512 \
--runs 3 \
--rate-hz 0
[sc4-tomogan-energy] $ cd /home/ashovon/drava/examples/tomogan && /home/ashovon/venvs/no-gil-3.13/bin/python benchmark.py --batches 2,4,8,16 --thread-list 2,4,8 --timeout-ms 200 --rate-hz 0 --num-frames 512 --runs 3 --gpu-sample-interval-s 0.2 --out-dir /home/ashovon/drava/experiments/results/sc4_tomogan_gpu_energy_20260604_175623/benchmark --nats-command nats-server --nats-config /home/ashovon/drava/experiments/results/sc4_tomogan_gpu_energy_20260604_175623/nats.generated.conf --stage-config /home/ashovon/drava/examples/tomogan/pipeline.yaml --rapl-glob /sys/class/powercap/intel-rapl:*/energy_uj
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running threads=2 batch=2 run=1 ...
[batch=2 run=1] starting app.py
[batch=2 run=1] starting publisher_jetstream.py
done: stage_fps=17.04 overhead_pct=1.80 gpu_j_per_frame=3.4281
Running threads=2 batch=2 run=2 ...
[batch=2 run=2] starting app.py
[batch=2 run=2] starting publisher_jetstream.py
done: stage_fps=17.14 overhead_pct=1.82 gpu_j_per_frame=3.3279
Running threads=2 batch=2 run=3 ...
[batch=2 run=3] starting app.py
[batch=2 run=3] starting publisher_jetstream.py
done: stage_fps=16.99 overhead_pct=1.89 gpu_j_per_frame=3.3621
Running threads=2 batch=4 run=1 ...
[batch=4 run=1] starting app.py
[batch=4 run=1] starting publisher_jetstream.py
done: stage_fps=30.14 overhead_pct=4.43 gpu_j_per_frame=4.0963
Running threads=2 batch=4 run=2 ...
[batch=4 run=2] starting app.py
[batch=4 run=2] starting publisher_jetstream.py
done: stage_fps=30.40 overhead_pct=3.26 gpu_j_per_frame=4.3540
Running threads=2 batch=4 run=3 ...
[batch=4 run=3] starting app.py
[batch=4 run=3] starting publisher_jetstream.py
done: stage_fps=30.32 overhead_pct=3.25 gpu_j_per_frame=4.2339
Running threads=2 batch=8 run=1 ...
[batch=8 run=1] starting app.py
[batch=8 run=1] starting publisher_jetstream.py
done: stage_fps=32.58 overhead_pct=3.71 gpu_j_per_frame=4.3695
Running threads=2 batch=8 run=2 ...
[batch=8 run=2] starting app.py
[batch=8 run=2] starting publisher_jetstream.py
done: stage_fps=32.60 overhead_pct=3.64 gpu_j_per_frame=4.1204
Running threads=2 batch=8 run=3 ...
[batch=8 run=3] starting app.py
[batch=8 run=3] starting publisher_jetstream.py
done: stage_fps=32.44 overhead_pct=3.54 gpu_j_per_frame=4.2789
Running threads=2 batch=16 run=1 ...
[batch=16 run=1] starting app.py
[batch=16 run=1] starting publisher_jetstream.py
done: stage_fps=38.11 overhead_pct=4.95 gpu_j_per_frame=3.3547
Running threads=2 batch=16 run=2 ...
[batch=16 run=2] starting app.py
[batch=16 run=2] starting publisher_jetstream.py
done: stage_fps=37.93 overhead_pct=4.43 gpu_j_per_frame=3.3578
Running threads=2 batch=16 run=3 ...
[batch=16 run=3] starting app.py
[batch=16 run=3] starting publisher_jetstream.py
done: stage_fps=37.99 overhead_pct=5.05 gpu_j_per_frame=3.7620
Running threads=4 batch=2 run=1 ...
[batch=2 run=1] starting app.py
[batch=2 run=1] starting publisher_jetstream.py
done: stage_fps=50.86 overhead_pct=5.38 gpu_j_per_frame=3.3549
Running threads=4 batch=2 run=2 ...
[batch=2 run=2] starting app.py
[batch=2 run=2] starting publisher_jetstream.py
done: stage_fps=47.50 overhead_pct=4.82 gpu_j_per_frame=3.3519
Running threads=4 batch=2 run=3 ...
[batch=2 run=3] starting app.py
[batch=2 run=3] starting publisher_jetstream.py
done: stage_fps=49.83 overhead_pct=5.02 gpu_j_per_frame=3.4825
Running threads=4 batch=4 run=1 ...
[batch=4 run=1] starting app.py
[batch=4 run=1] starting publisher_jetstream.py
done: stage_fps=56.73 overhead_pct=5.91 gpu_j_per_frame=3.0590
Running threads=4 batch=4 run=2 ...
[batch=4 run=2] starting app.py
[batch=4 run=2] starting publisher_jetstream.py
done: stage_fps=57.04 overhead_pct=5.90 gpu_j_per_frame=3.2357
Running threads=4 batch=4 run=3 ...
[batch=4 run=3] starting app.py
[batch=4 run=3] starting publisher_jetstream.py
done: stage_fps=57.97 overhead_pct=6.01 gpu_j_per_frame=3.0113
Running threads=4 batch=8 run=1 ...
[batch=8 run=1] starting app.py

Logs written to: /home/ashovon/drava/experiments/results/sc4_tomogan_gpu_energy_20260604_175623/benchmark/20260604_175623
[global] stopping nats-server
Traceback (most recent call last):
File "/home/ashovon/drava/examples/tomogan/benchmark.py", line 613, in <module>
main()
~~~~^^
File "/home/ashovon/drava/examples/tomogan/benchmark.py", line 590, in main
row = run_one(args, os.environ, run_dir, base_config, batch_size, threads, run_idx)
File "/home/ashovon/drava/examples/tomogan/benchmark.py", line 406, in run_one
raise RuntimeError(f"app exited early\n--- app tail ---\n{tail_text(app_log)}")
RuntimeError: app exited early
--- app tail ---
2026-06-04 18:06:23.907469: I tensorflow/core/platform/cpu_feature_guard.cc:210] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
To enable the following instructions: AVX2 FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
[0.000000][TID=22842] [LOGGER] [INFO] Visible GPUs: 1, [PhysicalDevice(name='/physical_device:GPU:0', device_type='GPU')]
[0.000053][TID=22842] [LOGGER] [INFO] Built with CUDA: True
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1780596389.613998   22842 gpu_device.cc:2020] Created device /job:localhost/replica:0/task:0/device:GPU:0 with 38503 MB memory:  -> device: 0, name: NVIDIA A100-PCIE-40GB, pci bus id: 0000:43:00.0, compute capability: 8.0
[1.190832][TID=22842] [LOGGER] [INFO] Loaded model: /home/ashovon/drava/examples/tomogan/dataset/testjob-it00500.h5
2026-06-04 18:06:30.847493: I external/local_xla/xla/service/service.cc:163] XLA service 0x7fa2b420bdf0 initialized for platform CUDA (this does not guarantee that XLA will be used). Devices:
2026-06-04 18:06:30.847518: I external/local_xla/xla/service/service.cc:171]   StreamExecutor device (0): NVIDIA A100-PCIE-40GB, Compute Capability 8.0
2026-06-04 18:06:30.861023: I tensorflow/compiler/mlir/tensorflow/utils/dump_mlir_util.cc:269] disabling MLIR crash reproducer, set env var `MLIR_CRASH_REPRODUCER_DIRECTORY` to enable.
2026-06-04 18:06:30.935978: I external/local_xla/xla/stream_executor/cuda/cuda_dnn.cc:473] Loaded cuDNN version 91900
2026-06-04 18:06:39.155853: E external/local_xla/xla/service/slow_operation_alarm.cc:73] Trying algorithm eng0{} for conv (f32[8,32,1024,1024]{3,2,1,0}, u8[0]{0}) custom-call(f32[8,64,1024,1024]{3,2,1,0}, f32[32,64,3,3]{3,2,1,0}, f32[32]{0}), window={size=3x3 pad=1_1x1_1}, dim_labels=bf01_oi01->bf01, custom_call_target="__cudnn$convBiasActivationForward", backend_config={"operation_queue_id":"0","wait_on_operation_queues":[],"cudnn_conv_backend_config":{"activation_mode":"kRelu","conv_result_scale":1,"side_input_scale":0,"leakyrelu_alpha":0},"force_earliest_schedule":false,"reification_cost":[]} is taking a while...
2026-06-04 18:06:39.233389: E external/local_xla/xla/service/slow_operation_alarm.cc:140] The operation took 1.077653943s
Trying algorithm eng0{} for conv (f32[8,32,1024,1024]{3,2,1,0}, u8[0]{0}) custom-call(f32[8,64,1024,1024]{3,2,1,0}, f32[32,64,3,3]{3,2,1,0}, f32[32]{0}), window={size=3x3 pad=1_1x1_1}, dim_labels=bf01_oi01->bf01, custom_call_target="__cudnn$convBiasActivationForward", backend_config={"operation_queue_id":"0","wait_on_operation_queues":[],"cudnn_conv_backend_config":{"activation_mode":"kRelu","conv_result_scale":1,"side_input_scale":0,"leakyrelu_alpha":0},"force_earliest_schedule":false,"reification_cost":[]} is taking a while...
I0000 00:00:1780596400.353819   23442 device_compiler.h:196] Compiled cluster using XLA!  This line is logged at most once for the lifetime of the process.
[11.309563][TID=22842] [LOGGER] [INFO] Warmup done: runs=2, batch=8, frame=(1024, 1024)
[11.311857][TID=22842] [LOGGER] [INFO] Loaded stage config: file=/home/ashovon/drava/experiments/results/sc4_tomogan_gpu_energy_20260604_175623/benchmark/20260604_175623/pipeline_b8_r1.yaml stage=stage1 transport=nats
[11.311877][TID=22842] [LOGGER] [INFO] Initializing XKRT
[11.323042][TID=22842] [LOGGER] [WARN] Unknown environment variable 'XKAAPI_HOME=/home/rpereira/shared/install/xkaapi/502226c375a8/Debug-cuda'
[11.323056][TID=22842] [LOGGER] [IMPL] 'XKAAPI_CACHE_LIMIT' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[11.323060][TID=22842] [LOGGER] [IMPL] 'XKAAPI_DEFAULT_MATH' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[11.323067][TID=22842] [LOGGER] [IMPL] 'XKAAPI_PRECISION' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[11.323081][TID=22842] [LOGGER] [INFO] Created new task format `0` named `(null)`
[11.323085][TID=22842] [LOGGER] [INFO] Created new task format `1` named `host_capture`
[11.323092][TID=22842] [LOGGER] [INFO] Created new task format `2` named `memory_register_async`
[11.323094][TID=22842] [LOGGER] [INFO] Created new task format `3` named `memory_unregister_async`
[11.323096][TID=22842] [LOGGER] [INFO] Created new task format `4` named `memory_touch_async`
[11.323103][TID=22842] [LOGGER] [INFO] Created new task format `5` named `file_read_async`
[11.323105][TID=22842] [LOGGER] [INFO] Created new task format `6` named `file_write_async`
[11.323108][TID=22842] [LOGGER] [INFO] Built with support for `host, cuda`
[11.323111][TID=22842] [LOGGER] [INFO] Loading driver `HOST`
[11.334153][TID=23819] [LOGGER] [INFO]   global id =  0 | Unknown CPU
[11.334161][TID=23819] [LOGGER] [INFO] Found memory `RAM` of capacity 269GB
[11.334169][TID=23819] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 63 of node 0
[11.334183][TID=23821] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 33 of node 0
[11.334203][TID=23822] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 57 of node 0
[11.334220][TID=23820] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 46 of node 0
[11.334251][TID=22842] [LOGGER] [INFO] Loading driver `CUDA`
[11.334258][TID=22842] [LOGGER] [INFO] Calling cuInit(0) ...
[11.334266][TID=22842] [LOGGER] [INFO] Returned from cuInit(0)
[11.334515][TID=23823] [LOGGER] [INFO]   global id =  1 | NVIDIA A100-PCIE-40GB, cu device: 1, pci: 43:00, 42.43 (GB)
[11.334563][TID=23823] [LOGGER] [INFO] Found memory `(null)` of capacity 42GB
[11.334569][TID=23823] [LOGGER] [INFO] Starting thread for CUDA device (device_driver_id=0, device_global_id=1) on cpu 10 of node 0
[11.350097][TID=22842] [LOGGER] [INFO] Found 2 devices (with 2 requested)
[11.350118][TID=22842] [LOGGER] [INFO] drava_init: selected transport=nats
[11.350135][TID=22842] [LOGGER] [INFO] drava_register_frame_routine: routine=0x7fa717cc4240 user_data=(nil)
[11.350143][TID=22842] [LOGGER] [INFO] team->desc.nthreads: 4
[11.350440][TID=23824] [LOGGER] [INFO] Starting thread 0 on device 1
[11.350468][TID=23824] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=0
[11.350475][TID=23824] [LOGGER] [INFO] JetStream trying to connect
[11.350479][TID=23824] [LOGGER] [INFO] JetStream fetch config: batch=8 timeout_ms=200 callback_batch=8 callback_flush_timeout_ms=0
[11.350485][TID=23826] [LOGGER] [INFO] Starting thread 1 on device 1
[11.350511][TID=23826] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=1
[11.350518][TID=23825] [LOGGER] [INFO] Starting thread 2 on device 1
[11.350546][TID=23825] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=2
[11.350554][TID=23827] [LOGGER] [INFO] Starting thread 3 on device 1
[11.350581][TID=23827] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=3
Traceback (most recent call last):
File "/home/ashovon/drava/experiments/sc4_tomogan_gpu_energy.py", line 283, in <module>
main()
~~~~^^
File "/home/ashovon/drava/experiments/sc4_tomogan_gpu_energy.py", line 250, in main
bench_dir = run_benchmark(args, out_dir)
File "/home/ashovon/drava/experiments/sc4_tomogan_gpu_energy.py", line 175, in run_benchmark
subprocess.run(cmd, cwd=TOMOGAN_DIR, env=os.environ.copy(), check=True)
~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/ashovon/miniconda3/lib/python3.13/subprocess.py", line 577, in run
raise CalledProcessError(retcode, process.args,
output=stdout, stderr=stderr)
subprocess.CalledProcessError: Command '['/home/ashovon/venvs/no-gil-3.13/bin/python', 'benchmark.py', '--batches', '2,4,8,16', '--thread-list', '2,4,8', '--timeout-ms', '200', '--rate-hz', '0', '--num-frames', '512', '--runs', '3', '--gpu-sample-interval-s', '0.2', '--out-dir', '/home/ashovon/drava/experiments/results/sc4_tomogan_gpu_energy_20260604_175623/benchmark', '--nats-command', 'nats-server', '--nats-config', '/home/ashovon/drava/experiments/results/sc4_tomogan_gpu_energy_20260604_175623/nats.generated.conf', '--stage-config', '/home/ashovon/drava/examples/tomogan/pipeline.yaml', '--rapl-glob', '/sys/class/powercap/intel-rapl:*/energy_uj']' returned non-zero exit status 1.
