## PtychoPINN Example

Two-stage inference for **PtychoPINN** (PyTorch) on Drava, reproducing a
published reconstruction and scoring it with the paper's Fourier ring
correlation.

```
publisher -> FRAMES/frames.raw -> [stage1: forward_predict] -> PATCHES/frames.stage1 -> [stage2: canvas + FRC]
```

- **[JLSE.md](JLSE.md)** — copy-paste commands for an A100 node
- **[NOTES.md](NOTES.md)** — design, caveats, socket transport, troubleshooting

### Dependencies

| Need | How |
|---|---|
| Drava built, on `PYTHONPATH` | [../../docs/jlse.md](../../docs/jlse.md) |
| `torch` (matched to the node's CUDA) | `pip install --no-cache-dir torch` |
| Example deps | `pip install -r requirements.txt` |
| `ptychopinn_torch` | `pip install -e /path/to/PtychoPINN-torch-pub` — **`-e` is required**, see NOTES |
| Data + weights (several GB) | `python download_zenodo.py` |

Put the venv, pip cache and data on scratch; torch alone is ~6 GB installed
plus ~3 GB cached.

```shell
export BIG=/scratch/$USER
export PIP_CACHE_DIR=$BIG/pipcache TMPDIR=$BIG/tmp
export PTYCHOPINN_DATA_ROOT=$BIG/ptychopinn_data
export PTYCHOPINN_PREP_DIR=$BIG/ptychopinn_data/prep_W_PS_W
```

### Setup

```shell
cd examples/ptychopinn
pip install --no-cache-dir torch
pip install -r requirements.txt
pip install -e /path/to/PtychoPINN-torch-pub

python download_zenodo.py                     # -> PtychoPINN_data/{data,mlruns}

cd /path/to/PtychoPINN-torch-pub              # rewrite MLflow artifact URIs
python initialize_data.py --repo-root <PTYCHOPINN_DATA_ROOT> --no-dry-run
```

### Run

```shell
cd examples/ptychopinn
python prepare_dataset.py --dataset W --model PS_W --seed 0
./run_two_stages.sh
```

`prepare_dataset.py` groups the scan positions offline and must be re-run
whenever the dataset, model or seed changes.

### Result

`run_two_stages.sh` prints a summary and writes `run_logs/<stamp>/summary.csv`:

```
status              complete   groups=20449/20449   duplicates=0
FRC AUC (0..0.5)    0.587875
canvas 194x194   crop 154x154   window 20   nan_px_crop=0
frame accounting OK (20449 through every stage)
```

Gates: `status=complete`, `nan_px_crop=0`, frame accounting OK.

### Verify

```shell
python verify_against_upstream.py --dataset W --model PS_W
```

Runs upstream's own `generate_gt_and_recon` and diffs. Expect `PASS`
(`|dAUC| < 0.01`). Reference on 1x A100-PCIE-40GB:

| | |
|---|---|
| Drava FRC AUC | 0.587875 |
| Upstream | 0.584559 - 0.590006 (3 runs) |
| complex NRMSE | 0.0144 |

Upstream regroups randomly each run, so expect ±0.005 spread and no bit
equality. Full methodology in [NOTES.md](NOTES.md).

### Dataset and model

Zenodo [10.5281/zenodo.16968020](https://doi.org/10.5281/zenodo.16968020):
`data.tar.gz` (Ptychodus `.npz` per experiment) and `mlruns.tar.gz` (trained
models). Default is dataset **W** with model **PS_W**
(`74ba23396c4042afb1751afe9fa87520`), the Figure 2 dead-leaves pretrain.
Other Figure 2 models are in [config.py](config.py).

### References

- [PtychoPINN-torch published artifact](https://github.com/AdvancedPhotonSource/PtychoPINN-torch-pub)
- [PtychoPINN upstream (maintained)](https://github.com/hoidn/PtychoPINN)
- Paper: *Robust, multi-probe ptychographic neural networks via
  experimentally-grounded synthetic data*, npj Computational Materials (2026),
  `s41524-026-02198-4`.
