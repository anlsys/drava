- [Debug] logs
```shell
# with 20 threads
[0.057084] [TID=28656] [LOGGER] [INFO] JetStream ready: url=nats://127.0.0.1:4222 stream=FRAMES subject=frames.raw durable=drava_consumer
First frame arrived at:106577.492385366
[frame]=256 / 3600, [current] idx=3478, pred time=315.15 ms, frame rate=40.02
[frame]=512 / 3600, [current] idx=3228, pred time=294.71 ms, frame rate=44.80


python publisher_jetstream.py
X_test shape: (3600, 64, 64, 1)
First frame sent at:106577.489145601
Published idx=255/3599 seq=52474 win_fps=999.87 avg_fps=999.87
# Without inference task
JetStream ready: url=nats://127.0.0.1:4222 stream=FRAMES subject=frames.raw durable=drava_consumer
First frame arrived at:107390.763745737
[frame]=256 / 3600, [current] idx=255, pred time=0.00 ms, frame rate=1016.15
[frame]=512 / 3600, [current] idx=511, pred time=0.00 ms, frame rate=996.01
[frame]=768 / 3600, [current] idx=767, pred time=0.00 ms, frame rate=1004.66
[frame]=1024 / 3600, [current] idx=1023, pred time=0.00 ms, frame rate=1003.79
[frame]=1280 / 3600, [current] idx=1279, pred time=0.00 ms, frame rate=1003.06
[frame]=1536 / 3600, [current] idx=1534, pred time=0.00 ms, frame rate=1002.48
[frame]=1792 / 3600, [current] idx=1791, pred time=0.00 ms, frame rate=1002.10
[frame]=2048 / 3600, [current] idx=2047, pred time=0.00 ms, frame rate=1001.97
[frame]=2304 / 3600, [current] idx=2303, pred time=0.00 ms, frame rate=1001.71
[frame]=2560 / 3600, [current] idx=2559, pred time=0.00 ms, frame rate=1001.45
[frame]=2816 / 3600, [current] idx=2815, pred time=0.00 ms, frame rate=1001.44
[frame]=3072 / 3600, [current] idx=3071, pred time=0.00 ms, frame rate=1001.15
[frame]=3328 / 3600, [current] idx=3327, pred time=0.00 ms, frame rate=1001.01
[frame]=3584 / 3600, [current] idx=3583, pred time=0.00 ms, frame rate=1001.02


python publisher_jetstream.py
X_test shape: (3600, 64, 64, 1)
First frame sent at:107390.759942517
Published idx=255/3599 seq=59674 win_fps=1001.86 avg_fps=1001.86
Published idx=511/3599 seq=59930 win_fps=977.90 avg_fps=989.73
Published idx=767/3599 seq=60186 win_fps=1020.59 avg_fps=999.81
Published idx=1023/3599 seq=60442 win_fps=1002.44 avg_fps=1000.47
Published idx=1279/3599 seq=60698 win_fps=998.87 avg_fps=1000.15
Published idx=1535/3599 seq=60954 win_fps=1001.20 avg_fps=1000.32
Published idx=1791/3599 seq=61210 win_fps=998.72 avg_fps=1000.09
Published idx=2047/3599 seq=61466 win_fps=1001.96 avg_fps=1000.32
Published idx=2303/3599 seq=61722 win_fps=998.74 avg_fps=1000.15
Published idx=2559/3599 seq=61978 win_fps=1000.76 avg_fps=1000.21
Published idx=2815/3599 seq=62234 win_fps=999.84 avg_fps=1000.18
Published idx=3071/3599 seq=62490 win_fps=999.16 avg_fps=1000.09
Published idx=3327/3599 seq=62746 win_fps=997.98 avg_fps=999.93
Published idx=3583/3599 seq=63002 win_fps=1001.18 avg_fps=1000.02
Published idx=3599/3599 seq=63018 win_fps=978.98 avg_fps=999.92
Done: published 3600 frames in 3.601s (avg_fps=999.80)



```

