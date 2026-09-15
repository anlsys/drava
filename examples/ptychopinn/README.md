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

### Setup

```shell
cd examples/ptychopinn
python -m venv venv
source venv/bin/activate

# torch first, matched to the node's CUDA
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt

# the published package, from a checkout (not on PyPI)
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

To compare against the paper, run the same dataset/model pair here and read the
corresponding FRC value from the manuscript's Figure 2 panel.

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

1. **Free-threaded Python is the main integration risk.** Drava's other
   examples run under the no-GIL Python 3.13/3.14 build on JLSE. PyTorch,
   Lightning, tensordict, and MLflow have limited or no free-threaded wheel
   coverage. If the stack will not install, build the Drava SWIG module against
   a standard GIL Python 3.12 and use that interpreter for this example.
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
