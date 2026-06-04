# Drava Runtime Characterization Experiments

## SC direct PtychoNN experiments

The SC paper evaluation should use the direct PtychoNN drivers below.  These
scripts do not import `_common.py`, do not parse `[drava-metrics]`, and do not
reconstruct latency components.  They use only the values already produced by
`examples/ptychonn/benchmark_two_stages.py` in `summary.csv`: end-to-end
pipeline latency, Stage 1 throughput, Stage 2 throughput, publisher throughput,
and per-stage elapsed time.

```bash
# 1. Callback batching with fixed TensorFlow inference batch.
python experiments/sc1_ptychonn_callback_batching.py \
    --callback-batches 128,256,512 --infer-batch 128 --runs 1

# 2. TensorFlow model.predict batching with fixed Drava callback batch.
python experiments/sc2_ptychonn_inference_batching.py \
    --infer-batches 64,128,256,512 --stage1-callback-batch 512 --runs 1

# 3. Stage 1 / Stage 2 thread scaling with batching fixed.
python experiments/sc3_ptychonn_thread_scaling.py \
    --stage1-threads-list 1,2,4,8 --stage2-threads-list 1,2,4,8 --runs 1
```

By default, the Stage 2 callback batch is frame-equivalent to Stage 1:
Stage 1 publishes prediction messages in 16-frame chunks, so a Stage 1
callback batch of `C` raw frames maps to `ceil(C/16)` Stage 2 prediction
messages.  To override this policy, pass `--stage2-callback-batch`.

Optional plotting:

```bash
python experiments/plot_sc_ptychonn_results.py --kind callback \
    --csv experiments/results/<run>/sc1_callback_batching_summary.csv
python experiments/plot_sc_ptychonn_results.py --kind inference \
    --csv experiments/results/<run>/sc2_inference_batching_summary.csv
python experiments/plot_sc_ptychonn_results.py --kind threads \
    --csv experiments/results/<run>/sc3_thread_scaling_summary.csv
```

## Legacy decomposition experiments

This directory contains five experiment drivers used in the Drava paper to
characterize runtime mechanisms (rather than tune workloads). Each driver
sweeps one runtime axis, captures `[drava-metrics]` lines from the existing
benchmark wrappers in `examples/`, and writes a CSV summary with a consistent
latency decomposition.

## Latency decomposition

Every experiment uses the same per-stage decomposition:

```
end_to_end_s = transport_lumped_s + microbatching_wait_s
             + dispatch_overhead_s + callback_compute_s + publish_s
```

Components are derived from existing runtime counters as follows:

| Component              | Source                                                    |
|------------------------|-----------------------------------------------------------|
| `callback_compute_s`   | `compute_total_s`                                         |
| `publish_s`            | `publish_total_s`                                         |
| `microbatching_wait_s` | `max(0, cb_total_s - compute_total_s - publish_total_s)`  |
| `dispatch_overhead_s`  | `max(0, stage_total_s - cb_total_s)`                      |
| `transport_lumped_s`   | `max(0, end_to_end_s - stage_total_s)`                    |

## Experiments

| # | File                              | Axis                                | Workload(s)             |
|---|-----------------------------------|-------------------------------------|-------------------------|
| 1 | `exp1_runtime_overhead.py`        | callback batch size                 | PtychoNN, TomoGAN       |
| 2 | `exp2_microbatching.py`           | publisher rate x fetch_timeout_ms   | PtychoNN                |
| 3 | `exp3_dispatch_mode.py`           | serialized vs parallel x threads    | PtychoNN, TomoGAN       |
| 4 | `exp4_transport.py`               | sockets vs nats x batch             | TomoGAN                 |
| 5 | `exp5_instrumentation_overhead.py`| full vs counters_only vs disabled   | PtychoNN                |

## Required runtime / app changes already applied

* `examples/ptychonn/app.py`, `examples/ptychonn/app_stage2.py`,
  `examples/tomogan/app.py` now honor the env var `DRAVA_CALLBACK_SERIALIZE`
  (0 or 1) and `DRAVA_CALLBACK_FLUSH_TIMEOUT_MS` instead of hard-coding them.
  Required by Exp 3 and useful to Exp 2.

## Required runtime changes still TODO

* **Exp 2** (full attribution of flush triggers): emit one log line per batch
  flush from `transport_js.cc` and `transport_socket.cc` of the form
  `[drava-flush] stage=<name> reason=<threshold|eos|timeout> size=<n>`.
  Without it the experiment still records latency but flush-trigger fractions
  are reported as `n/a` and rows are tagged `requires_runtime_change=true`.
* **Exp 5** (instrumentation overhead): add two compile-time flags,
  `-DDRAVA_DISABLE_METRICS=1` and `-DDRAVA_DISABLE_METRICS_TIMING=1`, that
  compile out the relevant `fetch_add` / `clock_gettime` paths in
  `src/drava_internal.cc`. Build the corresponding shared libraries and pass
  their paths via `--counters-only-build-dir` and `--disabled-build-dir`
  (or the `DRAVA_BUILD_DIR_*` env vars). Without those builds Exp 5 only
  collects the `full` mode and tags the others `requires_runtime_change=true`.

## Running

From the repo root, with PtychoNN/TomoGAN environments set up exactly as for
the existing benchmarks:

```bash
# Quick smoke (small frame counts, single run)
python experiments/exp1_runtime_overhead.py --batches 64,256 --runs 1 \
    --ptychonn-num-frames 256

# Full Exp 1 sweep
python experiments/exp1_runtime_overhead.py --workload both --runs 3

# Exp 2 (PtychoNN), 4x4 cells, 2 runs each
python experiments/exp2_microbatching.py --runs 2

# Exp 3 (both workloads, 4 thread counts, both modes)
python experiments/exp3_dispatch_mode.py --runs 2

# Exp 4 (NATS only by default; pass --enable-sockets for the sockets arm)
python experiments/exp4_transport.py --transports nats,sockets --enable-sockets

# Exp 5 (full mode only until other builds are provided)
python experiments/exp5_instrumentation_overhead.py --runs 3
```

All outputs land under `experiments/results/<exp_id>_<timestamp>/`.

## Output schema

Each `expN_summary.csv` shares the convention:

* one row per `(cell, run, stage)` so plotting tools can group easily;
* `n/a` is written as the empty string; numeric columns are floats;
* a `requires_runtime_change` column is set whenever a metric needed a
  runtime feature that was not available at run time.
