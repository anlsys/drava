## PtychoPINN Example

End-to-end inference workflow for **PtychoPINN** (PyTorch) on Drava, reproducing
a published reconstruction and scoring it against the paper's Fourier ring
correlation metric.

Scan-position groups are streamed from a publisher, transported through Drava
over JetStream or a Unix socket, run through the trained autoencoder in stage 1,
and reassembled into a full complex object on a shared canvas in stage 2.

```
publisher -> FRAMES/frames.raw -> [stage1: forward_predict] -> PATCHES/frames.stage1 -> [stage2: barycentric canvas + FRC]
```

### How this differs from the PtychoNN example

PtychoNN is frame-independent: one 64x64 diffraction patch in, one patch out.
**PtychoPINN is not.** Its published configuration is `C=4` with
`object_big=true`, so one model input is a *group of four spatially overlapping*
diffraction patterns, chosen by a KD-tree over the complete set of scan
positions. A frame cannot be grouped until all four of its quadrant neighbours
have arrived, which in a raster scan is at best one full scan row later.

Grouping is therefore done **once, offline**, by
[prepare_dataset.py](prepare_dataset.py), and the pipeline streams groups. Two
facts make the streaming stage clean:

- At inference, `forward_predict(x, positions, probe, input_scale_factor)` uses
  only `x` and `input_scale_factor`. It is just
  `scale -> autoencoder -> amp * exp(i*phase)`. `positions` and `probe` exist
  only for signature compatibility with the training `forward()`, where the
  physics forward model consumes them.
- Under `normalize: "Batch"` the scaling constant is a **single scalar** for the
  whole experiment, so the stage can carry it as a constant.

| | PtychoNN | PtychoPINN |
|---|---|---|
| Framework | TensorFlow / Keras `.hdf5` | PyTorch / Lightning via MLflow |
| Frame payload | `64x64x1` float32 (16 KB) | `4x64x64` float32 group (64 KB) |
| Stage 1 output | amplitude + phase, real | complex object patch, centre-cropped |
| Stage 2 | overlap-add into a square grid | barycentric scatter-add onto a canvas |
| Stage 2 metric | stitch geometry only | FRC AUC vs `objectGuess` |
| Stage 2 callbacks | parallel (disjoint slices) | **serialized** (shared canvas) |

### Dataset and model

