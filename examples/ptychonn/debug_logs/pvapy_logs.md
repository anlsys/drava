- PvaPy
```shell
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn/pvapy_baseline git:(main) ✗ python benchmark.py \
  --batches 128,256,512 \
  --runs 1 \
  --num-frames 3600 \
  --rate-hz 1000 \
  --monitor-queue 1024 \
  --start-settle-s 2

Running pvaPy baseline batch=128 run=1 ...
  done: publisher_avg_fps=999.97 stage1_fps=749.25 missed=0
Running pvaPy baseline batch=256 run=1 ...
  done: publisher_avg_fps=999.97 stage1_fps=746.57 missed=0
Running pvaPy baseline batch=512 run=1 ...
  done: publisher_avg_fps=999.97 stage1_fps=743.54 missed=0

Logs written to: /home/ashovon/drava/examples/ptychonn/pvapy_baseline/bench_logs/20260606_031138

| Batch | Frames | Pub FPS | Stage FPS | Missed | Stage Time (s) | Infer (s) | Publish (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 3600 | 999.97 | 749.25 | 0 | 4.80 | 3.30 | 0.04 |
| 256 | 3600 | 999.97 | 746.57 | 0 | 4.82 | 2.41 | 0.03 |
| 512 | 3600 | 999.97 | 743.54 | 0 | 4.84 | 1.95 | 0.03 |
Summary written to: /home/ashovon/drava/examples/ptychonn/pvapy_baseline/bench_logs/20260606_031138/summary.csv
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn/pvapy_baseline git:(main) ✗ cat /home/ashovon/drava/examples/ptychonn/pvapy_baseline/bench_logs/20260606_031138/summary.csv           
batch,run,num_frames,monitor_queue,publisher_time_s,publisher_avg_fps,rx_items,expected_frames,missed_frames,output_msgs,stage_total_s,stage_total_fps,infer_total_s,publish_total_s
128,1,3600,1024,3.6,999.97,3600,3600,0,226,4.8048,749.25,3.296634,0.036083
256,1,3600,1024,3.6,999.97,3600,3600,0,226,4.822068,746.57,2.407511,0.030933
512,1,3600,1024,3.6,999.97,3600,3600,0,226,4.841693,743.54,1.949863,0.026437


(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn/pvapy_baseline git:(main) ✗ python benchmark.py \
  --batches 128,256,512 \
  --runs 1 \
  --num-frames 3600 \
  --rate-hz 2000 \
  --monitor-queue 1024 \
  --start-settle-s 2

Running pvaPy baseline batch=128 run=1 ...
  done: publisher_avg_fps=1999.89 stage1_fps=1019.80 missed=0
Running pvaPy baseline batch=256 run=1 ...
  done: publisher_avg_fps=1999.86 stage1_fps=1193.86 missed=0
Running pvaPy baseline batch=512 run=1 ...
  done: publisher_avg_fps=1999.90 stage1_fps=1185.00 missed=0

Logs written to: /home/ashovon/drava/examples/ptychonn/pvapy_baseline/bench_logs/20260606_031728

| Batch | Frames | Pub FPS | Stage FPS | Missed | Stage Time (s) | Infer (s) | Publish (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 3600 | 1999.89 | 1019.80 | 0 | 3.53 | 3.34 | 0.04 |
| 256 | 3600 | 1999.86 | 1193.86 | 0 | 3.02 | 2.40 | 0.03 |
| 512 | 3600 | 1999.90 | 1185.00 | 0 | 3.04 | 1.94 | 0.03 |
Summary written to: /home/ashovon/drava/examples/ptychonn/pvapy_baseline/bench_logs/20260606_031728/summary.csv
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn/pvapy_baseline git:(main) ✗ cat /home/ashovon/drava/examples/ptychonn/pvapy_baseline/bench_logs/20260606_031728/summary.csv
batch,run,num_frames,monitor_queue,publisher_time_s,publisher_avg_fps,rx_items,expected_frames,missed_frames,output_msgs,stage_total_s,stage_total_fps,infer_total_s,publish_total_s
128,1,3600,1024,1.8,1999.89,3600,3600,0,226,3.530115,1019.8,3.344216,0.039667
256,1,3600,1024,1.8,1999.86,3600,3600,0,226,3.015418,1193.86,2.395602,0.030783
512,1,3600,1024,1.8,1999.9,3600,3600,0,226,3.037985,1185.0,1.938449,0.026653

(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn/pvapy_baseline git:(main) ✗ python benchmark.py \
  --batches 128,256,512 \
  --runs 1 \
  --num-frames 3600 \ 
  --rate-hz 3000 \
  --monitor-queue 1024 \
  --start-settle-s 2

Running pvaPy baseline batch=128 run=1 ...

Logs written to: /home/ashovon/drava/examples/ptychonn/pvapy_baseline/bench_logs/20260606_032759
Traceback (most recent call last):
  File "/home/ashovon/drava/examples/ptychonn/pvapy_baseline/benchmark.py", line 313, in <module>
    sys.exit(main())
             ~~~~^^
  File "/home/ashovon/drava/examples/ptychonn/pvapy_baseline/benchmark.py", line 276, in main
    row = run_one(args, root, run_dir, batch, run_idx)
  File "/home/ashovon/drava/examples/ptychonn/pvapy_baseline/benchmark.py", line 234, in run_one
    raise RuntimeError(
    ...<7 lines>...
    )
RuntimeError: pvaPy monitor lost frame updates: received=2816 expected=3600 missed=784 publisher_avg_fps=2999.79. The simple PvaServer record path overwrites the current PV value at this rate. Use a lower --rate-hz for a loss-free model baseline, or use the pvaPy HPC queued/distributor path for max-rate transport comparison.
--- consumer log ---
2026-06-06 03:27:59.804391: I tensorflow/core/platform/cpu_feature_guard.cc:210] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
To enable the following instructions: AVX2 FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
[pvapy-consumer] Visible GPUs: 1, [PhysicalDevice(name='/physical_device:GPU:0', device_type='GPU')]
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1780716483.386154   13174 gpu_device.cc:2020] Created device /job:localhost/replica:0/task:0/device:GPU:0 with 38503 MB memory:  -> device: 0, name: NVIDIA A100-PCIE-40GB, pci bus id: 0000:43:00.0, compute capability: 8.0
WARNING:absl:No training configuration found in the save file, so the model was *not* compiled. Compile it manually.
[pvapy-consumer] Loaded model: /home/ashovon/drava/examples/ptychonn/PtychoNN_data_partial/wts4/weights.66.hdf5
[pvapy-consumer] PVA output channel ready: ptychonn:stage1
2026-06-06 03:28:04.558042: I external/local_xla/xla/service/service.cc:163] XLA service 0x7f65d800b010 initialized for platform CUDA (this does not guarantee that XLA will be used). Devices:
2026-06-06 03:28:04.558068: I external/local_xla/xla/service/service.cc:171]   StreamExecutor device (0): NVIDIA A100-PCIE-40GB, Compute Capability 8.0
2026-06-06 03:28:04.590785: I tensorflow/compiler/mlir/tensorflow/utils/dump_mlir_util.cc:269] disabling MLIR crash reproducer, set env var `MLIR_CRASH_REPRODUCER_DIRECTORY` to enable.
2026-06-06 03:28:04.677700: I external/local_xla/xla/stream_executor/cuda/cuda_dnn.cc:473] Loaded cuDNN version 91900
I0000 00:00:1780716485.524117   13438 device_compiler.h:196] Compiled cluster using XLA!  This line is logged at most once for the lifetime of the process.
[pvapy-consumer] Warmup done: runs=2, batch=128
[pvapy-consumer] consumer ready: input=ptychonn:frames monitor_queue=1024
[pvapy-metrics] rx_items=2816 rx_bytes=46137344 expected_frames=3600 missed_frames=784 output_msgs=176 cb_batches=22 cb_avg_ms=83.146 infer_total_s=1.755487 publish_total_s=0.029277 stage_total_s=177.959707 stage_total_fps=15.82 publish_output=1

```

