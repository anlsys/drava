## PtychoPINN Example

Two-stage inference for **PtychoPINN** (PyTorch) on Drava, reproducing a
published reconstruction and scoring it with the paper's Fourier ring
correlation.

```
publisher -> FRAMES/frames.raw -> [stage1: forward_predict] -> PATCHES/frames.stage1 -> [stage2: canvas + FRC]
```

- **[JLSE.md](JLSE.md)** — copy-paste commands for an A100 node
- **[NOTES.md](NOTES.md)** — design, caveats, socket transport, env vars

### Dependencies

| Need | How |
|---|---|
| Drava built, on `PYTHONPATH` | [../../docs/jlse.md](../../docs/jlse.md) |
| `torch` | `pip install torch` |
| Example deps | `pip install -r requirements.txt` |
| `ptychopinn_torch` | `pip install -e /path/to/PtychoPINN-torch-pub` — **`-e` is required** |
| Data + weights | `python download_zenodo.py` |

### Setup

```shell
cd ~/drava/examples/ptychopinn
pip install torch
pip install -r requirements.txt

cd ~
git clone https://github.com/AdvancedPhotonSource/PtychoPINN-torch-pub.git
cd PtychoPINN-torch-pub
pip install -e .

cd ~/drava/examples/ptychopinn
python download_zenodo.py

cd ~/PtychoPINN-torch-pub
python initialize_data.py --repo-root ~/drava/examples/ptychopinn/PtychoPINN_data --no-dry-run
```

### Run

```shell
cd ~/drava/examples/ptychopinn
python prepare_dataset.py --dataset W --model PS_W --seed 0
./run_two_stages.sh
```

`prepare_dataset.py` groups the scan positions offline. Re-run it whenever the
dataset, model or seed changes.

### Result

`run_two_stages.sh` prints a summary and writes `run_logs/<stamp>/summary.csv`:

```
 dataset / model     W / PS_W   run_id=74ba23396c40...
 status              complete   groups=20449/20449   duplicates=0
 stage        rx_items    time_s     items/s  unit
 publisher       20449     2.134      9581.0  groups
 stage1          20449     3.044      6717.0  groups
 stage2            320     2.938       108.9  messages (20449 groups)
 pipeline e2e        4.898 s   (publisher start -> stage2 finalize)
 FRC AUC (0..0.5)    0.587875
 canvas 194x194   crop 154x154   window 20   nan_px_crop=0
 frame accounting OK (20449 through every stage)
```

Gates: `status=complete`, `nan_px_crop=0`, frame accounting OK.
Re-print any run with `python summarize_run.py [run_logs/<stamp>]`.

### Verify

```shell
python verify_against_upstream.py --dataset W --model PS_W
```

Runs upstream's own `generate_gt_and_recon` and diffs. Expect
`PASS: |dAUC| < 0.01`. Reference on 1x A100-PCIE-40GB: Drava 0.587875,
upstream 0.584559 - 0.590006 over 3 runs, complex NRMSE 0.0144. Upstream
regroups randomly each run, so expect a ±0.005 spread and no bit equality.

### Dataset and model

Zenodo [10.5281/zenodo.16968020](https://doi.org/10.5281/zenodo.16968020).
Default is **W** / **PS_W** (`74ba23396c4042afb1751afe9fa87520`), the Figure 2
dead-leaves pretrain; other Figure 2 models are in [config.py](config.py).
Paper: npj Computational Materials (2026), `s41524-026-02198-4`.
[Artifact](https://github.com/AdvancedPhotonSource/PtychoPINN-torch-pub) ·
[upstream](https://github.com/hoidn/PtychoPINN)