Both come from the paper's Zenodo record,
[10.5281/zenodo.16968020](https://doi.org/10.5281/zenodo.16968020):

- `data.tar.gz` — Ptychodus-formatted `.npz` per experiment, each containing
  `diff3d` `(n_scans, 64, 64)`, `xcoords`, `ycoords`, `probeGuess`, and
  `objectGuess` (the reconstruction used as ground truth).
- `mlruns.tar.gz` — MLflow runs holding the trained models.

Defaults are the **W** dataset with the **PS_W** model
(`74ba23396c4042afb1751afe9fa87520`), the dead-leaves synthetic pretrain used in
the paper's Figure 2 transfer experiment. Other Figure 2 models are listed in
[config.py](config.py); the multi-probe and synthetic-object models are in
upstream's `recreate_results.ipynb`.

### Disk footprint (read before installing)

This example is far heavier than the TensorFlow ones. On a quota-limited home
directory it **will** fail partway through the torch install.

| Item | Approx. size |
|---|---|
| `torch` + bundled CUDA/cuDNN/NCCL/Triton wheels, installed | ~6 GB |
| pip's wheel cache for the same | ~3 GB |
| Zenodo `data.tar.gz` + `mlruns.tar.gz` | several GB (check with `--list`) |
| `prep/` artifacts + reconstruction | modest, ~100 MB |

Put everything on a scratch or project filesystem:

```shell
export BIG=/scratch/$USER              # whatever your site provides
mkdir -p $BIG/{pipcache,tmp,ptychopinn_data}
export PIP_CACHE_DIR=$BIG/pipcache
export TMPDIR=$BIG/tmp
export PTYCHOPINN_DATA_ROOT=$BIG/ptychopinn_data
export PTYCHOPINN_PREP_DIR=$BIG/ptychopinn_data/prep_W_PS_W
```

`config.py` honours the last two, so every later step follows automatically.

### Setup

```shell
cd examples/ptychopinn
python -m venv venv                    # or put the venv on $BIG too
source venv/bin/activate

# torch first. The default PyPI wheel bundles its own CUDA runtime, so the
# host's nvcc version is irrelevant -- only the driver matters. Do not pass
# --index-url unless the default fails.
pip install --no-cache-dir torch
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"

pip install -r requirements.txt

# The published package, from a checkout (not on PyPI). The -e is MANDATORY:
# upstream's setup.py uses find_packages(), and eval/, notebooks/ and datagen/
# have no __init__.py, so a non-editable install silently drops them and
# stage 2 fails at `import ptychopinn_torch.eval.frc`.
pip install -e /path/to/PtychoPINN-torch-pub
```

Download and unpack the artifacts (several GB):

```shell
python download_zenodo.py --list          # inspect sizes first
python download_zenodo.py                 # -> ./PtychoPINN_data/{data,mlruns}
```

Rewrite the MLflow artifact URIs to their new absolute location, using
upstream's own script so nothing is forked here:

```shell
cd /path/to/PtychoPINN-torch-pub
python initialize_data.py --repo-root "$PWD/../drava/examples/ptychopinn/PtychoPINN_data" --no-dry-run
```

> Note the hyphen: upstream's README documents `--no_dry_run`, but argparse
> defines `--no-dry-run` and does not accept the underscore form.

This step is belt-and-braces: [app.py](app.py) also falls back to loading the
model artifact directly off disk if the `runs:/` URI cannot be resolved.

### Prepare the groups

```shell
python prepare_dataset.py --dataset W --model PS_W
```

This reads the model's own config out of MLflow, applies the same overrides
`recreate_results.ipynb` uses (`normalize='Batch'`, `n_subsample=1`,
bounds `[0.05, 0.95]`), runs upstream's unmodified `group_coords` and
`get_rms_scaling_factor`, and writes:

```
prep/W_PS_W/groups.npz    # nn_indices, coords_global, com, objectGuess
prep/W_PS_W/meta.json     # N, C, middle_trim, canvas_side, rms constant, window
```

Everything downstream reads geometry from `meta.json`. Nothing guesses it.

### Run

```shell
# build dir on PYTHONPATH so `import drava` works
cd ~/drava/build && export PYTHONPATH="$(pwd):$PYTHONPATH"
cd ~/drava/examples/ptychopinn && source venv/bin/activate

./run_two_stages.sh
```

Or manually, in three terminals (launch downstream-first):

```shell
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml

DRAVA_STAGE_NAME=stage2 python app_stage2.py     # terminal 1
DRAVA_STAGE_NAME=stage1 python app.py            # terminal 2
python publisher_jetstream.py                    # terminal 3
```

A short smoke run without streaming the whole scan:

```shell
DRAVA_PUBLISH_NUM_FRAMES=2000 ./run_two_stages.sh
```

### Result

Stage 2 emits one machine-parseable line at end-of-stream:

```
[stage2-final] frames=... groups=... canvas_side=... window=20 \
  recon_shape=...x... gt_shape=...x... nan_px=... frc_auc=0.xxxxxx \
  dataset=W model=PS_W
```

`frc_auc` is the area under the Fourier ring correlation curve from 0 to
half-Nyquist, the paper's headline resolution metric. The reconstruction and
ground truth are also written to `prep/<dataset>_<model>/reconstruction.npz`
(disable with `PTYCHOPINN_SAVE_RECON=0`).

### Verifying the result

Comparing straight to the paper conflates two questions: *does the Drava
pipeline reproduce PtychoPINN?* and *does PtychoPINN on this machine reproduce
the paper?* Answer them in that order.

**Step 1 — against upstream's own code path (the decisive check):**

```shell
python verify_against_upstream.py --dataset W --model PS_W
```

This runs `generate_gt_and_recon` from `recreate_results.ipynb` and scores it
with the *same* explicit FRC used by stage 2, then diffs the two. Expect
agreement to 2-3 decimal places; it is not bit-identical because FP16 autocast
makes reductions batch-composition dependent. The script exits non-zero if
`|dAUC| >= 0.01` or if the canvas shapes disagree.

**Step 2 — prep numbers against the published notebook.** For the `W` dataset,
upstream's captured notebook output gives exact anchors:

| `prepare_dataset.py` prints | Expected for `W` |
|---|---|
| `n_scans` | `25921` |
| `bounded centres` | `20449 of 25921` |
| `grouped rows` | `20449` |
| `max_offset` / `canvas` | `80` / `192x192` |
| `batch rms scaling constant` | `~0.0002` |

Note that grouped rows equals bounded centres here, so **no centres are
discarded on `W`** and caveat 3 below is a no-op for this dataset. That is what
makes `W` a good first target.

**Step 3 — frame accounting.** All four must be equal to `n_groups`:
publisher `frames` in `run_logs/*/pub_metrics.json`, `rx_items` in
`metrics_stage1.jsonl`, `groups=` in the `[stage2-final]` line, and
`n_groups` in `meta.json`. Any shortfall means dropped messages, not a
scientific result.

**Step 4 — against the paper.** Only once steps 1-3 are clean, read the FRC
value for this dataset/model off the manuscript's Figure 2 panel.

### Socket transport

Set `transport.type: socket` in [pipeline.yaml](pipeline.yaml), uncomment the
`output_fifo_path` / `socket_path` keys, then:

```shell
mkfifo /tmp/drava_in 2>/dev/null || true
socat /tmp/drava_in UNIX-LISTEN:/tmp/accel_2048.sock,fork
python publisher_socket.py
```

### Configuration

Runtime behaviour (threads, batching, transport, streams, EOS forwarding) lives
in [pipeline.yaml](pipeline.yaml). App-level knobs are environment variables
read by [config.py](config.py):

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
| `PTYCHOPINN_SAVE_RECON` | `1` | write `reconstruction.npz` |
| `DRAVA_INFER_BATCH` | `128` | warmup batch size |

### Known caveats

Read these before trusting a number out of this example.

1. **Check whether your interpreter is actually free-threaded.** PyTorch,
   Lightning, tensordict, and MLflow have limited free-threaded wheel coverage,
   so this is the first thing to establish. Do not trust the venv's name -- a
   venv called `no-gil-3.13` may well have been created from a stock conda
   Python:

   ```shell
   python -c "import sysconfig; print(bool(sysconfig.get_config_var('Py_GIL_DISABLED')))"
   python -VV
   ```

   `False` means a normal GIL build and the whole stack installs from PyPI as
   usual. That is fully supported: `PY_NO_GIL` is never defined in
   `CMakeLists.txt`, so `api/python/drava_routine_wrap.c` always compiles the
   `PyGILState_Ensure`/`Release` path. Free-threading buys parallel callbacks,
   not correctness.

   `True` and the stack refuses to install: build the SWIG module against a
   standard GIL interpreter and use that one here:

   ```shell
   cmake -DPython3_EXECUTABLE=$(which python) ..
   ```

   Either way, confirm the build matches the interpreter before running --
   a module built against a different Python fails with `undefined symbol`:

   ```shell
   python -c "import drava; print('drava OK')"
   ldd <build>/_drava_python*.so | grep -i python
   ```
2. **Stage 2 must stay serialized.** `callback_serialize: true` is load-bearing;
   see the comment in `pipeline.yaml`.
3. **Upstream's memmap row-count bug is sidestepped, not inherited.**
   `PtychoDataset` pre-allocates from an *estimated* row count while
   `get_fixed_quadrant_neighbors_c4` discards centres lacking a neighbour in all
   four quadrants, leaving zero-filled phantom rows whose `coords_global == 0`
   inflate `max_offset` and therefore the canvas the FRC crop is taken from.
   `prepare_dataset.py` sizes everything from the *actual* group count, matching
   the fix in both the intern's fork and the maintainer's repo. This means the
   reconstruction is **not bit-identical to the published artifact** on datasets
   where centres are discarded; it is the bug-fixed baseline.
4. **FRC is computed explicitly rather than via `analysis.py`.** Upstream's
   `preprocess_and_calculate_frc` is defined twice in that file with two
   different AUC cutoffs (1.0, then 0.5 shadowing it). Stage 2 calls
   `frc_preprocess_images` and `FSC` directly and integrates to
   `PTYCHOPINN_FRC_AUC_CUTOFF` (0.5) so the reported number is unambiguous.
5. **`model.training = True`** is replicated from upstream's inference path
   verbatim. It sets the flag on the top module only, not submodules. With
   `batch_norm: false` in the published config it has no effect, but it is kept
   so the path matches.
6. **Centre of mass follows the branch that actually executes.** Upstream's
   `reconstruct_image_barycentric` has an inverted condition:
   `if 'com' in data_dict: center_of_mass = mean(global_coords) else: ... = data_dict['com']`.
   Since `memory_map_data` always sets `data_dict['com']`, the mean-over-
   `coords_global` branch always runs and the stored value is dead code. The two
   differ, because `coords_global` includes neighbours just outside the bounds
   and weights each scan position by how many groups contain it.
   `prepare_dataset.py` reproduces the executing branch and records the unused
   one as `com_bounded_unused` in `meta.json` for comparison.
7. **Multi-GPU is not used.** Upstream's `reconstruct_image_barycentric`
   unconditionally overwrites its `gpu_ids` argument and wraps the model in
   `nn.DataParallel` whenever more than one device is visible, which changes the
   effective per-device batch. This example bypasses that function and runs
   single-device. Pin with `CUDA_VISIBLE_DEVICES=0` for reproducible timings.

### References

- [PtychoPINN-torch published artifact](https://github.com/AdvancedPhotonSource/PtychoPINN-torch-pub)
- [PtychoPINN upstream (maintained)](https://github.com/hoidn/PtychoPINN)
- [Zenodo record 16968020](https://doi.org/10.5281/zenodo.16968020)
- Paper: *Robust, multi-probe ptychographic neural networks via
  experimentally-grounded synthetic data*, npj Computational Materials (2026),
  `s41524-026-02198-4`.