- Drava Hz
```shell
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(main) ✗ python benchmark.py \                                                                       
  --batches 128,256,512 \
  --runs 1 \
  --num-frames 3600 \
  --rate-hz 1000 \  
  --threads 4 \
  --timeout-ms 200 \
  --stage-config pipeline.yaml
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=128 run=1 ...
[batch=128 run=1] starting app.py
[batch=128 run=1] app ready
[batch=128 run=1] starting publisher_jetstream.py
[batch=128 run=1] publisher finished
[batch=128 run=1] waiting for drava metrics (timeout=45.0s)
[batch=128 run=1] drava metrics received
GPU Usage: [0.0, 3.0, 4.0, 8.0, 8.0]
  done: publisher_avg_fps=999.55 stage1_fps=781.05
Running batch=256 run=1 ...
[batch=256 run=1] starting app.py
[batch=256 run=1] app ready
[batch=256 run=1] starting publisher_jetstream.py
[batch=256 run=1] publisher finished
[batch=256 run=1] waiting for drava metrics (timeout=45.0s)
[batch=256 run=1] drava metrics received
GPU Usage: [9.0, 0.0, 8.0, 8.0, 8.0]
  done: publisher_avg_fps=999.62 stage1_fps=802.55
Running batch=512 run=1 ...
[batch=512 run=1] starting app.py
[batch=512 run=1] app ready
[batch=512 run=1] starting publisher_jetstream.py
[batch=512 run=1] publisher finished
[batch=512 run=1] waiting for drava metrics (timeout=45.0s)
[batch=512 run=1] drava metrics received
GPU Usage: [18.0, 9.0, 8.0, 3.0, 0.0]
  done: publisher_avg_fps=999.46 stage1_fps=850.52

| Batch | Threads | Total Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | GPU Avg (%) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4 | 3600 | 3.60 | 999.55 | 4.61 | 781.05 | 4.60 |
| 256 | 4 | 3600 | 3.60 | 999.62 | 4.49 | 802.55 | 6.60 |
| 512 | 4 | 3600 | 3.60 | 999.46 | 4.23 | 850.52 | 7.60 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_042013
pvaPy-style comparison summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_042013/comparison_summary.csv
[global] stopping nats-server
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(main) ✗ cat /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_042013/comparison_summary.csv
batch,run,num_frames,monitor_queue,publisher_time_s,publisher_avg_fps,rx_items,expected_frames,missed_frames,output_msgs,stage_total_s,stage_total_fps,infer_total_s,publish_total_s
128,1,3600,,3.602,999.55,3600,3600,0,226,4.609177,781.05,3.369661,0.03172
256,1,3600,,3.601,999.62,3600,3600,0,226,4.485729,802.55,2.46274,0.030418
512,1,3600,,3.602,999.46,3600,3600,0,226,4.232713,850.52,2.24584,0.029099

(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(main) ✗ python benchmark.py \
  --batches 128,256,512 \
  --runs 1 \
  --num-frames 3600 \
  --rate-hz 2000 \
  --threads 4 \
  --timeout-ms 200 \
  --stage-config pipeline.yaml
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=128 run=1 ...
[batch=128 run=1] starting app.py
[batch=128 run=1] app ready
[batch=128 run=1] starting publisher_jetstream.py
[batch=128 run=1] publisher finished
[batch=128 run=1] waiting for drava metrics (timeout=45.0s)
[batch=128 run=1] drava metrics received
GPU Usage: [0.0, 9.0, 12.0, 77.0]
  done: publisher_avg_fps=1998.09 stage1_fps=1249.19
Running batch=256 run=1 ...
[batch=256 run=1] starting app.py
[batch=256 run=1] app ready
[batch=256 run=1] starting publisher_jetstream.py
[batch=256 run=1] publisher finished
[batch=256 run=1] waiting for drava metrics (timeout=45.0s)
[batch=256 run=1] drava metrics received
GPU Usage: [9.0, 5.0, 8.0, 80.0]
  done: publisher_avg_fps=1997.56 stage1_fps=1277.87
Running batch=512 run=1 ...
[batch=512 run=1] starting app.py
[batch=512 run=1] app ready
[batch=512 run=1] starting publisher_jetstream.py
[batch=512 run=1] publisher finished
[batch=512 run=1] waiting for drava metrics (timeout=45.0s)
[batch=512 run=1] drava metrics received
GPU Usage: [19.0, 5.0, 1.0, 77.0]
  done: publisher_avg_fps=1997.66 stage1_fps=1330.67

| Batch | Threads | Total Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | GPU Avg (%) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4 | 3600 | 1.80 | 1998.09 | 2.88 | 1249.19 | 24.50 |
| 256 | 4 | 3600 | 1.80 | 1997.56 | 2.82 | 1277.87 | 25.50 |
| 512 | 4 | 3600 | 1.80 | 1997.66 | 2.71 | 1330.67 | 25.50 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_032010
pvaPy-style comparison summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_032010/comparison_summary.csv
[global] stopping nats-server
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(main) ✗ cat /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_032010/comparison_summary.csv
batch,run,num_frames,monitor_queue,publisher_time_s,publisher_avg_fps,rx_items,expected_frames,missed_frames,output_msgs,stage_total_s,stage_total_fps,infer_total_s,publish_total_s
128,1,3600,,1.802,1998.09,3600,3600,0,226,2.881859,1249.19,3.646993,0.030796
256,1,3600,,1.802,1997.56,3600,3600,0,226,2.817194,1277.87,2.640967,0.029343
512,1,3600,,1.802,1997.66,3600,3600,0,226,2.705411,1330.67,2.230958,0.030479

(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn/pvapy_baseline git:(main) ✗ cd ..            
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(main) ✗ python benchmark.py \
  --batches 128,256,512 \
  --runs 1 \
  --num-frames 3600 \ 
  --rate-hz 2500 \
  --threads 4 \         
  --timeout-ms 200 \
  --stage-config pipeline.yaml
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=128 run=1 ...
[batch=128 run=1] starting app.py
[batch=128 run=1] app ready
[batch=128 run=1] starting publisher_jetstream.py
[batch=128 run=1] publisher finished
[batch=128 run=1] waiting for drava metrics (timeout=45.0s)
[batch=128 run=1] drava metrics received
GPU Usage: [5.0, 8.0, 0.0]
  done: publisher_avg_fps=2497.17 stage1_fps=1421.86
Running batch=256 run=1 ...
[batch=256 run=1] starting app.py
[batch=256 run=1] app ready
[batch=256 run=1] starting publisher_jetstream.py
[batch=256 run=1] publisher finished
[batch=256 run=1] waiting for drava metrics (timeout=45.0s)
[batch=256 run=1] drava metrics received
GPU Usage: [9.0, 9.0, 3.0]
  done: publisher_avg_fps=2497.21 stage1_fps=1464.93
Running batch=512 run=1 ...
[batch=512 run=1] starting app.py
[batch=512 run=1] app ready
[batch=512 run=1] starting publisher_jetstream.py
[batch=512 run=1] publisher finished
[batch=512 run=1] waiting for drava metrics (timeout=45.0s)
[batch=512 run=1] drava metrics received
GPU Usage: [18.0, 9.0, 3.0]
  done: publisher_avg_fps=2496.47 stage1_fps=1523.60

| Batch | Threads | Total Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | GPU Avg (%) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4 | 3600 | 1.44 | 2497.17 | 2.53 | 1421.86 | 4.33 |
| 256 | 4 | 3600 | 1.44 | 2497.21 | 2.46 | 1464.93 | 7.00 |
| 512 | 4 | 3600 | 1.44 | 2496.47 | 2.36 | 1523.60 | 10.00 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_034543
pvaPy-style comparison summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_034543/comparison_summary.csv
[global] stopping nats-server
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(main) ✗ python benchmark.py \
  --batches 128,256,512 \
  --runs 1 \
  --num-frames 3600 \
  --rate-hz 3000 \
  --threads 4 \
  --timeout-ms 200 \
  --stage-config pipeline.yaml
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=128 run=1 ...
[batch=128 run=1] starting app.py
[batch=128 run=1] app ready
[batch=128 run=1] starting publisher_jetstream.py
[batch=128 run=1] publisher finished
[batch=128 run=1] waiting for drava metrics (timeout=45.0s)
[batch=128 run=1] drava metrics received
GPU Usage: [0.0, 10.0, 1.0]
  done: publisher_avg_fps=2995.08 stage1_fps=1568.01
Running batch=256 run=1 ...
[batch=256 run=1] starting app.py
[batch=256 run=1] app ready
[batch=256 run=1] starting publisher_jetstream.py
[batch=256 run=1] publisher finished
[batch=256 run=1] waiting for drava metrics (timeout=45.0s)
[batch=256 run=1] drava metrics received
GPU Usage: [9.0, 11.0, 5.0]
  done: publisher_avg_fps=2995.93 stage1_fps=1593.91
Running batch=512 run=1 ...
[batch=512 run=1] starting app.py
[batch=512 run=1] app ready
[batch=512 run=1] starting publisher_jetstream.py
[batch=512 run=1] publisher finished
[batch=512 run=1] waiting for drava metrics (timeout=45.0s)
[batch=512 run=1] drava metrics received
GPU Usage: [11.0, 9.0, 13.0]
  done: publisher_avg_fps=2994.74 stage1_fps=1670.74

| Batch | Threads | Total Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | GPU Avg (%) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4 | 3600 | 1.20 | 2995.08 | 2.30 | 1568.01 | 3.67 |
| 256 | 4 | 3600 | 1.20 | 2995.93 | 2.26 | 1593.91 | 8.33 |
| 512 | 4 | 3600 | 1.20 | 2994.74 | 2.15 | 1670.74 | 11.00 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_034639
pvaPy-style comparison summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_034639/comparison_summary.csv
[global] stopping nats-server
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(main) ✗ cat /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_034543/comparison_summary.csv
batch,run,num_frames,monitor_queue,publisher_time_s,publisher_avg_fps,rx_items,expected_frames,missed_frames,output_msgs,stage_total_s,stage_total_fps,infer_total_s,publish_total_s
128,1,3600,,1.442,2497.17,3600,3600,0,226,2.531899,1421.86,3.513393,0.030983
256,1,3600,,1.442,2497.21,3600,3600,0,226,2.457462,1464.93,2.62427,0.029919
512,1,3600,,1.442,2496.47,3600,3600,0,226,2.362824,1523.6,2.180551,0.029447
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(main) ✗ cat /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_034639/comparison_summary.csv
batch,run,num_frames,monitor_queue,publisher_time_s,publisher_avg_fps,rx_items,expected_frames,missed_frames,output_msgs,stage_total_s,stage_total_fps,infer_total_s,publish_total_s
128,1,3600,,1.202,2995.08,3600,3600,0,226,2.295906,1568.01,3.693054,0.031002
256,1,3600,,1.202,2995.93,3600,3600,0,226,2.258594,1593.91,2.749635,0.030063
512,1,3600,,1.202,2994.74,3600,3600,0,226,2.154735,1670.74,2.183526,0.031001
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(main) ✗ python benchmark.py \                                                                      
  --batches 128,256,512 \
  --runs 1 \
  --num-frames 3600 \
  --rate-hz 0 \   
  --threads 4 \
  --timeout-ms 200 \
  --stage-config pipeline.yaml
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=128 run=1 ...
[batch=128 run=1] starting app.py
[batch=128 run=1] app ready
[batch=128 run=1] starting publisher_jetstream.py
[batch=128 run=1] publisher finished
[batch=128 run=1] waiting for drava metrics (timeout=45.0s)
[batch=128 run=1] drava metrics received
GPU Usage: [2.0, 3.0]
  done: publisher_avg_fps=19532.25 stage1_fps=2161.66
Running batch=256 run=1 ...
[batch=256 run=1] starting app.py
[batch=256 run=1] app ready
[batch=256 run=1] starting publisher_jetstream.py
[batch=256 run=1] publisher finished
[batch=256 run=1] waiting for drava metrics (timeout=45.0s)
[batch=256 run=1] drava metrics received
GPU Usage: [5.0, 10.0]
  done: publisher_avg_fps=21613.38 stage1_fps=2782.69
Running batch=512 run=1 ...
[batch=512 run=1] starting app.py
[batch=512 run=1] app ready
[batch=512 run=1] starting publisher_jetstream.py
[batch=512 run=1] publisher finished
[batch=512 run=1] waiting for drava metrics (timeout=45.0s)
[batch=512 run=1] drava metrics received
GPU Usage: [18.0, 33.0]
  done: publisher_avg_fps=22746.86 stage1_fps=2817.91

| Batch | Threads | Total Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | GPU Avg (%) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4 | 3600 | 0.18 | 19532.25 | 1.67 | 2161.66 | 2.50 |
| 256 | 4 | 3600 | 0.17 | 21613.38 | 1.29 | 2782.69 | 7.50 |
| 512 | 4 | 3600 | 0.16 | 22746.86 | 1.28 | 2817.91 | 25.50 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_034843
pvaPy-style comparison summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_034843/comparison_summary.csv
[global] stopping nats-server
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(main) ✗ cat  /home/ashovon/drava/examples/ptychonn/bench_logs/20260606_034843/comparison_summary.csv
batch,run,num_frames,monitor_queue,publisher_time_s,publisher_avg_fps,rx_items,expected_frames,missed_frames,output_msgs,stage_total_s,stage_total_fps,infer_total_s,publish_total_s
128,1,3600,,0.184,19532.25,3600,3600,0,226,1.665384,2161.66,4.907112,0.031629
256,1,3600,,0.167,21613.38,3600,3600,0,226,1.293714,2782.69,3.726587,0.030861
512,1,3600,,0.158,22746.86,3600,3600,0,226,1.277544,2817.91,2.646855,0.029084
```

