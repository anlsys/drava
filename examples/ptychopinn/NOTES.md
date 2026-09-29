# PtychoPINN example — design notes and caveats

Everything that is not needed to run the thing. See [README.md](README.md) to
run it, [JLSE.md](JLSE.md) for the command list.

## Why this is not shaped like the PtychoNN example

PtychoNN is frame-independent: one 64x64 patch in, one patch out. **PtychoPINN
is not.** Its published configuration is `C=4` with `object_big=true`, so one
model input is a *group of four spatially overlapping* diffraction patterns,
chosen by a KD-tree over the complete set of scan positions. A frame cannot be
grouped until all four of its quadrant neighbours have arrived — in a raster
scan, at best one full row later.

Grouping is therefore done once, offline, by
[prepare_dataset.py](prepare_dataset.py), and the pipeline streams groups. Two
facts keep the streaming stage clean:

- At inference, `forward_predict(x, positions, probe, input_scale_factor)` uses
  only `x` and `input_scale_factor` — it is just
  `scale -> autoencoder -> amp * exp(i*phase)`. `positions` and `probe` exist
  only for signature compatibility with the training `forward()`.
- Under `normalize: "Batch"` the scaling constant is a **single scalar** for
  the whole experiment, so the stage carries it as a constant.

| | PtychoNN | PtychoPINN |
|---|---|---|
| Framework | TensorFlow / Keras `.hdf5` | PyTorch / Lightning via MLflow |
| Frame payload | `64x64x1` float32 (16 KB) | 8-byte index + `4x64x64` float32 (64 KB) |
| Stage 1 output | amplitude + phase, real | complex object patch, centre-cropped |
| Stage 2 | overlap-add into a square grid | barycentric scatter-add onto a canvas |
| Stage 2 metric | stitch geometry only | FRC AUC vs `objectGuess` |
| Stage 2 callbacks | parallel (disjoint slices) | **serialized** (shared canvas) |
| Position source | runtime `base_index` | index carried in the payload |

## Verification methodology

Comparing straight to the paper conflates two questions: *does the pipeline
reproduce PtychoPINN?* and *does PtychoPINN here reproduce the paper?* Answer
them in order.

1. **Against upstream's own code path** — `verify_against_upstream.py` runs
   `generate_gt_and_recon` from `recreate_results.ipynb` and scores it with the
   *same* explicit FRC stage 2 uses. Exits non-zero on `|dAUC| >= 0.01` or a
   canvas shape mismatch. Not bit-identical: FP16 autocast makes reductions
   batch-composition dependent, and upstream regroups randomly each run.
2. **Prep numbers against the published notebook.** For `W`:

   | `prepare_dataset.py` prints | Expected |
   |---|---|
   | `n_scans` | `25921` |
   | `bounded centres` | `20449 of 25921` |
   | `grouped rows` | `20449` |
   | `max_offset` / `canvas` | `81` / `194x194` |
   | `batch rms scaling constant` | `~0.00022` |

   Grouped rows equals bounded centres, so **no centres are discarded on `W`**
   and caveat 3 below is inert for this dataset. That is what makes `W` a good
   first target.
3. **Frame accounting.** Publisher `frames`, stage1 `rx_items`, `groups=` in
   `[stage2-final]` and `n_groups` in `meta.json` must all be equal. A
   shortfall means dropped messages, not a result. Note this check cannot
   detect *misplacement*, only loss — see caveat 7.
4. **Against the paper.** Only once 1-3 are clean, read the FRC for this
   dataset/model off the manuscript's Figure 2 panel.

If 1 fails, bisect with `debug_offline_reconstruct.py`: it uses the prep
artifacts and this example's reassembly maths but no Drava. Near upstream means
the streaming path is at fault; near the pipeline means prep or reassembly is.

## Socket transport

Set `transport.type: socket` in [pipeline.yaml](pipeline.yaml), uncomment the
`output_fifo_path` / `socket_path` keys, then:

```shell
mkfifo /tmp/drava_in 2>/dev/null || true
socat /tmp/drava_in UNIX-LISTEN:/tmp/accel_2048.sock,fork
python publisher_socket.py
```

The runtime takes the socket path **only** from `ingress.socket_path`; it does
not read `DRAVA_SOCKET_PATH`.

## Configuration

