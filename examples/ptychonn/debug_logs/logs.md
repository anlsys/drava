### A 100
- 4 threads, 128 batch size:
```shell
(no-gil-3.13) (base) ➜  ~/drava/build git:(feature/data-model) ✗ export PYTHONPATH="$(pwd):$PYTHONPATH" # so that the build dir is in the Python path
(no-gil-3.13) (base) ➜  ~/drava/build git:(feature/data-model) ✗ export DRAVA_TRANSPORT=nats
(no-gil-3.13) (base) ➜  ~/drava/build git:(feature/data-model) ✗ export XKAAPI_VERBOSE=4
(no-gil-3.13) (base) ➜  ~/drava/build git:(feature/data-model) ✗ cd ../examples/ptychonn
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/data-model) ✗ python app.py
2026-02-14 15:54:42.831098: I tensorflow/core/platform/cpu_feature_guard.cc:210] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
To enable the following instructions: AVX2 FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
[0.000000] [TID=58794] [LOGGER] [INFO] Visible GPUs: 1, [PhysicalDevice(name='/physical_device:GPU:0', device_type='GPU')]
[0.000056] [TID=58794] [LOGGER] [INFO] Built with CUDA: True
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1771084495.061905   58794 gpu_device.cc:2020] Created device /job:localhost/replica:0/task:0/device:GPU:0 with 38482 MB memory:  -> device: 0, name: NVIDIA A100-PCIE-40GB, pci bus id: 0000:43:00.0, compute capability: 8.0
WARNING:absl:No training configuration found in the save file, so the model was *not* compiled. Compile it manually.
[1.291515] [TID=58794] [LOGGER] [INFO] Loaded model: PtychoNN_data_partial/wts4/weights.66.hdf5
[1.291540] [TID=58794] [LOGGER] [INFO] drava_init: selected transport=nats
[1.291554] [TID=58794] [LOGGER] [INFO] Initializing XKRT
[1.303554] [TID=58794] [LOGGER] [WARN] Unknown environment variable 'XKAAPI_HOME=/home/rpereira/shared/install/xkaapi/502226c375a8/Debug-cuda'
[1.303568] [TID=58794] [LOGGER] [IMPL] 'XKAAPI_CACHE_LIMIT' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[1.303572] [TID=58794] [LOGGER] [IMPL] 'XKAAPI_DEFAULT_MATH' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[1.303579] [TID=58794] [LOGGER] [IMPL] 'XKAAPI_PRECISION' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[1.303592] [TID=58794] [LOGGER] [INFO] Created new task format `0` named `(null)`
[1.303597] [TID=58794] [LOGGER] [INFO] Created new task format `1` named `host_capture`
[1.303605] [TID=58794] [LOGGER] [INFO] Created new task format `2` named `memory_register_async`
[1.303609] [TID=58794] [LOGGER] [INFO] Created new task format `3` named `memory_unregister_async`
[1.303613] [TID=58794] [LOGGER] [INFO] Created new task format `4` named `memory_touch_async`
[1.303621] [TID=58794] [LOGGER] [INFO] Created new task format `5` named `file_read_async`
[1.303625] [TID=58794] [LOGGER] [INFO] Created new task format `6` named `file_write_async`
[1.303630] [TID=58794] [LOGGER] [INFO] Built with support for `host, cuda`
[1.303635] [TID=58794] [LOGGER] [INFO] Loading driver `HOST`
[1.315632] [TID=59412] [LOGGER] [INFO]   global id =  0 | Unknown CPU
[1.315641] [TID=59412] [LOGGER] [INFO] Found memory `RAM` of capacity 269GB
[1.315651] [TID=59412] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 63 of node 0
[1.315667] [TID=59414] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 41 of node 0
[1.315695] [TID=59415] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 16 of node 0
[1.315728] [TID=59413] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 39 of node 0
[1.315896] [TID=58794] [LOGGER] [INFO] Loading driver `CUDA`
[1.315907] [TID=58794] [LOGGER] [INFO] Calling cuInit(0) ...
[1.315914] [TID=58794] [LOGGER] [INFO] Returned from cuInit(0)
[1.316118] [TID=59416] [LOGGER] [INFO]   global id =  1 | NVIDIA A100-PCIE-40GB, cu device: 1, pci: 43:00, 42.41 (GB)
[1.316176] [TID=59416] [LOGGER] [INFO] Found memory `(null)` of capacity 42GB
[1.316184] [TID=59416] [LOGGER] [INFO] Starting thread for CUDA device (device_driver_id=0, device_global_id=1) on cpu 43 of node 0
[1.344957] [TID=58794] [LOGGER] [INFO] Found 2 devices (with 2 requested)
[drava_py] register_routine_py: enter cb=0x7fe8f1ed1300
[drava_py] register_routine_py: calling drava_register_frame_routine
[1.344988] [TID=58794] [LOGGER] [INFO] drava_register_frame_routine: routine=0x7feace230e10 user_data=(nil)
[drava_py] register_routine_py: done
[drava_py] listen_py: before PyEval_SaveThread
[drava_py] listen_py: before drava_listen
[1.345006] [TID=58794] [LOGGER] [INFO] api.cc/drava_listen: entering
[1.345013] [TID=58794] [LOGGER] [INFO] drava.listen: enter, ndevices=2
[1.345023] [TID=58794] [LOGGER] [INFO] team->desc.nthreads: 4
[1.345726] [TID=59417] [LOGGER] [INFO] Starting thread 0 on device 1
[1.345757] [TID=59417] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=0
[1.345766] [TID=59417] [LOGGER] [INFO] JetStream trying to connect
[1.345772] [TID=59419] [LOGGER] [INFO] Starting thread 1 on device 1
[1.345804] [TID=59419] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=1
[1.345827] [TID=59418] [LOGGER] [INFO] Starting thread 2 on device 1
[1.345860] [TID=59418] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=2
[1.345919] [TID=59420] [LOGGER] [INFO] Starting thread 3 on device 1
[1.345951] [TID=59420] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=3
[1.354308] [TID=59417] [LOGGER] [INFO] JetStream ready: url=nats://127.0.0.1:4222 stream=FRAMES subject=frames.raw durable=drava_consumer
2026-02-14 15:55:36.307496: I external/local_xla/xla/service/service.cc:163] XLA service 0x7fe64800ea00 initialized for platform CUDA (this does not guarantee that XLA will be used). Devices:
2026-02-14 15:55:36.307521: I external/local_xla/xla/service/service.cc:171]   StreamExecutor device (0): NVIDIA A100-PCIE-40GB, Compute Capability 8.0
2026-02-14 15:55:36.340457: I tensorflow/compiler/mlir/tensorflow/utils/dump_mlir_util.cc:269] disabling MLIR crash reproducer, set env var `MLIR_CRASH_REPRODUCER_DIRECTORY` to enable.
2026-02-14 15:55:36.485683: I external/local_xla/xla/stream_executor/cuda/cuda_dnn.cc:473] Loaded cuDNN version 91900
I0000 00:00:1771084537.430287   59380 device_compiler.h:196] Compiled cluster using XLA!  This line is logged at most once for the lifetime of the process.
[42.973585] [TID=59419] [LOGGER] [INFO] [frames]=256 batch=128 step_ms=1640.13 avg_fps=156.08
[43.210645] [TID=59419] [LOGGER] [INFO] [frames]=512 batch=128 step_ms=234.80 avg_fps=272.75
[43.227551] [TID=59420] [LOGGER] [INFO] [frames]=768 batch=128 step_ms=250.76 avg_fps=405.47
[43.337478] [TID=59420] [LOGGER] [INFO] [frames]=1024 batch=128 step_ms=107.96 avg_fps=510.97
[43.399459] [TID=59419] [LOGGER] [INFO] [frames]=1280 batch=128 step_ms=91.12 avg_fps=619.55
[43.439984] [TID=59418] [LOGGER] [INFO] [frames]=1536 batch=128 step_ms=99.38 avg_fps=729.16
[43.549590] [TID=59418] [LOGGER] [INFO] [frames]=1792 batch=128 step_ms=107.68 avg_fps=808.62
[43.591817] [TID=59419] [LOGGER] [INFO] [frames]=2048 batch=128 step_ms=100.96 avg_fps=906.85
[43.666244] [TID=59420] [LOGGER] [INFO] [frames]=2304 batch=128 step_ms=113.87 avg_fps=987.66
[43.882436] [TID=59418] [LOGGER] [INFO] [frames]=2560 batch=128 step_ms=73.83 avg_fps=1004.32
[44.098450] [TID=59419] [LOGGER] [INFO] [frames]=2816 batch=128 step_ms=77.08 avg_fps=1018.44
[44.460374] [TID=59420] [LOGGER] [INFO] [frames]=3072 batch=128 step_ms=142.57 avg_fps=982.44
[44.607583] [TID=59418] [LOGGER] [INFO] [frames]=3328 batch=128 step_ms=75.54 avg_fps=1016.45
[44.906732] [TID=59419] [LOGGER] [INFO] [frames]=3584 batch=128 step_ms=77.83 avg_fps=1003.00


```