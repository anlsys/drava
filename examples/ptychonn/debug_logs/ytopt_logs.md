- New
```shell
 (no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(main) python tune_two_stage_ytopt.py \                                                                  
  --max-evals 64 \
  --initial-points 12 \
  --batch-size 1 \
  --batches 128,256,512,1024 \
  --stage1-threads 4,8,12,16 \
  --stage2-threads 2,4,8,12 \
  --stage1-callback-batches 128,256,512,1024 \
  --stage2-callback-batches 32,64,128,256 \
  --rates 0,1000,2000,4000 \
  --timeouts-ms 100,200,500 \
  --objective pipeline_e2e_s \
  --runs 1 \
  --num-frames 10000
| Rank | Eval | Batch | Threads S1/S2 | Callback S1/S2 | Rate Hz | Timeout ms | Publisher FPS | Stage1 FPS | Stage2 FPS | Pipeline E2E (s) | Summary |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 60 | 256 | 4/2 | 512/32 | 0.00 | 200 | 18787.27 | 4286.85 | 4275.20 | 2.86 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161857 |
| 2 | 52 | 256 | 4/2 | 1024/32 | 0.00 | 100 | 19148.14 | 4220.47 | 4262.15 | 2.89 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161543 |
| 3 | 58 | 256 | 4/4 | 512/32 | 0.00 | 100 | 20656.74 | 4196.85 | 4174.06 | 2.89 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161737 |
| 4 | 61 | 256 | 4/8 | 512/32 | 0.00 | 200 | 18082.77 | 4190.88 | 4169.31 | 2.91 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161917 |
| 5 | 55 | 256 | 4/8 | 1024/32 | 0.00 | 200 | 19042.30 | 4053.85 | 4098.64 | 2.99 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161641 |
| 6 | 46 | 256 | 4/4 | 1024/32 | 0.00 | 100 | 20231.90 | 4055.17 | 4088.19 | 2.99 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161230 |
| 7 | 56 | 256 | 4/8 | 512/32 | 0.00 | 100 | 19480.54 | 4005.57 | 3983.59 | 3.00 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161659 |
| 8 | 57 | 256 | 4/2 | 1024/32 | 0.00 | 200 | 19642.08 | 4020.82 | 4055.51 | 3.01 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161718 |
| 9 | 54 | 256 | 4/12 | 1024/32 | 0.00 | 100 | 18483.05 | 4103.03 | 4060.14 | 3.02 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161621 |
| 10 | 37 | 256 | 4/2 | 1024/32 | 0.00 | 500 | 19634.93 | 3992.67 | 4038.64 | 3.02 | /home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_160919 |

Sorted by `pipeline_e2e_s` (ascending).

Aggregate CSV written to: /home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/aggregate.csv
Recorded 28 failures in: /home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/failures.csv
ytopt tuner logs written to: /home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn git:(main) ✗ cat /home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/aggregate.csv
eval,batch,run,stage1_threads,stage2_threads,stage1_callback_batch,stage2_callback_batch,rate_hz,timeout_ms,total_frames,publisher_time_s,publisher_avg_fps,stage1_total_time_s,stage1_total_fps,stage2_total_time_s,stage2_total_fps,stage2_side,pipeline_e2e_s,ytopt_eval_elapsed_s,summary_path,run_log
60,256,1,4,2,512,32,0,200,10000,0.532,18787.27,2.332713,4286.85,2.339074,4275.196081868295,100,2.8589440799551085,17.04311438300647,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161857,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0060_b256_s1t4_s2t2_s1cb512_s2cb32_r0_to200.log
52,256,1,4,2,1024,32,0,100,10000,0.522,19148.14,2.369405,4220.47,2.346234,4262.1494701721995,100,2.8863410101039335,15.957789200008847,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161543,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0052_b256_s1t4_s2t2_s1cb1024_s2cb32_r0_to100.log
58,256,1,4,4,512,32,0,100,10000,0.484,20656.74,2.382739,4196.85,2.395748,4174.061712667609,100,2.8891674069454893,16.708005722030066,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161737,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0058_b256_s1t4_s2t4_s1cb512_s2cb32_r0_to100.log
61,256,1,4,8,512,32,0,200,10000,0.553,18082.77,2.386134,4190.88,2.398476,4169.3141811717105,100,2.9088783729821444,16.02004813705571,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161917,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0061_b256_s1t4_s2t8_s1cb512_s2cb32_r0_to200.log
55,256,1,4,8,1024,32,0,200,10000,0.525,19042.3,2.466789,4053.85,2.439831,4098.644537265081,100,2.9884473889833316,15.956687296973541,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161641,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0055_b256_s1t4_s2t8_s1cb1024_s2cb32_r0_to200.log
46,256,1,4,4,1024,32,0,100,10000,0.494,20231.9,2.465991,4055.17,2.446073,4088.1854302794723,100,2.9893240979872644,15.914985109004192,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161230,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0046_b256_s1t4_s2t4_s1cb1024_s2cb32_r0_to100.log
56,256,1,4,8,512,32,0,100,10000,0.513,19480.54,2.496521,4005.57,2.510301,3983.5860321132805,100,3.003338105045259,15.960332283983007,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161659,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0056_b256_s1t4_s2t8_s1cb512_s2cb32_r0_to100.log
57,256,1,4,2,1024,32,0,200,10000,0.509,19642.08,2.487054,4020.82,2.465784,4055.5052672902407,100,3.01069845398888,15.999983366928063,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161718,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0057_b256_s1t4_s2t2_s1cb1024_s2cb32_r0_to200.log
54,256,1,4,12,1024,32,0,100,10000,0.541,18483.05,2.437224,4103.03,2.462972,4060.1354786006495,100,3.0166964839445427,17.16182151599787,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161621,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0054_b256_s1t4_s2t12_s1cb1024_s2cb32_r0_to100.log
37,256,1,4,2,1024,32,0,500,10000,0.509,19634.93,2.50459,3992.67,2.476079,4038.6433550787356,100,3.0242441409500316,15.959129284950905,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_160919,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0037_b256_s1t4_s2t2_s1cb1024_s2cb32_r0_to500.log
51,256,1,4,8,1024,32,0,100,10000,0.528,18956.43,2.501566,3997.5,2.476758,4037.5361662302093,100,3.027423008927144,15.96148268703837,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161524,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0051_b256_s1t4_s2t8_s1cb1024_s2cb32_r0_to100.log
63,256,1,4,12,1024,32,0,200,10000,0.521,19209.87,2.535132,3944.57,2.505175,3991.737104194318,100,3.0629278040723875,17.246055267984048,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_162036,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0063_b256_s1t4_s2t12_s1cb1024_s2cb32_r0_to200.log
53,256,1,4,12,1024,256,0,100,10000,0.504,19854.56,2.556596,3911.45,1.889813,5291.528844388307,100,3.1429376039886847,16.161021440057084,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161602,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0053_b256_s1t4_s2t12_s1cb1024_s2cb256_r0_to100.log
45,128,1,12,2,1024,32,0,200,10000,0.493,20268.41,3.239703,3086.7,3.13212,3192.725693779293,100,3.7672127640107647,18.036420576972887,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161209,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0045_b128_s1t12_s2t2_s1cb1024_s2cb32_r0_to200.log
26,128,1,4,2,128,32,0,500,10000,0.506,19779.0,3.277797,3050.83,3.235083,3091.1107999392907,100,3.7909770749974996,16.763641651021317,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_160516,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0026_b128_s1t4_s2t2_s1cb128_s2cb32_r0_to500.log
50,128,1,4,2,256,32,0,200,10000,0.49,20421.79,3.302261,3028.23,3.228656,3097.2640008721896,100,3.830574536928907,18.549511202028953,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161503,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0050_b128_s1t4_s2t2_s1cb256_s2cb32_r0_to200.log
1,128,1,4,2,128,32,0,100,10000,0.542,18443.87,3.353378,2982.07,3.265366,3062.443842436039,100,3.868896487983875,18.03570506500546,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_154851,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0001_b128_s1t4_s2t2_s1cb128_s2cb32_r0_to100.log
31,128,1,4,2,256,32,0,500,10000,0.511,19577.84,3.459664,2890.45,3.391308,2948.7147731789623,100,3.962053010938689,16.960741497925483,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_160701,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0031_b128_s1t4_s2t2_s1cb256_s2cb32_r0_to500.log
35,128,1,4,4,256,32,0,500,10000,0.541,18467.54,3.469336,2882.4,3.382804,2956.127520246517,100,3.9738928880542517,17.62468097906094,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_160856,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0035_b128_s1t4_s2t4_s1cb256_s2cb32_r0_to500.log
40,128,1,4,2,1024,32,0,200,10000,0.484,20663.67,3.535157,2828.73,3.477109,2875.952407589178,100,4.061809330014512,18.9108666209504,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161019,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0040_b128_s1t4_s2t2_s1cb1024_s2cb32_r0_to200.log
44,128,1,4,4,1024,32,0,200,10000,0.513,19499.2,3.530134,2832.75,3.465317,2885.7388804545153,100,4.062623666017316,17.035388504038565,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161149,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0044_b128_s1t4_s2t4_s1cb1024_s2cb32_r0_to200.log
29,128,1,4,2,256,32,0,100,10000,0.55,18173.93,3.570705,2800.57,3.521283,2839.873989111355,100,4.079184470931068,18.673298163106665,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_160619,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0029_b128_s1t4_s2t2_s1cb256_s2cb32_r0_to100.log
41,128,1,4,8,1024,32,0,500,10000,0.518,19295.8,3.546928,2819.34,3.476467,2876.483510414452,100,4.096082156989723,16.95842540008016,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161041,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0041_b128_s1t4_s2t8_s1cb1024_s2cb32_r0_to500.log
23,128,1,4,2,512,32,0,500,10000,0.501,19965.42,3.565568,2804.6,3.518084,2842.456291549605,100,4.1613757309969515,19.57653781794943,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_160340,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0023_b128_s1t4_s2t2_s1cb512_s2cb32_r0_to500.log
38,128,1,4,2,1024,32,0,100,10000,0.516,19382.13,3.607745,2771.81,3.55328,2814.301152737752,100,4.172053535003215,17.209195047034882,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_160938,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0038_b128_s1t4_s2t2_s1cb1024_s2cb32_r0_to100.log
30,128,1,4,2,1024,32,0,500,10000,0.54,18526.3,3.657104,2734.4,3.600199,2777.6242368824614,100,4.180842568981461,17.36119125201367,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_160641,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0030_b128_s1t4_s2t2_s1cb1024_s2cb32_r0_to500.log
39,128,1,4,4,1024,32,0,500,10000,0.522,19167.24,3.673618,2722.11,3.611155,2769.19711283509,100,4.196803783997893,18.38816190196667,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_160958,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0039_b128_s1t4_s2t4_s1cb1024_s2cb32_r0_to500.log
32,128,1,4,2,1024,128,0,500,10000,0.489,20431.89,3.673579,2722.14,3.219397,3106.171745826936,100,4.236448582960293,18.20339038397651,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_160721,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0032_b128_s1t4_s2t2_s1cb1024_s2cb128_r0_to500.log
27,128,1,4,2,1024,64,0,500,10000,0.51,19590.52,3.784958,2642.04,3.577237,2795.453586105701,100,4.317941660992801,17.36280987400096,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_160535,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0027_b128_s1t4_s2t2_s1cb1024_s2cb64_r0_to500.log
42,128,1,4,12,1024,32,0,200,10000,0.558,17922.21,3.731399,2679.96,3.706151,2698.217099087436,100,4.33016505104024,18.2389152739197,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161101,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0042_b128_s1t4_s2t12_s1cb1024_s2cb32_r0_to200.log
14,1024,1,4,2,256,32,0,500,10000,0.5,19982.72,2.318084,4313.91,5.692682,1756.6412457256529,100,6.219944415031932,19.366404059925117,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_155700,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0014_b1024_s1t4_s2t2_s1cb256_s2cb32_r0_to500.log
28,128,1,16,2,128,64,0,500,10000,0.516,19394.81,3.192662,3132.18,7.274079,1374.744486552868,100,8.23738253803458,21.37226324400399,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_160555,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0028_b128_s1t16_s2t2_s1cb128_s2cb64_r0_to500.log
43,128,1,4,2,1024,32,2000,500,10000,5.003,1998.94,6.088669,1642.4,9.840213,1016.2381647633034,100,10.975606162915938,24.418270759051666,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_161122,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0043_b128_s1t4_s2t2_s1cb1024_s2cb32_r2000_to500.log
17,256,1,8,4,1024,32,1000,100,10000,10.002,999.79,10.391326,962.34,13.682102,730.8818484177358,100,15.225378728006035,29.528162344940938,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_155928,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0017_b256_s1t8_s2t4_s1cb1024_s2cb32_r1000_to100.log
5,1024,1,16,4,512,64,1000,200,10000,10.002,999.82,10.635553,940.24,15.138914,660.5493630520657,100,16.629623721004464,31.56503859499935,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_155049,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0005_b1024_s1t16_s2t4_s1cb512_s2cb64_r1000_to200.log
2,128,1,12,12,128,32,1000,200,10000,10.003,999.74,11.067881,903.52,15.868135,630.1937814368229,100,16.971205886104144,30.86677455494646,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260605_154909,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260605_154837/eval0002_b128_s1t12_s2t12_s1cb128_s2cb32_r1000_to200.log
```
- Old
```shell
(no-gil-3.13) (base) ➜  ~/drava/examples/ptychonn/bench_logs_two_stages/20260512_185724 git:(main) ✗ cat /home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/aggregate.csv
eval,batch,run,stage1_threads,stage2_threads,stage1_callback_batch,stage2_callback_batch,rate_hz,timeout_ms,total_frames,publisher_time_s,publisher_avg_fps,stage1_total_time_s,stage1_total_fps,stage2_total_time_s,stage2_total_fps,stage2_side,pipeline_e2e_s,ytopt_eval_elapsed_s,summary_path,run_log
51,128,1,4,8,128,32,0,500,10000,0.591,16907.76,3.359366,2976.75,3.315079,3016.5193649985417,100,3.824563867994584,16.609571745968424,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185314,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0051_b128_s1t4_s2t8_s1cb128_s2cb32_r0_to500.log
1,128,1,4,2,128,32,0,100,10000,0.589,16975.0,3.345713,2988.9,3.272022,3056.214169709128,100,3.8461784070241265,17.999599755974486,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_183737,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0001_b128_s1t4_s2t2_s1cb128_s2cb32_r0_to100.log
55,128,1,4,8,512,32,0,500,10000,0.614,16285.26,3.361192,2975.14,3.244116,3082.5038315522625,100,3.8623449580045417,16.660598707967438,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185423,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0055_b128_s1t4_s2t8_s1cb512_s2cb32_r0_to500.log
41,128,1,4,8,1024,128,0,500,10000,0.593,16856.41,3.363904,2972.74,2.902109,3445.769955573688,100,3.867989097023383,16.809181504009757,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185002,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0041_b128_s1t4_s2t8_s1cb1024_s2cb128_r0_to500.log
19,128,1,4,2,128,64,0,100,10000,0.587,17044.59,3.36637,2970.56,3.147559,3177.065147944804,100,3.88242405699566,16.82068371301284,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184258,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0019_b128_s1t4_s2t2_s1cb128_s2cb64_r0_to100.log
61,128,1,4,4,128,32,0,500,10000,0.606,16489.85,3.391624,2948.44,3.317142,3014.6433285038747,100,3.8840976010542363,16.61027218599338,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185624,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0061_b128_s1t4_s2t4_s1cb128_s2cb32_r0_to500.log
58,128,1,4,12,128,32,0,500,10000,0.6,16673.5,3.398601,2942.39,3.314598,3016.957109127562,100,3.888737336965278,16.809106908971444,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185523,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0058_b128_s1t4_s2t12_s1cb128_s2cb32_r0_to500.log
33,128,1,4,8,256,128,0,100,10000,0.588,17012.45,3.374826,2963.12,2.920793,3423.7277342146463,100,3.8887680689804256,16.89374734798912,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184651,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0033_b128_s1t4_s2t8_s1cb256_s2cb128_r0_to100.log
53,128,1,4,8,128,64,0,500,10000,0.616,16221.67,3.400146,2941.05,3.198236,3126.7236063880214,100,3.903227041999344,16.66100257396465,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185343,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0053_b128_s1t4_s2t8_s1cb128_s2cb64_r0_to500.log
40,128,1,4,4,128,128,0,500,10000,0.605,16535.95,3.344294,2990.17,2.937809,3403.8972581267194,100,3.9461765000014566,17.263174235005863,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184942,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0040_b128_s1t4_s2t4_s1cb128_s2cb128_r0_to500.log
62,128,1,4,4,256,32,0,500,10000,0.642,15586.58,3.453127,2895.93,3.404868,2936.971418568943,100,3.9581638560048304,17.75782361504389,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185644,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0062_b128_s1t4_s2t4_s1cb256_s2cb32_r0_to500.log
50,128,1,4,8,256,32,0,500,10000,0.6,16659.25,3.454286,2894.95,3.402267,2939.2167046266504,100,3.961114193953108,16.808176504040603,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185255,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0050_b128_s1t4_s2t8_s1cb256_s2cb32_r0_to500.log
60,128,1,4,12,1024,32,0,500,10000,0.635,15750.15,3.483202,2870.92,3.410706,2931.9442954039428,100,3.972356146958191,16.909359860001132,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185604,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0060_b128_s1t4_s2t12_s1cb1024_s2cb32_r0_to500.log
59,128,1,4,12,512,32,0,500,10000,0.626,15973.55,3.473852,2878.65,3.402157,2939.311736642371,100,3.9768539830110967,18.568317188997753,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185543,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0059_b128_s1t4_s2t12_s1cb512_s2cb32_r0_to500.log
34,128,1,4,8,128,128,0,500,10000,0.63,15861.37,3.477822,2875.36,3.024769,3306.037585018889,100,3.982354588981252,17.720567891024984,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184711,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0034_b128_s1t4_s2t8_s1cb128_s2cb128_r0_to500.log
16,128,1,4,12,128,64,0,100,10000,0.623,16053.06,3.533491,2830.06,3.321889,3010.3353844755197,100,4.0260951070231386,16.848884181992617,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184154,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0016_b128_s1t4_s2t12_s1cb128_s2cb64_r0_to100.log
54,128,1,4,8,256,32,0,100,10000,0.63,15880.84,3.545913,2820.15,3.480698,2872.986969854897,100,4.052536885021254,17.289593271969352,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185403,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0054_b128_s1t4_s2t8_s1cb256_s2cb32_r0_to100.log
14,128,1,4,4,128,128,0,100,10000,0.586,17069.9,3.507905,2850.7,2.701477,3701.6787483291546,100,4.0565587999881245,17.65985247900244,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184126,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0014_b128_s1t4_s2t4_s1cb128_s2cb128_r0_to100.log
30,128,1,4,12,128,128,0,500,10000,0.613,16322.41,3.488441,2866.61,3.099447,3226.3819965303487,100,4.0605374409933574,16.86181399197085,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184626,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0030_b128_s1t4_s2t12_s1cb128_s2cb128_r0_to500.log
43,128,1,4,8,256,128,0,500,10000,0.614,16294.92,3.559994,2808.99,3.080067,3246.6826208650655,100,4.0781670800060965,17.459546809026506,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185043,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0043_b128_s1t4_s2t8_s1cb256_s2cb128_r0_to500.log
57,128,1,4,8,512,32,0,100,10000,0.613,16314.17,3.565188,2804.9,3.429264,2916.0776189876315,100,4.094069804996252,17.259807228983846,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185503,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0057_b128_s1t4_s2t8_s1cb512_s2cb32_r0_to100.log
35,128,1,4,8,128,128,0,200,10000,0.608,16455.38,3.595465,2781.28,3.092442,3233.690397427017,100,4.112025064008776,16.866328835953027,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184731,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0035_b128_s1t4_s2t8_s1cb128_s2cb128_r0_to200.log
48,128,1,4,4,128,32,0,200,10000,0.604,16564.51,3.589644,2785.79,3.49807,2858.719236607615,100,4.114774435991421,17.263481511035934,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185213,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0048_b128_s1t4_s2t4_s1cb128_s2cb32_r0_to200.log
28,128,1,4,12,128,128,0,100,10000,0.604,16561.57,3.408123,2934.17,3.156993,3167.5711666132934,100,4.1170480659930035,17.419198617048096,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184545,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0028_b128_s1t4_s2t12_s1cb128_s2cb128_r0_to100.log
44,128,1,4,8,256,128,0,200,10000,0.612,16351.55,3.546087,2820.01,3.116701,3208.5208045301747,100,4.1286506010219455,17.062802478962112,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185103,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0044_b128_s1t4_s2t8_s1cb256_s2cb128_r0_to200.log
17,128,1,4,2,128,128,0,100,10000,0.6,16670.17,3.631846,2753.42,3.091386,3234.7950078055605,100,4.14427245099796,17.626536960015073,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184214,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0017_b128_s1t4_s2t2_s1cb128_s2cb128_r0_to100.log
63,128,1,4,12,128,32,0,100,10000,0.622,16076.84,3.645596,2743.04,3.586399,2788.3121760852596,100,4.155246936017647,16.859144561982248,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185704,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0063_b128_s1t4_s2t12_s1cb128_s2cb32_r0_to100.log
29,128,1,4,8,128,128,0,100,10000,0.598,16714.57,3.345265,2989.3,3.196978,3127.9539615224126,100,4.161794056999497,18.29978561302414,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184605,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0029_b128_s1t4_s2t8_s1cb128_s2cb128_r0_to100.log
42,128,1,4,8,512,128,0,500,10000,0.594,16826.88,3.613066,2767.73,3.092867,3233.2460464675655,100,4.174843148037326,18.791855291987304,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185022,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0042_b128_s1t4_s2t8_s1cb512_s2cb128_r0_to500.log
36,128,1,4,12,1024,128,0,100,10000,0.615,16255.2,3.291322,3038.29,3.165237,3159.321087172935,100,4.177336590015329,17.674921659985557,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184751,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0036_b128_s1t4_s2t12_s1cb1024_s2cb128_r0_to100.log
23,128,1,4,2,128,32,0,500,10000,0.578,17314.56,3.687926,2711.55,3.577126,2795.540330421685,100,4.184953176998533,17.217186265974306,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184409,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0023_b128_s1t4_s2t2_s1cb128_s2cb32_r0_to500.log
49,128,1,4,8,1024,128,0,100,10000,0.614,16284.97,3.398372,2942.59,3.182447,3142.2361472162775,100,4.191184098017402,18.33745342999464,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185233,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0049_b128_s1t4_s2t8_s1cb1024_s2cb128_r0_to100.log
21,128,1,4,2,128,64,0,500,10000,0.602,16619.28,3.675058,2721.05,3.434167,2911.91430119735,100,4.194192634022329,17.710084078949876,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184340,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0021_b128_s1t4_s2t2_s1cb128_s2cb64_r0_to500.log
47,128,1,4,12,512,128,0,500,10000,0.621,16093.5,3.401091,2940.23,3.240066,3086.356882853621,100,4.240208250004798,17.261989270045888,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185153,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0047_b128_s1t4_s2t12_s1cb512_s2cb128_r0_to500.log
38,128,1,4,12,256,128,0,100,10000,0.629,15909.89,3.640199,2747.1,3.297307,3032.777960923869,100,4.286197346984409,18.55549375800183,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184912,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0038_b128_s1t4_s2t12_s1cb256_s2cb128_r0_to100.log
56,128,1,4,8,128,256,0,500,10000,0.626,15966.05,3.467011,2884.33,2.000951,4997.623629963952,100,4.323388114979025,18.10794097802136,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185442,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0056_b128_s1t4_s2t8_s1cb128_s2cb256_r0_to500.log
27,128,1,4,2,128,256,0,100,10000,0.584,17124.57,3.340896,2993.21,2.356594,4243.4123145522735,100,4.59568098798627,17.418068605009466,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184524,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0027_b128_s1t4_s2t2_s1cb128_s2cb256_r0_to100.log
45,128,1,4,8,128,256,0,200,10000,0.612,16349.82,3.322695,3009.61,2.593661,3855.55398334632,100,4.816182134964038,19.108045558969025,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_185123,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0045_b128_s1t4_s2t8_s1cb128_s2cb256_r0_to200.log
18,128,1,8,2,128,128,0,100,10000,0.59,16937.47,2.673384,3740.58,5.924545,1687.8933318929976,100,6.876672217040323,20.40331183496164,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184234,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0018_b128_s1t8_s2t2_s1cb128_s2cb128_r0_to100.log
20,128,1,8,2,128,64,0,100,10000,0.604,16553.22,2.650299,3773.16,6.390391,1564.8494747817465,100,7.080752603011206,20.414492045994848,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184317,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0020_b128_s1t8_s2t2_s1cb128_s2cb64_r0_to100.log
11,256,1,12,8,512,256,0,200,10000,0.589,16971.46,2.317384,4315.21,6.66552,1500.2580443836341,100,7.971825062006246,20.912134575017262,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184034,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0011_b256_s1t12_s2t8_s1cb512_s2cb256_r0_to200.log
24,128,1,16,2,128,64,0,100,10000,0.619,16142.86,2.840375,3520.66,7.662029,1305.1373206757635,100,8.531803549034521,21.875968751031905,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184429,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0024_b128_s1t16_s2t2_s1cb128_s2cb64_r0_to100.log
4,1024,1,4,4,256,256,0,100,10000,0.596,16791.73,1.810324,5523.87,9.915488,1008.523231534343,100,10.815060070017353,23.8047230860102,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_183832,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0004_b1024_s1t4_s2t4_s1cb256_s2cb256_r0_to100.log
13,1024,1,4,4,1024,128,0,500,10000,0.614,16283.97,1.826298,5475.56,10.096222,990.4695043353842,100,10.868743151018862,24.114313669037074,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184059,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0013_b1024_s1t4_s2t4_s1cb1024_s2cb128_r0_to500.log
26,512,1,4,2,128,32,0,100,10000,0.589,16986.26,1.824743,5480.22,11.498156,869.7046726449006,100,12.119642429985106,25.30938791699009,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184456,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0026_b512_s1t4_s2t2_s1cb128_s2cb32_r0_to100.log
8,1024,1,8,8,1024,256,2000,100,10000,5.002,1999.23,5.713551,1750.23,12.203014,819.4696818343403,100,14.810041356016882,29.617841412022244,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_183905,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0008_b1024_s1t8_s2t8_s1cb1024_s2cb256_r2000_to100.log
10,128,1,16,12,512,256,4000,200,10000,2.502,3996.09,3.598992,2778.56,14.016837,713.4277155395329,100,15.466186920995824,29.117831040988676,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_184005,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0010_b128_s1t16_s2t12_s1cb512_s2cb256_r4000_to200.log
2,128,1,12,12,128,32,1000,200,10000,10.003,999.74,11.015227,907.83,15.713861,636.3808360020494,100,16.599323981965426,29.829656438028906,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_183755,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0002_b128_s1t12_s2t12_s1cb128_s2cb32_r1000_to200.log
9,128,1,12,8,128,64,1000,200,10000,10.002,999.82,11.005059,908.67,15.776246,633.8643553098754,100,17.178652697999496,30.233319191960618,/home/ashovon/drava/examples/ptychonn/bench_logs_two_stages/20260512_183935,/home/ashovon/drava/examples/ptychonn/tune_logs_two_stages_ytopt/20260512_183723/eval0009_b128_s1t12_s2t8_s1cb128_s2cb64_r1000_to200.log

```

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