- Pvapy 100hz
```shell
python benchmark.py \
  --batches 128,256,512 \
  --runs 1 \
  --num-frames 3600 \
  --rate-hz 100 \
  --monitor-queue 1024 \
  --start-settle-s 2
Running pvaPy baseline batch=128 run=1 ...
  done: publisher_avg_fps=100.00 stage1_fps=97.01 missed=0
Running pvaPy baseline batch=256 run=1 ...
  done: publisher_avg_fps=100.00 stage1_fps=96.88 missed=0
Running pvaPy baseline batch=512 run=1 ...
  done: publisher_avg_fps=100.00 stage1_fps=96.92 missed=0

Logs written to: /home/ashovon/drava/examples/ptychonn/pvapy_baseline/bench_logs/20260605_213326

| Batch | Frames | Pub FPS | Stage FPS | Missed | Stage Time (s) | Infer (s) | Publish (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 3600 | 100.00 | 97.01 | 0 | 37.11 | 3.30 | 0.04 |
| 256 | 3600 | 100.00 | 96.88 | 0 | 37.16 | 2.42 | 0.03 |
| 512 | 3600 | 100.00 | 96.92 | 0 | 37.14 | 1.96 | 0.03 |
Summary written to: /home/ashovon/drava/examples/ptychonn/pvapy_baseline/bench_logs/20260605_213326/summary.csv
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn/pvapy_baseline git:(main) ✗ cat /home/ashovon/drava/examples/ptychonn/pvapy_baseline/bench_logs/20260605_213326/summary.csv
batch,run,num_frames,monitor_queue,publisher_time_s,publisher_avg_fps,rx_items,expected_frames,missed_frames,output_msgs,stage_total_s,stage_total_fps,infer_total_s,publish_total_s
128,1,3600,1024,36.0,100.0,3600,3600,0,226,37.108084,97.01,3.302576,0.038103
256,1,3600,1024,36.0,100.0,3600,3600,0,226,37.157561,96.88,2.417135,0.030941
512,1,3600,1024,36.0,100.0,3600,3600,0,226,37.144883,96.92,1.964707,0.026724

```
- Drava 100 hz
```shell
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(main) ✗ python benchmark.py \
  --batches 128,256,512 \
  --runs 1 \
  --num-frames 3600 \
  --rate-hz 100 \
  --threads 4 \
  --timeout-ms 200 \
  --stage-config pipeline.yaml \
  --nats-url nats://127.0.0.1:4222
[global] starting nats-server
[global] nats ready (nats://127.0.0.1:4222)
Running batch=128 run=1 ...
[batch=128 run=1] starting app.py
[batch=128 run=1] app ready
[batch=128 run=1] starting publisher_jetstream.py
[batch=128 run=1] publisher finished
[batch=128 run=1] waiting for drava metrics (timeout=45.0s)
[batch=128 run=1] drava metrics received
GPU Usage: [5.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.0, 4.0, 4.0, 0.0, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.0]
  done: publisher_avg_fps=99.99 stage1_fps=100.42
Running batch=256 run=1 ...
[batch=256 run=1] starting app.py
[batch=256 run=1] app ready
[batch=256 run=1] starting publisher_jetstream.py
[batch=256 run=1] publisher finished
[batch=256 run=1] waiting for drava metrics (timeout=45.0s)
[batch=256 run=1] drava metrics received
GPU Usage: [5.0, 0.0, 0.0, 8.0, 0.0, 0.0, 0.0, 0.0, 8.0, 0.0, 0.0, 0.0, 0.0, 8.0, 0.0, 0.0, 0.0, 0.0, 8.0, 0.0, 0.0, 0.0, 0.0, 8.0, 0.0, 0.0, 0.0, 0.0, 8.0, 0.0, 0.0, 0.0, 0.0, 8.0, 0.0, 0.0, 0.0]
  done: publisher_avg_fps=99.99 stage1_fps=104.12
Running batch=512 run=1 ...
[batch=512 run=1] starting app.py
[batch=512 run=1] app ready
[batch=512 run=1] starting publisher_jetstream.py
[batch=512 run=1] publisher finished
[batch=512 run=1] waiting for drava metrics (timeout=45.0s)
[batch=512 run=1] drava metrics received
GPU Usage: [2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  done: publisher_avg_fps=99.99 stage1_fps=112.49

| Batch | Threads | Total Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | GPU Avg (%) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 4 | 3600 | 36.00 | 99.99 | 35.85 | 100.42 | 1.00 |
| 256 | 4 | 3600 | 36.00 | 99.99 | 34.58 | 104.12 | 1.65 |
| 512 | 4 | 3600 | 36.00 | 99.99 | 32.00 | 112.49 | 0.05 |

Logs and summary written to: /home/ashovon/drava/examples/ptychonn/bench_logs/20260605_214153
[global] stopping nats-server
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(main) ✗ cd /home/ashovon/drava/examples/ptychonn/bench_logs/20260605_214153   
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn/bench_logs/20260605_214153 git:(main) ✗ ls
app_b128_r1.log  app_b256_r1.log  app_b512_r1.log  nats.log  pub_b128_r1.log  pub_b256_r1.log  pub_b512_r1.log  summary.csv
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn/bench_logs/20260605_214153 git:(main) ✗ cat summary.csv                                                                                
batch,threads,timeout_ms,total_frames,publisher_time_s,publisher_avg_fps,stage1_total_time_s,stage1_total_fps,stage1_compute_time_s,stage1_publish_time_s,gpu_avg_pct
128,4,200,3600,36.003,99.99,35.848241,100.42,None,None,1.0
256,4,200,3600,36.004,99.99,34.575836,104.12,None,None,1.6486486486486487
512,4,200,3600,36.002,99.99,32.003231,112.49,None,None,0.05405405405405406
```