Runtime behaviour (threads, batching, transport, streams, EOS forwarding) lives
in [pipeline.yaml](pipeline.yaml). Everything else is an environment variable.

Read by [config.py](config.py), so shared by every entry point:

| Variable | Default | Meaning |
|---|---|---|
| `PTYCHOPINN_DATA_ROOT` | `./PtychoPINN_data` | unpacked Zenodo bundle |
| `PTYCHOPINN_MLRUNS_DIR` | `<root>/mlruns` | MLflow file store |
| `PTYCHOPINN_DATASET` | `W` | dataset key |
| `PTYCHOPINN_MODEL` | `PS_W` | model key from `MODEL_IDS` |
| `PTYCHOPINN_RUN_ID` | — | explicit run hash, overrides the model key |
| `PTYCHOPINN_PREP_DIR` | `./prep/<ds>_<model>` | prep artifacts |
| `PTYCHOPINN_DEVICE` | `cuda` | stage 1 torch device |
| `PTYCHOPINN_MIXED_PRECISION` | `1` | FP16 autocast, as published |
| `PTYCHOPINN_FRC_AUC_CUTOFF` | `0.5` | AUC integration limit |
| `PTYCHOPINN_SAVE_RECON` | `1` | write `reconstruction.npz` |
| `PTYCHOPINN_RECON_PATH` | `<prep>/reconstruction.npz` | where to write it |
| `DRAVA_INFER_BATCH` | `128` | warmup batch size |
| `DRAVA_STAGE1_JOB_ID` | `1` | tag on stage1 messages |

Geometry (`N`, `C`, `middle_trim`, `window`, canvas size, rms constant) is not
configurable by environment: `prepare_dataset.py` takes it from the model's own
MLflow config and writes `meta.json`, which both stages treat as authoritative.
Change it with `prepare_dataset.py` flags, not env vars.

Read by [app_stage2.py](app_stage2.py) only:

| Variable | Default | Meaning |
|---|---|---|
| `PTYCHOPINN_STAGE2_DEVICE` | cuda if available | canvas accumulator device |
| `PTYCHOPINN_STAGE2_LOG_EVERY` | `25` | progress log interval, messages |

Read by `drava_common` (publisher side):

| Variable | Default | Meaning |
|---|---|---|
| `DRAVA_PUBLISH_NUM_FRAMES` | all groups | cap the run |
| `DRAVA_PUBLISH_RATE_HZ` | `0` (max) | pacing |
| `DRAVA_PUBLISHER_METRICS_FILE` | — | publisher metrics JSON |

Read by [run_two_stages.sh](run_two_stages.sh):

| Variable | Default | Meaning |
|---|---|---|
| `JSDATA_DIR` | `<run>/jsdata` | JetStream store location |
| `RUN_DIR` | `run_logs/<stamp>` | log directory |
| `START_NATS` | `1` | set `0` to reuse a running server |
| `APP_TIMEOUT_S` | `3600` | give up waiting for `[stage2-final]` |

## Known caveats

1. **Check whether your interpreter is actually free-threaded.** PyTorch,
   Lightning, tensordict and MLflow have limited free-threaded wheel coverage.
   Do not trust the venv's name — one called `no-gil-3.13` may be a stock conda
   build:

   ```shell
   python -c "import sysconfig; print(bool(sysconfig.get_config_var('Py_GIL_DISABLED')))"
   ```

   `False` means a normal GIL build; the whole stack installs from PyPI as
   usual, and that is fully supported — `PY_NO_GIL` is never defined in
   `CMakeLists.txt`, so `drava_routine_wrap.c` always compiles the
   `PyGILState_Ensure`/`Release` path. Free-threading buys parallel callbacks,
   not correctness. Either way confirm the build matches the interpreter:

   ```shell
   python -c "import drava; print('drava OK')"
   ldd <build>/_drava_python*.so | grep -i python
   ```

2. **Stage 2 must stay serialized.** `callback_serialize: true` is
   load-bearing: stage 2 scatter-adds overlapping patches into one shared
   canvas, and parallel callbacks would race on that in-place accumulation.

