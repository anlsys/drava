### A 100
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