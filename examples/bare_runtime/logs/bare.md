```shell
(no-gil-3.13) (base) ➜  ~/drava git:(main) ✗ python experiments/sc5_bare_runtime_ceiling.py \
  --batches 8,32,128,256,512 \
  --thread-list 2,4,8 \
  --payload-bytes 1 \
  --gpu-backend auto \
  --kernel-launches 1 \
  --num-frames 100000 \
  --runs 1
[sc5-bare-runtime] writing to /home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247
[sc5-bare-runtime] starting nats-server
[sc5-bare-runtime] nats ready (nats://127.0.0.1:4222)
[sc5-bare-runtime] batch=8 threads=2 payload=1 serialize=0 run=1
  done: pipeline_fps=7698.16 stage_fps=7843.13 cb_avg_ms=0.015
[sc5-bare-runtime] batch=32 threads=2 payload=1 serialize=0 run=1
  done: pipeline_fps=27869.46 stage_fps=29168.57 cb_avg_ms=0.018
[sc5-bare-runtime] batch=128 threads=2 payload=1 serialize=0 run=1
  done: pipeline_fps=31447.72 stage_fps=33100.57 cb_avg_ms=0.048
[sc5-bare-runtime] batch=256 threads=2 payload=1 serialize=0 run=1
  done: pipeline_fps=29910.73 stage_fps=31439.57 cb_avg_ms=0.066
[sc5-bare-runtime] batch=512 threads=2 payload=1 serialize=0 run=1
  done: pipeline_fps=30487.98 stage_fps=32089.93 cb_avg_ms=0.110
[sc5-bare-runtime] batch=8 threads=4 payload=1 serialize=0 run=1
  done: pipeline_fps=7779.06 stage_fps=7888.39 cb_avg_ms=0.031
[sc5-bare-runtime] batch=32 threads=4 payload=1 serialize=0 run=1
  done: pipeline_fps=28040.07 stage_fps=29601.73 cb_avg_ms=0.035
[sc5-bare-runtime] batch=128 threads=4 payload=1 serialize=0 run=1
  done: pipeline_fps=31661.58 stage_fps=33386.89 cb_avg_ms=0.050
[sc5-bare-runtime] batch=256 threads=4 payload=1 serialize=0 run=1
  done: pipeline_fps=30957.73 stage_fps=32622.46 cb_avg_ms=0.081
[sc5-bare-runtime] batch=512 threads=4 payload=1 serialize=0 run=1
  done: pipeline_fps=31114.31 stage_fps=32847.02 cb_avg_ms=0.129
[sc5-bare-runtime] batch=8 threads=8 payload=1 serialize=0 run=1
  done: pipeline_fps=7799.45 stage_fps=7897.51 cb_avg_ms=0.034
[sc5-bare-runtime] batch=32 threads=8 payload=1 serialize=0 run=1
  done: pipeline_fps=28104.53 stage_fps=29609.05 cb_avg_ms=0.038
[sc5-bare-runtime] batch=128 threads=8 payload=1 serialize=0 run=1
  done: pipeline_fps=31469.02 stage_fps=33165.90 cb_avg_ms=0.054
[sc5-bare-runtime] batch=256 threads=8 payload=1 serialize=0 run=1
  done: pipeline_fps=31027.33 stage_fps=32699.05 cb_avg_ms=0.089
[sc5-bare-runtime] batch=512 threads=8 payload=1 serialize=0 run=1
  done: pipeline_fps=30814.78 stage_fps=32884.59 cb_avg_ms=0.116

| Batch | Threads | Payload B | Ser | Frames | Pipeline FPS | Stage FPS | cb avg ms | Stage max ms | Backend |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 8 | 2 | 1 | 0 | 100000 | 7698.16 | 7843.13 | 0.015 | 0.000 | none |
| 32 | 2 | 1 | 0 | 100000 | 27869.46 | 29168.57 | 0.018 | 0.000 | none |
| 128 | 2 | 1 | 0 | 100000 | 31447.72 | 33100.57 | 0.048 | 0.000 | none |
| 256 | 2 | 1 | 0 | 100000 | 29910.73 | 31439.57 | 0.066 | 0.000 | none |
| 512 | 2 | 1 | 0 | 100000 | 30487.98 | 32089.93 | 0.110 | 0.000 | none |
| 8 | 4 | 1 | 0 | 100000 | 7779.06 | 7888.39 | 0.031 | 0.000 | none |
| 32 | 4 | 1 | 0 | 100000 | 28040.07 | 29601.73 | 0.035 | 0.000 | none |
| 128 | 4 | 1 | 0 | 100000 | 31661.58 | 33386.89 | 0.050 | 0.000 | none |
| 256 | 4 | 1 | 0 | 100000 | 30957.73 | 32622.46 | 0.081 | 0.000 | none |
| 512 | 4 | 1 | 0 | 100000 | 31114.31 | 32847.02 | 0.129 | 0.000 | none |
| 8 | 8 | 1 | 0 | 100000 | 7799.45 | 7897.51 | 0.034 | 0.000 | none |
| 32 | 8 | 1 | 0 | 100000 | 28104.53 | 29609.05 | 0.038 | 0.000 | none |
| 128 | 8 | 1 | 0 | 100000 | 31469.02 | 33165.90 | 0.054 | 0.000 | none |
| 256 | 8 | 1 | 0 | 100000 | 31027.33 | 32699.05 | 0.089 | 0.000 | none |
| 512 | 8 | 1 | 0 | 100000 | 30814.78 | 32884.59 | 0.116 | 0.000 | none |

Wrote raw summary: /home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/sc5_bare_runtime_ceiling_summary.csv
Wrote aggregate summary: /home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/sc5_bare_runtime_ceiling_aggregate.csv
[sc5-bare-runtime] stopping nats-server
(no-gil-3.13) (base) ➜  ~/drava git:(main) ✗ cat /home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/sc5_bare_runtime_ceiling_summary.csv
experiment,config,run,batch,threads,fetch_batch,timeout_ms,payload_bytes,output_payload_bytes,callback_serialize,gpu_backend_requested,gpu_backend_selected,kernel_launches,kernel_blocks,kernel_threads,gpu_sync,publish_mode,rate_hz,frames,publisher_time_s,publisher_fps,pipeline_e2e_s,pipeline_fps,stage_total_s,stage_total_fps,runtime_gap_s,runtime_gap_pct,rx_msgs,rx_items,rx_bytes,tx_msgs,tx_bytes,callback_batches,cb_avg_ms,stage_samples,stage_avg_ms,stage_max_ms,cb_total_s,compute_total_s,publish_total_s,app_log,publisher_log
bare_runtime_ceiling,b8_t2_p1_s0,1,8,2,8,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,2.991,33429.11,12.990118460962549,7698.159204669035,12.750012,7843.13,0.24010646096254895,1.8483777625593525,12501,100000,100016,0,0,12501,0.015,0,0.0,0.0,0.18969,0.18969,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b8_t2_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b8_t2_p1_s0_r1.log
bare_runtime_ceiling,b32_t2_p1_s0,1,32,2,32,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,3.02,33114.12,3.5881576269166544,27869.455692204683,3.428347,29168.57,0.15981062691665437,4.453835185997153,3126,100000,100016,0,0,3126,0.018,0,0.0,0.0,0.056093,0.056093,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b32_t2_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b32_t2_p1_s0_r1.log
bare_runtime_ceiling,b128_t2_p1_s0,1,128,2,128,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,3.04,32898.39,3.1798809370957315,31447.71831970936,3.021096,33100.57,0.1587849370957315,4.993423975199334,782,100000,100016,0,0,782,0.048,0,0.0,0.0,0.037896,0.037896,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b128_t2_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b128_t2_p1_s0_r1.log
bare_runtime_ceiling,b256_t2_p1_s0,1,256,2,256,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,3.201,31243.94,3.3432815599953756,29910.732376407545,3.180705,31439.57,0.16257655999537546,4.8627839766986405,391,100000,100016,0,0,391,0.066,0,0.0,0.0,0.025667,0.025667,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b256_t2_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b256_t2_p1_s0_r1.log
bare_runtime_ceiling,b512_t2_p1_s0,1,512,2,512,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,3.139,31854.65,3.279980876017362,30487.982637698366,3.116242,32089.93,0.1637388760173617,4.992068009133568,196,100000,100016,0,0,196,0.11,0,0.0,0.0,0.021542,0.021542,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b512_t2_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b512_t2_p1_s0_r1.log
bare_runtime_ceiling,b8_t4_p1_s0,1,8,4,8,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,2.972,33647.53,12.855017497902736,7779.06370149358,12.676862,7888.39,0.17815549790273622,1.385882966956691,12501,100000,100016,0,0,12501,0.031,0,0.0,0.0,0.390713,0.390713,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b8_t4_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b8_t4_p1_s0_r1.log
bare_runtime_ceiling,b32_t4_p1_s0,1,32,4,32,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,3.011,33209.92,3.566325339023024,28040.06659341811,3.378181,29601.73,0.18814433902302374,5.275579795380219,3126,100000,100016,0,0,3126,0.035,0,0.0,0.0,0.109533,0.109533,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b32_t4_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b32_t4_p1_s0_r1.log
bare_runtime_ceiling,b128_t4_p1_s0,1,128,4,128,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,3.016,33160.83,3.158402519999072,31661.5755486509,2.995188,33386.89,0.16321451999907177,5.167628855587404,782,100000,100016,0,0,782,0.05,0,0.0,0.0,0.039469,0.039469,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b128_t4_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b128_t4_p1_s0_r1.log
bare_runtime_ceiling,b256_t4_p1_s0,1,256,4,256,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,3.089,32370.11,3.2302110390737653,30957.729631397124,3.065373,32622.46,0.16483803907376515,5.103011446615296,391,100000,100016,0,0,391,0.081,0,0.0,0.0,0.031672,0.031672,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b256_t4_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b256_t4_p1_s0_r1.log
bare_runtime_ceiling,b512_t4_p1_s0,1,512,4,512,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,3.069,32584.62,3.2139551730360836,31114.310752982394,3.044416,32847.02,0.16953917303608357,5.275094514648358,196,100000,100016,0,0,196,0.129,0,0.0,0.0,0.025303,0.025303,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b512_t4_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b512_t4_p1_s0_r1.log
bare_runtime_ceiling,b8_t8_p1_s0,1,8,8,8,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,3.053,32751.35,12.821422026026994,7799.446878591458,12.662226,7897.51,0.15919602602699356,1.2416409482803994,12501,100000,100016,0,0,12501,0.034,0,0.0,0.0,0.427813,0.427813,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b8_t8_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b8_t8_p1_s0_r1.log
bare_runtime_ceiling,b32_t8_p1_s0,1,32,8,32,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,3.032,32980.38,3.5581452450715005,28104.53006057388,3.377346,29609.05,0.18079924507150036,5.081277818041046,3126,100000,100016,0,0,3126,0.038,0,0.0,0.0,0.118018,0.118018,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b32_t8_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b32_t8_p1_s0_r1.log
bare_runtime_ceiling,b128_t8_p1_s0,1,128,8,128,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,3.036,32933.74,3.177728509064764,31469.019368627865,3.015145,33165.9,0.16258350906476382,5.116343595778536,782,100000,100016,0,0,782,0.054,0,0.0,0.0,0.041971,0.041971,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b128_t8_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b128_t8_p1_s0_r1.log
bare_runtime_ceiling,b256_t8_p1_s0,1,256,8,256,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,3.08,32471.16,3.222965070977807,31027.329740704034,3.058193,32699.05,0.16477207097780688,5.112437378287103,391,100000,100016,0,0,391,0.089,0,0.0,0.0,0.034728,0.034728,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b256_t8_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b256_t8_p1_s0_r1.log
bare_runtime_ceiling,b512_t8_p1_s0,1,512,8,512,200,1,1,0,auto,none,1,1,1,1,none,0.0,100000,3.065,32624.82,3.2451956178992987,30814.78338268331,3.040938,32884.59,0.20425761789929853,6.294154249829781,196,100000,100016,0,0,196,0.116,0,0.0,0.0,0.022786,0.022786,0.0,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/app_sc5_bare_runtime_ceiling_20260605_141247_b512_t8_p1_s0_r1.log,/home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/pub_sc5_bare_runtime_ceiling_20260605_141247_b512_t8_p1_s0_r1.log
(no-gil-3.13) (base) ➜  ~/drava git:(main) ✗ cat /home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_141247/sc5_bare_runtime_ceiling_aggregate.csv
experiment,config,batch,threads,payload_bytes,callback_serialize,runs,frames,gpu_backend_selected,publish_mode,pipeline_fps_mean,pipeline_fps_std,stage_total_fps_mean,stage_total_fps_std,pipeline_e2e_s_mean,cb_avg_ms_mean,stage_avg_ms_mean,stage_max_ms_mean,compute_total_s_mean,publish_total_s_mean,runtime_gap_pct_mean
bare_runtime_ceiling,b8_t2_p1_s0,8,2,1,0,1,100000,none,none,7698.159204669035,0.0,7843.13,0.0,12.990118460962549,0.015,0.0,0.0,0.18969,0.0,1.8483777625593525
bare_runtime_ceiling,b8_t4_p1_s0,8,4,1,0,1,100000,none,none,7779.06370149358,0.0,7888.39,0.0,12.855017497902736,0.031,0.0,0.0,0.390713,0.0,1.385882966956691
bare_runtime_ceiling,b8_t8_p1_s0,8,8,1,0,1,100000,none,none,7799.446878591458,0.0,7897.51,0.0,12.821422026026994,0.034,0.0,0.0,0.427813,0.0,1.2416409482803994
bare_runtime_ceiling,b32_t2_p1_s0,32,2,1,0,1,100000,none,none,27869.455692204683,0.0,29168.57,0.0,3.5881576269166544,0.018,0.0,0.0,0.056093,0.0,4.453835185997153
bare_runtime_ceiling,b32_t4_p1_s0,32,4,1,0,1,100000,none,none,28040.06659341811,0.0,29601.73,0.0,3.566325339023024,0.035,0.0,0.0,0.109533,0.0,5.275579795380219
bare_runtime_ceiling,b32_t8_p1_s0,32,8,1,0,1,100000,none,none,28104.53006057388,0.0,29609.05,0.0,3.5581452450715005,0.038,0.0,0.0,0.118018,0.0,5.081277818041046
bare_runtime_ceiling,b128_t2_p1_s0,128,2,1,0,1,100000,none,none,31447.71831970936,0.0,33100.57,0.0,3.1798809370957315,0.048,0.0,0.0,0.037896,0.0,4.993423975199334
bare_runtime_ceiling,b128_t4_p1_s0,128,4,1,0,1,100000,none,none,31661.5755486509,0.0,33386.89,0.0,3.158402519999072,0.05,0.0,0.0,0.039469,0.0,5.167628855587404
bare_runtime_ceiling,b128_t8_p1_s0,128,8,1,0,1,100000,none,none,31469.019368627865,0.0,33165.9,0.0,3.177728509064764,0.054,0.0,0.0,0.041971,0.0,5.116343595778536
bare_runtime_ceiling,b256_t2_p1_s0,256,2,1,0,1,100000,none,none,29910.732376407545,0.0,31439.57,0.0,3.3432815599953756,0.066,0.0,0.0,0.025667,0.0,4.8627839766986405
bare_runtime_ceiling,b256_t4_p1_s0,256,4,1,0,1,100000,none,none,30957.729631397124,0.0,32622.46,0.0,3.2302110390737653,0.081,0.0,0.0,0.031672,0.0,5.103011446615296
bare_runtime_ceiling,b256_t8_p1_s0,256,8,1,0,1,100000,none,none,31027.329740704034,0.0,32699.05,0.0,3.222965070977807,0.089,0.0,0.0,0.034728,0.0,5.112437378287103
bare_runtime_ceiling,b512_t2_p1_s0,512,2,1,0,1,100000,none,none,30487.982637698366,0.0,32089.93,0.0,3.279980876017362,0.11,0.0,0.0,0.021542,0.0,4.992068009133568
bare_runtime_ceiling,b512_t4_p1_s0,512,4,1,0,1,100000,none,none,31114.310752982394,0.0,32847.02,0.0,3.2139551730360836,0.129,0.0,0.0,0.025303,0.0,5.275094514648358
bare_runtime_ceiling,b512_t8_p1_s0,512,8,1,0,1,100000,none,none,30814.78338268331,0.0,32884.59,0.0,3.2451956178992987,0.116,0.0,0.0,0.022786,0.0,6.294154249829781
(no-gil-3.13) (base) ➜  ~/drava git:(main) ✗ 

```
- Cupy
```shell
(no-gil-3.13) (base) ➜  ~/drava git:(main) ✗ python experiments/sc5_bare_runtime_ceiling.py \
  --batches 8,32,128,256,512 \
  --thread-list 2,4,8 \
  --payload-bytes 1 \
  --gpu-backend cupy \
  --kernel-launches 1 \
  --num-frames 100000 \
  --runs 1
[sc5-bare-runtime] writing to /home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_142349
[sc5-bare-runtime] starting nats-server
[sc5-bare-runtime] nats ready (nats://127.0.0.1:4222)
[sc5-bare-runtime] batch=8 threads=2 payload=1 serialize=0 run=1
  done: pipeline_fps=7716.60 stage_fps=7835.21 cb_avg_ms=0.056
[sc5-bare-runtime] batch=32 threads=2 payload=1 serialize=0 run=1
  done: pipeline_fps=27694.61 stage_fps=29052.07 cb_avg_ms=0.061
[sc5-bare-runtime] batch=128 threads=2 payload=1 serialize=0 run=1
  done: pipeline_fps=30962.70 stage_fps=32632.86 cb_avg_ms=0.103
[sc5-bare-runtime] batch=256 threads=2 payload=1 serialize=0 run=1
  done: pipeline_fps=31114.44 stage_fps=32781.79 cb_avg_ms=0.150
[sc5-bare-runtime] batch=512 threads=2 payload=1 serialize=0 run=1
  done: pipeline_fps=31075.46 stage_fps=32865.60 cb_avg_ms=0.201
[sc5-bare-runtime] batch=8 threads=4 payload=1 serialize=0 run=1
  done: pipeline_fps=7802.18 stage_fps=7899.06 cb_avg_ms=0.118
[sc5-bare-runtime] batch=32 threads=4 payload=1 serialize=0 run=1
  done: pipeline_fps=28009.58 stage_fps=29440.79 cb_avg_ms=0.126
[sc5-bare-runtime] batch=128 threads=4 payload=1 serialize=0 run=1
  done: pipeline_fps=31476.41 stage_fps=33123.80 cb_avg_ms=0.135
[sc5-bare-runtime] batch=256 threads=4 payload=1 serialize=0 run=1
  done: pipeline_fps=30885.01 stage_fps=32618.18 cb_avg_ms=0.157
[sc5-bare-runtime] batch=512 threads=4 payload=1 serialize=0 run=1
  done: pipeline_fps=30797.22 stage_fps=32485.76 cb_avg_ms=0.221
[sc5-bare-runtime] batch=8 threads=8 payload=1 serialize=0 run=1
  done: pipeline_fps=7807.94 stage_fps=7903.24 cb_avg_ms=0.125
[sc5-bare-runtime] batch=32 threads=8 payload=1 serialize=0 run=1
  done: pipeline_fps=28092.12 stage_fps=29589.33 cb_avg_ms=0.129
[sc5-bare-runtime] batch=128 threads=8 payload=1 serialize=0 run=1
  done: pipeline_fps=31434.08 stage_fps=33105.56 cb_avg_ms=0.156
[sc5-bare-runtime] batch=256 threads=8 payload=1 serialize=0 run=1
  done: pipeline_fps=31071.98 stage_fps=32900.02 cb_avg_ms=0.185
[sc5-bare-runtime] batch=512 threads=8 payload=1 serialize=0 run=1
  done: pipeline_fps=31546.06 stage_fps=33226.60 cb_avg_ms=0.254

| Batch | Threads | Payload B | Ser | Frames | Pipeline FPS | Stage FPS | cb avg ms | Stage max ms | Backend |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 8 | 2 | 1 | 0 | 100000 | 7716.60 | 7835.21 | 0.056 | 0.000 | cupy |
| 32 | 2 | 1 | 0 | 100000 | 27694.61 | 29052.07 | 0.061 | 0.000 | cupy |
| 128 | 2 | 1 | 0 | 100000 | 30962.70 | 32632.86 | 0.103 | 0.000 | cupy |
| 256 | 2 | 1 | 0 | 100000 | 31114.44 | 32781.79 | 0.150 | 0.000 | cupy |
| 512 | 2 | 1 | 0 | 100000 | 31075.46 | 32865.60 | 0.201 | 0.000 | cupy |
| 8 | 4 | 1 | 0 | 100000 | 7802.18 | 7899.06 | 0.118 | 0.000 | cupy |
| 32 | 4 | 1 | 0 | 100000 | 28009.58 | 29440.79 | 0.126 | 0.000 | cupy |
| 128 | 4 | 1 | 0 | 100000 | 31476.41 | 33123.80 | 0.135 | 0.000 | cupy |
| 256 | 4 | 1 | 0 | 100000 | 30885.01 | 32618.18 | 0.157 | 0.000 | cupy |
| 512 | 4 | 1 | 0 | 100000 | 30797.22 | 32485.76 | 0.221 | 0.000 | cupy |
| 8 | 8 | 1 | 0 | 100000 | 7807.94 | 7903.24 | 0.125 | 0.000 | cupy |
| 32 | 8 | 1 | 0 | 100000 | 28092.12 | 29589.33 | 0.129 | 0.000 | cupy |
| 128 | 8 | 1 | 0 | 100000 | 31434.08 | 33105.56 | 0.156 | 0.000 | cupy |
| 256 | 8 | 1 | 0 | 100000 | 31071.98 | 32900.02 | 0.185 | 0.000 | cupy |
| 512 | 8 | 1 | 0 | 100000 | 31546.06 | 33226.60 | 0.254 | 0.000 | cupy |

Wrote raw summary: /home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_142349/sc5_bare_runtime_ceiling_summary.csv
Wrote aggregate summary: /home/ashovon/drava/experiments/results/sc5_bare_runtime_ceiling_20260605_142349/sc5_bare_runtime_ceiling_aggregate.csv
[sc5-bare-runtime] stopping nats-server
```