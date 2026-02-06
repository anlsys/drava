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

