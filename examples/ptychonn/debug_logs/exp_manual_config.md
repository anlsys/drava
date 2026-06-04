```shell
python3 tune_two_stage.py \
  --batches 64,128,256,512 \
  --stage1-threads 4,8 \
  --stage2-threads 4,8 \
  --stage1-callback-batches 64,128,256 \
  --stage2-callback-batches 32,64 \
  --rates 0 \
  --runs 1 \
  --timeout-ms 200 \
  --num-frames 10000 \
  --objective pipeline_e2e_s \
  --top-k 10 \
  --keep-going
```