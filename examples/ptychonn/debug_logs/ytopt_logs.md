```shell
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(feature/tomogan) ✗ python tune_two_stage_ytopt.py \
  --max-evals 24 \
  --initial-points 8 \
  --batches 256,512 \
  --stage1-threads 4,8,16 \
  --stage2-threads 2,4,8 \
  --stage1-callback-batches 256,512 \
  --stage2-callback-batches 64,128,256 \
  --rates 0,1000,2000 \
  --objective pipeline_e2e_s
ytopt tuning logs: /home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_174445
Running up to 24 benchmark evaluations.

[1/24] batch=256 s1_threads=4 s2_threads=2 s1_cb=256 s2_cb=64 rate_hz=0
  objective=4.50525 publisher_fps=16687.18 stage1_fps=4085.00 stage2_fps=2573.37 pipeline_e2e_s=4.51

[2/24] batch=256 s1_threads=16 s2_threads=8 s1_cb=256 s2_cb=64 rate_hz=1000
  objective=17.2374 publisher_fps=999.80 stage1_fps=918.57 stage2_fps=632.70 pipeline_e2e_s=17.24

[3/24] batch=256 s1_threads=16 s2_threads=4 s1_cb=256 s2_cb=128 rate_hz=1000
  failed: Traceback (most recent call last):
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 711, in <module>
    main()
    ~~~~^^
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 674, in main
    row = run_one(args, base_env, run_dir, b, run_idx)
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 541, in run_one
    fail_with_logs(run_dir, f"stage1 exited early\n--- stage1 tail ---\n{tail_text(stage1_log)}")
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 290, in fail_with_logs
    raise RuntimeError(f"{message}\n--- logs ---\n{run_dir}")
RuntimeError: stage1 exited early
--- stage1 tail ---
[2.446459][TID=14867] [LOGGER] [INFO] Built with support for `host, cuda`
[2.446462][TID=14867] [LOGGER] [INFO] Loading driver `HOST`
[2.457806][TID=15922] [LOGGER] [INFO]   global id =  0 | Unknown CPU
[2.457815][TID=15922] [LOGGER] [INFO] Found memory `RAM` of capacity 269GB
[2.457823][TID=15922] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 63 of node 0
[2.457837][TID=15924] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 35 of node 0
[2.457856][TID=15923] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 43 of node 0
[2.457874][TID=15925] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 41 of node 0
[2.457918][TID=14867] [LOGGER] [INFO] Loading driver `CUDA`
[2.457926][TID=14867] [LOGGER] [INFO] Calling cuInit(0) ...
[2.457935][TID=14867] [LOGGER] [INFO] Returned from cuInit(0)
[2.458075][TID=15926] [LOGGER] [INFO]   global id =  1 | NVIDIA A100-PCIE-40GB, cu device: 1, pci: 43:00, 42.41 (GB)
[2.458122][TID=15926] [LOGGER] [INFO] Found memory `(null)` of capacity 42GB
[2.458128][TID=15926] [LOGGER] [INFO] Starting thread for CUDA device (device_driver_id=0, device_global_id=1) on cpu 33 of node 0
[2.472621][TID=14867] [LOGGER] [INFO] Found 2 devices (with 2 requested)
[2.472641][TID=14867] [LOGGER] [INFO] drava_init: selected transport=nats
[2.472665][TID=14867] [LOGGER] [INFO] drava_register_frame_routine: routine=0x7fb1a402a240 user_data=(nil)
[2.472675][TID=14867] [LOGGER] [INFO] team->desc.nthreads: 16
[2.473529][TID=15927] [LOGGER] [INFO] Starting thread 0 on device 1
[2.473554][TID=15927] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=0
[2.473559][TID=15927] [LOGGER] [INFO] JetStream trying to connect
[2.473564][TID=15927] [LOGGER] [INFO] JetStream fetch config: batch=256 timeout_ms=200 callback_batch=256 callback_flush_timeout_ms=0
[2.473727][TID=15928] [LOGGER] [INFO] Starting thread 8 on device 1
[2.473751][TID=15931] [LOGGER] [INFO] Starting thread 1 on device 1
[2.473777][TID=15928] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=8
[2.473785][TID=15931] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=1
[2.473810][TID=15934] [LOGGER] [INFO] Starting thread 9 on device 1
[2.473838][TID=15934] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=9
[2.473916][TID=15933] [LOGGER] [INFO] Starting thread 10 on device 1
[2.473939][TID=15937] [LOGGER] [INFO] Starting thread 11 on device 1
[2.473963][TID=15929] [LOGGER] [INFO] Starting thread 4 on device 1
[2.473990][TID=15930] [LOGGER] [INFO] Starting thread 2 on device 1
[2.474011][TID=15929] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=4
[2.474024][TID=15933] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=10
[2.474036][TID=15939] [LOGGER] [INFO] Starting thread 3 on device 1
[2.474054][TID=15940] [LOGGER] [INFO] Starting thread 5 on device 1
[2.474072][TID=15938] [LOGGER] [INFO] Starting thread 14 on device 1
[2.474096][TID=15937] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=11
[2.474114][TID=15943] [LOGGER] [INFO] Starting thread 7 on device 1
[2.474137][TID=15938] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=14
--- logs ---
/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_174541

[4/24] batch=512 s1_threads=4 s2_threads=2 s1_cb=512 s2_cb=256 rate_hz=1000
  objective=19.3619 publisher_fps=999.80 stage1_fps=939.70 stage2_fps=675.89 pipeline_e2e_s=19.36

[5/24] batch=256 s1_threads=16 s2_threads=4 s1_cb=512 s2_cb=256 rate_hz=2000
  failed: Traceback (most recent call last):
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 711, in <module>
    main()
    ~~~~^^
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 674, in main
    row = run_one(args, base_env, run_dir, b, run_idx)
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 541, in run_one
    fail_with_logs(run_dir, f"stage1 exited early\n--- stage1 tail ---\n{tail_text(stage1_log)}")
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 290, in fail_with_logs
    raise RuntimeError(f"{message}\n--- logs ---\n{run_dir}")
RuntimeError: stage1 exited early
--- stage1 tail ---
[2.451883][TID=19596] [LOGGER] [INFO] Built with support for `host, cuda`
[2.451886][TID=19596] [LOGGER] [INFO] Loading driver `HOST`
[2.462944][TID=20323] [LOGGER] [INFO]   global id =  0 | Unknown CPU
[2.462952][TID=20323] [LOGGER] [INFO] Found memory `RAM` of capacity 269GB
[2.462961][TID=20323] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 63 of node 0
[2.462974][TID=20325] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 53 of node 0
[2.462991][TID=20326] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 59 of node 0
[2.463007][TID=20324] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 35 of node 0
[2.463050][TID=19596] [LOGGER] [INFO] Loading driver `CUDA`
[2.463059][TID=19596] [LOGGER] [INFO] Calling cuInit(0) ...
[2.463067][TID=19596] [LOGGER] [INFO] Returned from cuInit(0)
[2.463467][TID=20327] [LOGGER] [INFO]   global id =  1 | NVIDIA A100-PCIE-40GB, cu device: 1, pci: 43:00, 42.41 (GB)
[2.463517][TID=20327] [LOGGER] [INFO] Found memory `(null)` of capacity 42GB
[2.463523][TID=20327] [LOGGER] [INFO] Starting thread for CUDA device (device_driver_id=0, device_global_id=1) on cpu 43 of node 0
[2.477866][TID=19596] [LOGGER] [INFO] Found 2 devices (with 2 requested)
[2.477878][TID=19596] [LOGGER] [INFO] drava_init: selected transport=nats
[2.477893][TID=19596] [LOGGER] [INFO] drava_register_frame_routine: routine=0x7f104e862240 user_data=(nil)
[2.477900][TID=19596] [LOGGER] [INFO] team->desc.nthreads: 16
[2.478484][TID=20330] [LOGGER] [INFO] Starting thread 4 on device 1
[2.478501][TID=20330] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=4
[2.478509][TID=20335] [LOGGER] [INFO] Starting thread 5 on device 1
[2.478526][TID=20335] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=5
[2.478605][TID=20331] [LOGGER] [INFO] Starting thread 2 on device 1
[2.478624][TID=20328] [LOGGER] [INFO] Starting thread 0 on device 1
[2.478642][TID=20337] [LOGGER] [INFO] Starting thread 3 on device 1
[2.478663][TID=20328] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=0
[2.478671][TID=20328] [LOGGER] [INFO] JetStream trying to connect
[2.478674][TID=20337] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=3
[2.478686][TID=20328] [LOGGER] [INFO] JetStream fetch config: batch=256 timeout_ms=200 callback_batch=256 callback_flush_timeout_ms=0
[2.478691][TID=20334] [LOGGER] [INFO] Starting thread 1 on device 1
[2.478717][TID=20331] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=2
[2.478726][TID=20334] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=1
free(): invalid pointer
[2.478760][TID=20336] [LOGGER] [INFO] Starting thread 10 on device 1
[2.478786][TID=20336] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=10
[2.478820][TID=20339] [LOGGER] [INFO] Starting thread 11 on device 1
[2.478839][TID=20333] [LOGGER] [INFO] Starting thread 6 on device 1
[2.478858][TID=20329] [LOGGER] [INFO] Starting thread 8 on device 1
[2.478882][TID=20340] [LOGGER] [INFO] Starting thread 7 on device 1
[2.478900][TID=20333] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=6
--- logs ---
/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_174620

[6/24] batch=512 s1_threads=4 s2_threads=4 s1_cb=512 s2_cb=128 rate_hz=2000
  objective=15.1627 publisher_fps=1999.12 stage1_fps=1692.37 stage2_fps=731.05 pipeline_e2e_s=15.16

[7/24] batch=512 s1_threads=4 s2_threads=8 s1_cb=512 s2_cb=256 rate_hz=2000
  objective=15.8504 publisher_fps=1999.29 stage1_fps=1691.52 stage2_fps=750.40 pipeline_e2e_s=15.85

[8/24] batch=256 s1_threads=16 s2_threads=4 s1_cb=256 s2_cb=256 rate_hz=0
  failed: Traceback (most recent call last):
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 711, in <module>
    main()
    ~~~~^^
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 674, in main
    row = run_one(args, base_env, run_dir, b, run_idx)
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 543, in run_one
    fail_with_logs(run_dir, f"stage2 exited early\n--- stage2 tail ---\n{tail_text(stage2_log)}")
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 290, in fail_with_logs
    raise RuntimeError(f"{message}\n--- logs ---\n{run_dir}")
RuntimeError: stage2 exited early
--- stage2 tail ---
[0.000033][TID=27942] [LOGGER] [INFO] Initializing XKRT
[0.012810][TID=27942] [LOGGER] [WARN] Unknown environment variable 'XKAAPI_HOME=/home/rpereira/shared/install/xkaapi/502226c375a8/Debug-cuda'
[0.012835][TID=27942] [LOGGER] [IMPL] 'XKAAPI_CACHE_LIMIT' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[0.012839][TID=27942] [LOGGER] [IMPL] 'XKAAPI_DEFAULT_MATH' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[0.012845][TID=27942] [LOGGER] [IMPL] 'XKAAPI_PRECISION' at /home/rpereira/shared/repo/xkaapi/src/conf/conf.cc:320 in __parse_with_respect_to_prefix()
[0.012865][TID=27942] [LOGGER] [INFO] Created new task format `0` named `(null)`
[0.012868][TID=27942] [LOGGER] [INFO] Created new task format `1` named `host_capture`
[0.012871][TID=27942] [LOGGER] [INFO] Created new task format `2` named `memory_register_async`
[0.012874][TID=27942] [LOGGER] [INFO] Created new task format `3` named `memory_unregister_async`
[0.012876][TID=27942] [LOGGER] [INFO] Created new task format `4` named `memory_touch_async`
[0.012879][TID=27942] [LOGGER] [INFO] Created new task format `5` named `file_read_async`
[0.012881][TID=27942] [LOGGER] [INFO] Created new task format `6` named `file_write_async`
[0.012885][TID=27942] [LOGGER] [INFO] Built with support for `host, cuda`
[0.012889][TID=27942] [LOGGER] [INFO] Loading driver `HOST`
[0.028478][TID=28072] [LOGGER] [INFO]   global id =  0 | Unknown CPU
[0.028487][TID=28072] [LOGGER] [INFO] Found memory `RAM` of capacity 269GB
[0.028496][TID=28072] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 63 of node 0
[0.028501][TID=28075] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 45 of node 0
[0.028523][TID=28073] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 59 of node 0
[0.028543][TID=28074] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 41 of node 0
[0.028578][TID=27942] [LOGGER] [INFO] Loading driver `CUDA`
[0.028588][TID=27942] [LOGGER] [INFO] Calling cuInit(0) ...
[0.091696][TID=27942] [LOGGER] [INFO] Returned from cuInit(0)
[0.231375][TID=28082] [LOGGER] [INFO]   global id =  1 | NVIDIA A100-PCIE-40GB, cu device: 1, pci: 43:00, 42.41 (GB)
[0.231440][TID=28082] [LOGGER] [INFO] Found memory `(null)` of capacity 42GB
[0.231449][TID=28082] [LOGGER] [INFO] Starting thread for CUDA device (device_driver_id=0, device_global_id=1) on cpu 53 of node 0
[0.262112][TID=27942] [LOGGER] [INFO] Found 2 devices (with 2 requested)
[0.262132][TID=27942] [LOGGER] [INFO] drava_init: selected transport=nats
[0.262158][TID=27942] [LOGGER] [INFO] [stage2] registering callback
[0.262165][TID=27942] [LOGGER] [INFO] drava_register_frame_routine: routine=0x7f73b0d62240 user_data=(nil)
[0.262172][TID=27942] [LOGGER] [INFO] [stage2] entering listen loop
[0.262178][TID=27942] [LOGGER] [INFO] team->desc.nthreads: 4
[0.262641][TID=28083] [LOGGER] [INFO] Starting thread 0 on device 1
[0.262658][TID=28083] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=0
[0.262665][TID=28083] [LOGGER] [INFO] JetStream trying to connect
[0.262669][TID=28083] [LOGGER] [INFO] JetStream fetch config: batch=256 timeout_ms=200 callback_batch=256 callback_flush_timeout_ms=0
[0.262695][TID=28085] [LOGGER] [INFO] Starting thread 1 on device 1
[0.262714][TID=28085] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=1
[0.262742][TID=28084] [LOGGER] [INFO] Starting thread 2 on device 1
[0.262767][TID=28084] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=2
--- logs ---
/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_174725

[9/24] batch=256 s1_threads=4 s2_threads=2 s1_cb=256 s2_cb=128 rate_hz=0
  objective=7.44606 publisher_fps=16170.39 stage1_fps=4231.88 stage2_fps=1500.03 pipeline_e2e_s=7.45

[10/24] batch=256 s1_threads=16 s2_threads=4 s1_cb=256 s2_cb=256 rate_hz=2000
  failed: Traceback (most recent call last):
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 711, in <module>
    main()
    ~~~~^^
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 674, in main
    row = run_one(args, base_env, run_dir, b, run_idx)
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 541, in run_one
    fail_with_logs(run_dir, f"stage1 exited early\n--- stage1 tail ---\n{tail_text(stage1_log)}")
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 290, in fail_with_logs
    raise RuntimeError(f"{message}\n--- logs ---\n{run_dir}")
RuntimeError: stage1 exited early
--- stage1 tail ---
[2.489423][TID=35245] [LOGGER] [INFO] Loading driver `CUDA`
[2.489429][TID=35245] [LOGGER] [INFO] Calling cuInit(0) ...
[2.489436][TID=35245] [LOGGER] [INFO] Returned from cuInit(0)
[2.489588][TID=35977] [LOGGER] [INFO]   global id =  1 | NVIDIA A100-PCIE-40GB, cu device: 1, pci: 43:00, 42.41 (GB)
[2.489636][TID=35977] [LOGGER] [INFO] Found memory `(null)` of capacity 42GB
[2.489642][TID=35977] [LOGGER] [INFO] Starting thread for CUDA device (device_driver_id=0, device_global_id=1) on cpu 37 of node 0
[2.504291][TID=35245] [LOGGER] [INFO] Found 2 devices (with 2 requested)
[2.504300][TID=35245] [LOGGER] [INFO] drava_init: selected transport=nats
[2.504312][TID=35245] [LOGGER] [INFO] drava_register_frame_routine: routine=0x7f8491625240 user_data=(nil)
[2.504316][TID=35245] [LOGGER] [INFO] team->desc.nthreads: 16
[2.505066][TID=35981] [LOGGER] [INFO] Starting thread 2 on device 1
[2.505082][TID=35985] [LOGGER] [INFO] Starting thread 6 on device 1
[2.505106][TID=35978] [LOGGER] [INFO] Starting thread 0 on device 1
[2.505127][TID=35981] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=2
[2.505133][TID=35984] [LOGGER] [INFO] Starting thread 1 on device 1
[2.505142][TID=35984] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=1
[2.505150][TID=35988] [LOGGER] [INFO] Starting thread 9 on device 1
[2.505169][TID=35985] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=6
[2.505179][TID=35986] [LOGGER] [INFO] Starting thread 10 on device 1
[2.505206][TID=35988] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=9
[2.505215][TID=35983] [LOGGER] [INFO] Starting thread 3 on device 1
[2.505241][TID=35979] [LOGGER] [INFO] Starting thread 8 on device 1
[2.505257][TID=35978] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=0
[2.505265][TID=35978] [LOGGER] [INFO] JetStream trying to connect
[2.505268][TID=35986] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=10
[2.505278][TID=35983] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=3
[2.505288][TID=35979] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=8
[2.505294][TID=35978] [LOGGER] [INFO] JetStream fetch config: batch=256 timeout_ms=200 callback_batch=256 callback_flush_timeout_ms=0
[2.505473][TID=35987] [LOGGER] [INFO] Starting thread 7 on device 1
[2.505497][TID=35980] [LOGGER] [INFO] Starting thread 4 on device 1
[2.505516][TID=35987] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=7
[2.505525][TID=35980] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=4
[2.505537][TID=35989] [LOGGER] [INFO] Starting thread 11 on device 1
[2.505562][TID=35989] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=11
[2.505572][TID=35990] [LOGGER] [INFO] Starting thread 5 on device 1
[2.505590][TID=35990] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=5
[2.505623][TID=35982] [LOGGER] [INFO] Starting thread 12 on device 1
[2.505648][TID=35982] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=12
[2.505657][TID=35992] [LOGGER] [INFO] Starting thread 13 on device 1
[2.505680][TID=35992] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=13
--- logs ---
/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_174751

[11/24] batch=256 s1_threads=4 s2_threads=2 s1_cb=512 s2_cb=128 rate_hz=0
  objective=6.31508 publisher_fps=17020.90 stage1_fps=4075.54 stage2_fps=1818.24 pipeline_e2e_s=6.32

[12/24] batch=256 s1_threads=16 s2_threads=2 s1_cb=256 s2_cb=128 rate_hz=0
  objective=7.88191 publisher_fps=17505.16 stage1_fps=4375.10 stage2_fps=1449.35 pipeline_e2e_s=7.88

[13/24] batch=256 s1_threads=8 s2_threads=2 s1_cb=256 s2_cb=128 rate_hz=0
  objective=10.3291 publisher_fps=17017.36 stage1_fps=5000.47 stage2_fps=1048.83 pipeline_e2e_s=10.33

[14/24] batch=256 s1_threads=4 s2_threads=2 s1_cb=256 s2_cb=256 rate_hz=0
  objective=6.19739 publisher_fps=17223.25 stage1_fps=4131.80 stage2_fps=2100.17 pipeline_e2e_s=6.20

[15/24] batch=256 s1_threads=16 s2_threads=2 s1_cb=256 s2_cb=64 rate_hz=0
  failed: Traceback (most recent call last):
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 711, in <module>
    main()
    ~~~~^^
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 674, in main
    row = run_one(args, base_env, run_dir, b, run_idx)
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 541, in run_one
    fail_with_logs(run_dir, f"stage1 exited early\n--- stage1 tail ---\n{tail_text(stage1_log)}")
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ashovon/drava/examples/ptychonn/benchmark_two_stages.py", line 290, in fail_with_logs
    raise RuntimeError(f"{message}\n--- logs ---\n{run_dir}")
RuntimeError: stage1 exited early
--- stage1 tail ---
[2.487156][TID=61446] [LOGGER] [INFO] Loading driver `HOST`
[2.499884][TID=62173] [LOGGER] [INFO]   global id =  0 | Unknown CPU
[2.499892][TID=62173] [LOGGER] [INFO] Found memory `RAM` of capacity 269GB
[2.499901][TID=62173] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 63 of node 0
[2.499915][TID=62175] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 25 of node 0
[2.499932][TID=62174] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 45 of node 0
[2.499951][TID=62176] [LOGGER] [INFO] Starting thread for HOST device (device_driver_id=0, device_global_id=0) on cpu 59 of node 0
[2.499988][TID=61446] [LOGGER] [INFO] Loading driver `CUDA`
[2.499996][TID=61446] [LOGGER] [INFO] Calling cuInit(0) ...
[2.500003][TID=61446] [LOGGER] [INFO] Returned from cuInit(0)
[2.500141][TID=62177] [LOGGER] [INFO]   global id =  1 | NVIDIA A100-PCIE-40GB, cu device: 1, pci: 43:00, 42.41 (GB)
[2.500190][TID=62177] [LOGGER] [INFO] Found memory `(null)` of capacity 42GB
[2.500196][TID=62177] [LOGGER] [INFO] Starting thread for CUDA device (device_driver_id=0, device_global_id=1) on cpu 47 of node 0
[2.518505][TID=61446] [LOGGER] [INFO] Found 2 devices (with 2 requested)
[2.518523][TID=61446] [LOGGER] [INFO] drava_init: selected transport=nats
[2.518541][TID=61446] [LOGGER] [INFO] drava_register_frame_routine: routine=0x7fd5d866e240 user_data=(nil)
[2.518549][TID=61446] [LOGGER] [INFO] team->desc.nthreads: 16
[2.519456][TID=62180] [LOGGER] [INFO] Starting thread 4 on device 1
[2.519481][TID=62181] [LOGGER] [INFO] Starting thread 2 on device 1
[2.519500][TID=62184] [LOGGER] [INFO] Starting thread 5 on device 1
[2.519525][TID=62181] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=2
[2.519533][TID=62180] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=4
[2.519543][TID=62182] [LOGGER] [INFO] Starting thread 6 on device 1
[2.519566][TID=62185] [LOGGER] [INFO] Starting thread 3 on device 1
[2.519589][TID=62182] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=6
[2.519601][TID=62184] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=5
[2.519610][TID=62185] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=3
[2.519620][TID=62179] [LOGGER] [INFO] Starting thread 8 on device 1
[2.519644][TID=62183] [LOGGER] [INFO] Starting thread 12 on device 1
[2.519670][TID=62178] [LOGGER] [INFO] Starting thread 0 on device 1
[2.519693][TID=62189] [LOGGER] [INFO] Starting thread 9 on device 1
[2.519713][TID=62189] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=9
[2.519727][TID=62191] [LOGGER] [INFO] Starting thread 1 on device 1
[2.519746][TID=62187] [LOGGER] [INFO] Starting thread 7 on device 1
[2.519769][TID=62187] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=7
[2.519778][TID=62192] [LOGGER] [INFO] Starting thread 15 on device 1
[2.519799][TID=62192] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=15
[2.519808][TID=62183] [LOGGER] [INFO] drava_transport_nats_main: device=1 tid=12
[2.519822][TID=62188] [LOGGER] [INFO] Starting thread 14 on device 1
[2.519840][TID=62186] [LOGGER] [INFO] 
--- logs ---
/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_174932

[16/24] batch=256 s1_threads=4 s2_threads=2 s1_cb=512 s2_cb=64 rate_hz=0
  objective=4.28902 publisher_fps=17558.02 stage1_fps=3942.69 stage2_fps=2719.91 pipeline_e2e_s=4.29

[17/24] batch=512 s1_threads=4 s2_threads=2 s1_cb=512 s2_cb=64 rate_hz=0
  objective=12.2734 publisher_fps=17439.98 stage1_fps=5337.57 stage2_fps=860.21 pipeline_e2e_s=12.27

[18/24] batch=256 s1_threads=4 s2_threads=8 s1_cb=256 s2_cb=64 rate_hz=0
  objective=6.17181 publisher_fps=17342.31 stage1_fps=4218.58 stage2_fps=1788.28 pipeline_e2e_s=6.17

[19/24] batch=256 s1_threads=8 s2_threads=2 s1_cb=512 s2_cb=64 rate_hz=0
  objective=11.7941 publisher_fps=15813.85 stage1_fps=4570.18 stage2_fps=905.41 pipeline_e2e_s=11.79

[20/24] batch=256 s1_threads=4 s2_threads=4 s1_cb=256 s2_cb=64 rate_hz=0
  objective=5.63603 publisher_fps=16740.47 stage1_fps=4162.85 stage2_fps=1982.39 pipeline_e2e_s=5.64

[21/24] batch=256 s1_threads=4 s2_threads=4 s1_cb=256 s2_cb=256 rate_hz=0
  objective=7.17055 publisher_fps=16196.05 stage1_fps=4154.82 stage2_fps=1736.72 pipeline_e2e_s=7.17

[22/24] batch=512 s1_threads=4 s2_threads=4 s1_cb=256 s2_cb=64 rate_hz=0
  objective=12.6737 publisher_fps=16119.36 stage1_fps=5338.12 stage2_fps=827.54 pipeline_e2e_s=12.67

[23/24] batch=256 s1_threads=4 s2_threads=8 s1_cb=512 s2_cb=64 rate_hz=0
  objective=6.20255 publisher_fps=16255.87 stage1_fps=4149.05 stage2_fps=1800.16 pipeline_e2e_s=6.20

[24/24] batch=256 s1_threads=4 s2_threads=4 s1_cb=512 s2_cb=64 rate_hz=0
  objective=5.5162 publisher_fps=16311.86 stage1_fps=4068.36 stage2_fps=2053.67 pipeline_e2e_s=5.52

| Rank | Eval | Batch | Threads S1/S2 | Callback S1/S2 | Rate Hz | Publisher FPS | Stage1 FPS | Stage2 FPS | Pipeline E2E (s) | Summary |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 16 | 256 | 4/2 | 512/64 | 0.00 | 17558.02 | 3942.69 | 2719.91 | 4.29 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_174940 |
| 2 | 1 | 256 | 4/2 | 256/64 | 0.00 | 16687.18 | 4085.00 | 2573.37 | 4.51 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_174453 |
| 3 | 24 | 256 | 4/4 | 512/64 | 0.00 | 16311.86 | 4068.36 | 2053.67 | 5.52 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_175252 |
| 4 | 20 | 256 | 4/4 | 256/64 | 0.00 | 16740.47 | 4162.85 | 1982.39 | 5.64 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_175117 |
| 5 | 18 | 256 | 4/8 | 256/64 | 0.00 | 17342.31 | 4218.58 | 1788.28 | 6.17 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_175028 |
| 6 | 14 | 256 | 4/2 | 256/256 | 0.00 | 17223.25 | 4131.80 | 2100.17 | 6.20 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_174910 |
| 7 | 23 | 256 | 4/8 | 512/64 | 0.00 | 16255.87 | 4149.05 | 1800.16 | 6.20 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_175229 |
| 8 | 11 | 256 | 4/2 | 512/128 | 0.00 | 17020.90 | 4075.54 | 1818.24 | 6.32 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_174759 |
| 9 | 21 | 256 | 4/4 | 256/256 | 0.00 | 16196.05 | 4154.82 | 1736.72 | 7.17 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_175138 |
| 10 | 9 | 256 | 4/2 | 256/128 | 0.00 | 16170.39 | 4231.88 | 1500.03 | 7.45 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_174728 |

Sorted by `pipeline_e2e_s` (ascending).

Aggregate CSV written to: /home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_174445/aggregate.csv
Recorded 5 failures in: /home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_174445/failures.csv
ytopt tuner logs written to: /home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_174445
```