- Using 4 and 15 threads (GPU usage 2-3%):
```shell
[15.180893] [TID=52162] [LOGGER] [INFO] [frame]=70/3600 [idx]=3599 step_ms=87.39 avg_fps=17.95
[21.556449] [TID=52160] [LOGGER] [INFO] [frame]=256/3600 [idx]=3326 step_ms=85.30 avg_fps=24.91
[30.632510] [TID=52162] [LOGGER] [INFO] [frame]=512/3600 [idx]=2992 step_ms=80.47 avg_fps=26.46
[39.835350] [TID=52160] [LOGGER] [INFO] [frame]=768/3600 [idx]=2571 step_ms=70.14 avg_fps=26.90
[49.042317] [TID=52160] [LOGGER] [INFO] [frame]=1024/3600 [idx]=2205 step_ms=79.81 avg_fps=27.12
[58.381553] [TID=52162] [LOGGER] [INFO] [frame]=1280/3600 [idx]=1993 step_ms=259.94 avg_fps=27.18
[67.741674] [TID=52162] [LOGGER] [INFO] [frame]=1536/3600 [idx]=1675 step_ms=100.90 avg_fps=27.20
[77.230222] [TID=52160] [LOGGER] [INFO] [frame]=1792/3600 [idx]=1033 step_ms=84.90 avg_fps=27.17
[86.258896] [TID=52160] [LOGGER] [INFO] [frame]=2048/3600 [idx]=664 step_ms=91.85 avg_fps=27.31
[95.251879] [TID=52160] [LOGGER] [INFO] [frame]=2304/3600 [idx]=316 step_ms=87.76 avg_fps=27.44
[104.617629] [TID=52161] [LOGGER] [INFO] [frame]=2560/3600 [idx]=305 step_ms=91.65 avg_fps=27.43
[113.911495] [TID=52160] [LOGGER] [INFO] [frame]=2816/3600 [idx]=3180 step_ms=100.07 avg_fps=27.44
[123.513180] [TID=52161] [LOGGER] [INFO] [frame]=3072/3600 [idx]=2124 step_ms=89.03 avg_fps=27.37
[132.545545] [TID=52160] [LOGGER] [INFO] [frame]=3328/3600 [idx]=1107 step_ms=73.60 avg_fps=27.44
[142.078688] [TID=52161] [LOGGER] [INFO] [frame]=3584/3600 [idx]=71 step_ms=99.94 avg_fps=27.40


# 15 threads:
[10.330153] [TID=25489] [LOGGER] [INFO] [frame]=104/3600 [idx]=3599 step_ms=275.96 avg_fps=26.12
[13.808946] [TID=25485] [LOGGER] [INFO] [frame]=256/3600 [idx]=3462 step_ms=409.83 avg_fps=34.32
[19.687870] [TID=25482] [LOGGER] [INFO] [frame]=512/3600 [idx]=3123 step_ms=278.66 avg_fps=38.38
[25.727089] [TID=25487] [LOGGER] [INFO] [frame]=768/3600 [idx]=2894 step_ms=318.40 avg_fps=39.63
[31.617312] [TID=25490] [LOGGER] [INFO] [frame]=1024/3600 [idx]=2612 step_ms=289.64 avg_fps=40.52
[37.801167] [TID=25493] [LOGGER] [INFO] [frame]=1280/3600 [idx]=2273 step_ms=270.57 avg_fps=40.70
[43.461586] [TID=25491] [LOGGER] [INFO] [frame]=1536/3600 [idx]=2240 step_ms=328.93 avg_fps=41.39
[49.435470] [TID=25488] [LOGGER] [INFO] [frame]=1792/3600 [idx]=2011 step_ms=315.95 avg_fps=41.59
[55.505647] [TID=25482] [LOGGER] [INFO] [frame]=2048/3600 [idx]=1477 step_ms=481.30 avg_fps=41.66
[61.287420] [TID=25486] [LOGGER] [INFO] [frame]=2304/3600 [idx]=947 step_ms=362.02 avg_fps=41.94
[67.536645] [TID=25496] [LOGGER] [INFO] [frame]=2560/3600 [idx]=579 step_ms=627.15 avg_fps=41.84
[73.200711] [TID=25488] [LOGGER] [INFO] [frame]=2816/3600 [idx]=1123 step_ms=257.57 avg_fps=42.12
[79.194445] [TID=25489] [LOGGER] [INFO] [frame]=3072/3600 [idx]=507 step_ms=293.11 avg_fps=42.17
[85.034684] [TID=25484] [LOGGER] [INFO] [frame]=3328/3600 [idx]=2934 step_ms=494.03 avg_fps=42.29
[91.251437] [TID=25491] [LOGGER] [INFO] [frame]=3584/3600 [idx]=92 step_ms=363.99 avg_fps=42.21
[217.176323] [TID=25480] [LOGGER] [FATAL] Fetch error: Limit reached
```
- Batch
```shell
[44.763579] [TID=18130] [LOGGER] [INFO] [batch] reason=full bsz=32 last_idx=1693 batch_ms=98.11 per_frame_ms=3.07 avg_fps=95.92
[45.074032] [TID=18131] [LOGGER] [INFO] [batch] reason=full bsz=32 last_idx=1322 batch_ms=77.27 per_frame_ms=2.41 avg_fps=172.85
[45.512131] [TID=18130] [LOGGER] [INFO] [batch] reason=full bsz=32 last_idx=2568 batch_ms=289.17 per_frame_ms=9.04 avg_fps=225.60
[45.716585] [TID=18131] [LOGGER] [INFO] [batch] reason=full bsz=33 last_idx=3599 batch_ms=91.84 per_frame_ms=2.78 avg_fps=283.82
[45.772934] [TID=18132] [LOGGER] [INFO] [batch] reason=job_end bsz=1 last_idx=1150 batch_ms=73.70 per_frame_ms=73.70 avg_fps=288.45
[46.062549] [TID=18131] [LOGGER] [INFO] [batch] reason=full bsz=32 last_idx=2440 batch_ms=71.59 per_frame_ms=2.24 avg_fps=323.85
[46.278698] [TID=18130] [LOGGER] [INFO] [batch] reason=full bsz=32 last_idx=2132 batch_ms=85.73 per_frame_ms=2.68 avg_fps=368.30
[46.782187] [TID=18131] [LOGGER] [INFO] [batch] reason=full bsz=32 last_idx=350 batch_ms=306.53 per_frame_ms=9.58 avg_fps=383.57
[46.998788] [TID=18132] [LOGGER] [INFO] [batch] reason=full bsz=33 last_idx=79 batch_ms=106.55 per_frame_ms=3.23 avg_fps=419.23
[47.262487] [TID=18132] [LOGGER] [INFO] [batch] reason=full bsz=32 last_idx=1015 batch_ms=75.91 per_frame_ms=2.37 avg_fps=447.38
[47.472880] [TID=18131] [LOGGER] [INFO] [batch] reason=full bsz=32 last_idx=302 batch_ms=84.51 per_frame_ms=2.64 avg_fps=477.48
[47.678325] [TID=18130] [LOGGER] [INFO] [batch] reason=full bsz=32 last_idx=3254 batch_ms=74.60 per_frame_ms=2.33 avg_fps=505.76
[48.099841] [TID=18132] [LOGGER] [INFO] [batch] reason=full bsz=32 last_idx=2546 batch_ms=75.25 per_frame_ms=2.35 avg_fps=512.89
[48.288757] [TID=18131] [LOGGER] [INFO] [batch] reason=full bsz=32 last_idx=1534 batch_ms=70.58 per_frame_ms=2.21 avg_fps=538.57
[48.521262] [TID=18130] [LOGGER] [INFO] [batch] reason=full bsz=32 last_idx=486 batch_ms=78.12 per_frame_ms=2.44 avg_fps=558.92
```