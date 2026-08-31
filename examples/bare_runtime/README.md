# Bare Runtime Example

This example is a synthetic Drava application for runtime ceiling experiments.
It preserves the normal publisher, JetStream, Drava listen/callback, EOS, and
metrics cycle, but it does not load datasets or generate per-frame data.

The publisher reuses one cached payload for every message. The stage callback
counts payloads, optionally launches blank GPU work, and optionally republishes
cached output payloads.

Run the SC driver from the repository root:

```bash
python experiments/sc5_bare_runtime_ceiling.py \
    --batches 1,8,32,128,256,512 \
    --thread-list 1,2,4,8 \
    --payload-bytes 1 \
    --gpu-backend auto \
    --kernel-launches 1 \
    --num-frames 100000 \
    --runs 3
```

Paper artifacts:

- Experiment index: [../../docs/paper.md](../../docs/paper.md)
- Preserved run log: [../../experiments/logs/sc5_bare_runtime_ceiling.md](../../experiments/logs/sc5_bare_runtime_ceiling.md)
- Figure package: [../../experiments/figures/sc5_bare_runtime_ceiling](../../experiments/figures/sc5_bare_runtime_ceiling)

Useful callback modes:

* `DRAVA_BARE_GPU_BACKEND=auto|cupy|torch|none`
* `DRAVA_BARE_KERNEL_LAUNCHES=0` for the pure runtime/Python callback path
* `DRAVA_BARE_PUBLISH_MODE=none|one_per_callback|one_per_frame`