3. **Upstream's memmap row-count bug is sidestepped, not inherited.**
   `PtychoDataset` pre-allocates from an *estimated* row count while
   `get_fixed_quadrant_neighbors_c4` discards centres lacking a neighbour in
   all four quadrants, leaving zero-filled phantom rows whose
   `coords_global == 0` inflate `max_offset` and therefore the canvas the FRC
   crop is taken from. `prepare_dataset.py` sizes everything from the *actual*
   group count, matching the fix in both the intern's fork and the maintainer's
   repo. On datasets where centres are discarded the reconstruction is
   therefore **not bit-identical to the published artifact**; it is the
   bug-fixed baseline. Inert on `W`.

4. **FRC is computed explicitly rather than via `analysis.py`.** Upstream's
   `preprocess_and_calculate_frc` is defined twice in that file with two
   different AUC cutoffs (1.0, then 0.5 shadowing it). Stage 2 calls
   `frc_preprocess_images` and `FSC` directly and integrates to
   `PTYCHOPINN_FRC_AUC_CUTOFF` (0.5) so the reported number is unambiguous.
   Note the published path uses `align=False` — no registration — so a
   *displaced* reconstruction is penalised as if it were degraded.

5. **`model.training = True`** is replicated from upstream's inference path
   verbatim. It sets the flag on the top module only, not submodules. With
   `batch_norm: false` in the published config it has no effect, but the path
   matches.

6. **Centre of mass follows the branch that actually executes.** Upstream's
   `reconstruct_image_barycentric` has an inverted condition:
   `if 'com' in data_dict: center_of_mass = mean(global_coords) else: ... = data_dict['com']`.
   Since `memory_map_data` always sets `data_dict['com']`, the mean-over-
   `coords_global` branch always runs and the stored value is dead code. The
   two differ, because `coords_global` includes neighbours just outside the
   bounds and weights each position by how many groups contain it.
   `prepare_dataset.py` reproduces the executing branch and records the unused
   one as `com_bounded_unused` in `meta.json`. On `W` this yields an x/y
   asymmetry of ~1.03 px on an exactly symmetric scan; upstream produces the
   same value, and it is not the source of any error.

7. **Position is carried in the payload, not taken from `base_index`.** The
   runtime reserves `base_index` in the transport fetch loop so it is
   arrival-ordered (see `drava_reserve_base_index`), but this example does not
   depend on that: each frame is prefixed with its 8-byte group index, and
   stage 1 cross-checks it against `base_index` and warns on disagreement.
   That also makes the pipeline immune to JetStream reordering and to
   redelivery at stage 1.

8. **Grouping is randomised upstream.** `get_fixed_quadrant_neighbors_c4` calls
   `np.random.choice` once per quadrant per group against the unseeded global
   RNG. `prepare_dataset.py --seed` (default 0) makes it reproducible;
   `--seed -1` restores upstream behaviour. Upstream itself is unseeded, so
   `verify_against_upstream.py` will differ slightly run to run — its observed
   spread is about ±0.005 AUC.

9. **Delivery is at-least-once.** The runtime acks after enqueue, so a message
   can arrive twice. Scatter-add is not idempotent, so stage 2 keeps a `seen`
   mask keyed on the group index and drops repeats. Redelivery is most easily
   triggered by a slow callback stalling the ack loop; `consumer_seq` climbing
   past `stream_seq` in a stage log is the symptom.

10. **Multi-GPU is not used.** Upstream's `reconstruct_image_barycentric`
    unconditionally overwrites its `gpu_ids` argument and wraps the model in
    `nn.DataParallel` whenever more than one device is visible, which changes
    the effective per-device batch. This example bypasses that function and
    runs single-device. Pin with `CUDA_VISIBLE_DEVICES=0` for reproducible
    timings.

11. **`weights_only` on newer torch.** PyTorch 2.6 flipped `torch.load` to
    `weights_only=True`. The Zenodo artifacts are fully pickled
    `PtychoPINN_Lightning` objects, not state dicts. Recent MLflow passes
    `weights_only=False` itself; if yours does not, the model came from the
    paper's own Zenodo record and can be allowed explicitly.

## Isolating a model-load problem

Seconds, and separates an artifact/torch problem from a transport problem:

```shell
python -c "
import config, mlflow, torch
mlflow.set_tracking_uri(f'file:{config.MLRUNS_DIR.resolve()}')
m = mlflow.pytorch.load_model(f'runs:/{config.RUN_ID}/model', map_location='cpu')
print('loaded', type(m).__name__, hasattr(m, 'forward_predict'))
"
```

Expect `loaded PtychoPINN_Lightning True`.
