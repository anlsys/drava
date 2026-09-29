# PtychoPINN on JLSE

Copy-paste. Background: [README.md](README.md), [NOTES.md](NOTES.md).

To run this example from a config derived from its SystemFlow performance
model, see [docs/systemflow-jlse.md](../../docs/systemflow-jlse.md).

## Get a node

```shell
qsub -q gpu_a100 -t 200 -n 1 -I
```

## Every session

```shell
cd ~
source drava_nvidia.sh
export PYTHONPATH="$HOME/drava/build:$PYTHONPATH"
python -c "import drava; print('drava OK')"
```

## Build (only after a C/C++ change)

```shell
cd ~/drava/build
make -j
```

Re-run cmake only when changing compiler, Python or `*_ROOT`:

```shell
cd ~/drava/build
CC=clang CXX=clang++ cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j
```

Runtime tests:

```shell
ctest --test-dir ~/drava/build/tests -R base_index_ordering -V
```

## One-time install

```shell
cd ~/drava/examples/ptychopinn
pip install torch
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
pip install -r requirements.txt
```

```shell
cd ~
git clone https://github.com/AdvancedPhotonSource/PtychoPINN-torch-pub.git
cd PtychoPINN-torch-pub
pip install -e .
python -c "from ptychopinn_torch.eval.frc import frc_preprocess_images; print('imports OK')"
```

```shell
cd ~/drava/examples/ptychopinn
python download_zenodo.py --list
python download_zenodo.py
```

```shell
cd ~/PtychoPINN-torch-pub
python initialize_data.py --repo-root ~/drava/examples/ptychopinn/PtychoPINN_data --no-dry-run
```

## Prepare groups

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

## Run

```shell
cd ~/drava/examples/ptychopinn
./run_two_stages.sh
```

Smoke test:

```shell
DRAVA_PUBLISH_NUM_FRAMES=2000 ./run_two_stages.sh
```

Watch live from another shell:

```shell
tail -f ~/drava/examples/ptychopinn/run_logs/*/app_stage2.log
```

Prints the run summary and writes `run_logs/<stamp>/summary.csv`. Expect
`status=complete`, `nan_px_crop=0`, `FRC AUC 0.587875`, E2E ~4.9 s.

## Verify

```shell
cd ~/drava/examples/ptychopinn
python verify_against_upstream.py --dataset W --model PS_W
```

Expect `PASS: |dAUC| < 0.01`.

## Bisect a bad FRC

```shell
cd ~/drava/examples/ptychopinn
python debug_offline_reconstruct.py --batch-size 512
```

Near upstream → the streaming path is at fault. Near the pipeline → prep or
reassembly is.

## Re-print a summary

```shell
cd ~/drava/examples/ptychopinn
python summarize_run.py                  # newest run
python summarize_run.py run_logs/20260928_194419
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `import drava` fails | `export PYTHONPATH="$HOME/drava/build:$PYTHONPATH"` |
| `undefined symbol` on import | rebuild with `-DPython3_EXECUTABLE=$(which python)` |
| `ModuleNotFoundError: ptychopinn_torch.eval` | installed non-editable; `pip install -e` |
| `Fetch error: Limit reached` | stage outlived the run; normal after `[stage2-final]` |