- 200 hz
```shell
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn/pvapy_baseline git:(main) ✗ python benchmark.py \                                                                          
  --batches 128,256,512 \
  --runs 1 \
  --num-frames 3600 \
  --rate-hz 200 \
  --monitor-queue 1024 \
  --start-settle-s 2

Running pvaPy baseline batch=128 run=1 ...
  done: publisher_avg_fps=200.00 stage1_fps=188.32 missed=0
Running pvaPy baseline batch=256 run=1 ...
  done: publisher_avg_fps=200.00 stage1_fps=187.92 missed=0
Running pvaPy baseline batch=512 run=1 ...
  done: publisher_avg_fps=200.00 stage1_fps=187.91 missed=0

Logs written to: /home/ashovon/drava/examples/ptychonn/pvapy_baseline/bench_logs/20260605_214906

| Batch | Frames | Pub FPS | Stage FPS | Missed | Stage Time (s) | Infer (s) | Publish (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 3600 | 200.00 | 188.32 | 0 | 19.12 | 3.31 | 0.04 |
| 256 | 3600 | 200.00 | 187.92 | 0 | 19.16 | 2.42 | 0.03 |
| 512 | 3600 | 200.00 | 187.91 | 0 | 19.16 | 1.94 | 0.03 |
Summary written to: /home/ashovon/drava/examples/ptychonn/pvapy_baseline/bench_logs/20260605_214906/summary.csv
```
