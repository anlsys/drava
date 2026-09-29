# PtychoPINN on JLSE

Commands only. Background: [README.md](README.md), [NOTES.md](NOTES.md).

## 1. Get an A100 node

```shell
qsub -q gpu_a100 -t 200 -n 1 -I
```

## 2. Environment (every session)

```shell
source ~/drava_nvidia.sh                        # modules
source ~/venvs/no-gil-3.13/bin/activate         # venv
export PYTHONPATH="$HOME/drava/build:$PYTHONPATH"
python -c "import drava; print('drava OK')"
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

## 3. Build (only after a C/C++ change)

```shell
cd ~/drava/build && make -j
```

Re-run `cmake` only when changing compiler, Python or `*_ROOT`:

```shell
CC=clang CXX=clang++ cmake -DCMAKE_BUILD_TYPE=Debug .. && make -j
```

## 4. One-time setup

Scratch first — torch is ~6 GB installed, ~3 GB cached, data is several GB.

```shell
export BIG=/scratch/$USER
mkdir -p $BIG/{pipcache,tmp,ptychopinn_data}
export PIP_CACHE_DIR=$BIG/pipcache TMPDIR=$BIG/tmp
export PTYCHOPINN_DATA_ROOT=$BIG/ptychopinn_data
export PTYCHOPINN_PREP_DIR=$BIG/ptychopinn_data/prep_W_PS_W
```

```shell
cd ~/drava/examples/ptychopinn
pip install --no-cache-dir torch
pip install -r requirements.txt

cd ~ && git clone https://github.com/AdvancedPhotonSource/PtychoPINN-torch-pub.git
cd PtychoPINN-torch-pub && pip install -e .          # -e is required
python -c "from ptychopinn_torch.eval.frc import frc_preprocess_images; print('imports OK')"
```

```shell
cd ~/drava/examples/ptychopinn
python download_zenodo.py --list                     # check sizes first
python download_zenodo.py

cd ~/PtychoPINN-torch-pub
python initialize_data.py --repo-root $PTYCHOPINN_DATA_ROOT --no-dry-run
```

## 5. Prepare groups (per dataset/model/seed)

```shell
cd ~/drava/examples/ptychopinn
python prepare_dataset.py --dataset W --model PS_W --seed 0
```

Expected for `W`:

```
n_scans=25921   bounded centres: 20449 of 25921   grouped rows: 20449
batch rms scaling constant = 0.00022064150834921747
max_offset=81 canvas=194x194 middle_trim=32
```

## 6. Run

```shell
./run_two_stages.sh                              # full 20449-group scan
DRAVA_PUBLISH_NUM_FRAMES=2000 ./run_two_stages.sh   # smoke test
```

Watch live:

```shell
tail -f run_logs/*/app_stage2.log
```

Reference (1x A100-PCIE-40GB): publisher ~9500 groups/s, stage1 ~6700
groups/s, E2E ~4.9 s, FRC AUC 0.587875.

## 7. Verify

```shell
python verify_against_upstream.py --dataset W --model PS_W
```

Expect `PASS: |dAUC| < 0.01`.

## 8. Bisect a bad FRC

```shell
python debug_offline_reconstruct.py --batch-size 512   # no Drava at all
```

Near upstream → streaming path at fault. Near the pipeline → prep or
reassembly at fault.

## 9. Disk

```shell
du -sh ~/drava/examples/ptychopinn/* | sort -h
pgrep -af nats-server            # must be empty before deleting a store
```

| Path | Keep? |
|---|---|
| `run_logs/<stamp>/jsdata` | delete after reading `summary.csv` |
| `run_logs/` | delete old runs |
| `prep/` | keep, else re-run `prepare_dataset.py` |
| `PtychoPINN_data/` | keep, else re-download several GB |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `import drava` fails | `export PYTHONPATH="$HOME/drava/build:$PYTHONPATH"` |
| `undefined symbol` on import | rebuild with `-DPython3_EXECUTABLE=$(which python)` |
| `MlflowException: ... maintenance mode` | `export MLFLOW_ALLOW_FILE_STORE=true` (config.py sets it too) |
| `ModuleNotFoundError: ptychopinn_torch.eval` | installed non-editable; reinstall with `pip install -e` |
| `_read_array_header` missing | NumPy 2.x; already shimmed in `verify_against_upstream.py` |
| `Fetch error: Limit reached` | stage outlived the run; normal after `[stage2-final]` |
| Disk quota exceeded | see §4 scratch exports |
