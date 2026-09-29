# SystemFlow interface on JLSE

Copy-paste. Background: [systemflow.md](systemflow.md). General build:
[jlse.md](jlse.md). PtychoPINN runbook:
[examples/ptychopinn/JLSE.md](../examples/ptychopinn/JLSE.md).

**The importer is pure Python.** It needs no C++ build, no GPU, and no
`systemflow` install. Tier 1 below runs on a login node in seconds. Only tier 2
— proving the derived config drives a real pipeline — needs an A100 node.

## Tier 1 — the importer alone (login node, no build)

```shell
cd ~/drava
git fetch origin
git checkout feature/systemflow
```

Only PyYAML is required:

```shell
python -c "import yaml; print('pyyaml', yaml.__version__)"
```

Run the unit tests:

```shell
python examples/common/tests/test_systemflow.py
```

Expect `21/21 passed`. The whole pure-Python suite:

```shell
python examples/common/tests/run_tests.py
```

Generate a pipeline config from the PtychoPINN performance model:

```shell
./drava-pipeline from-systemflow examples/ptychopinn/systemflow_model.yaml
```

Write it out and validate it, **without touching the checked-in
`pipeline.yaml`** (see [Do not clobber pipeline.yaml](#do-not-clobber-pipelineyaml)):

```shell
mkdir -p .scratch
./drava-pipeline from-systemflow examples/ptychopinn/systemflow_model.yaml \
    -o .scratch/sf_pipeline.yaml --force
./drava-pipeline validate .scratch/sf_pipeline.yaml
```

Expected:

```
wrote .scratch/sf_pipeline.yaml — pipeline 'ptychopinn_two_stage', transport=nats
    stages: stage1 -> stage2
    from SystemFlow graph 'ptychopinn inference' in examples/ptychopinn/systemflow_model.yaml
      stage1 <- node 'PtychoPINN inference'
      stage2 <- node 'Canvas assembly'
OK: .scratch/sf_pipeline.yaml — pipeline 'ptychopinn_two_stage', transport=nats
    stages: stage1 -> stage2
```

## Tier 2 — prove the derived config runs PtychoPINN

This is the test that matters: the SystemFlow-derived config must produce the
**same scientific result** as the hand-written one.

Prerequisite: PtychoPINN already set up per
[examples/ptychopinn/JLSE.md](../examples/ptychopinn/JLSE.md) (Zenodo download,
`prepare_dataset.py` run). No rebuild is needed — nothing in `src/` changed.

```shell
qsub -q gpu_a100 -t 200 -n 1 -I
```

```shell
cd ~
source drava_nvidia.sh
export PYTHONPATH="$HOME/drava/build:$PYTHONPATH"
python -c "import drava; print('drava OK')"
```

Generate the config:

```shell
cd ~/drava
mkdir -p .scratch
./drava-pipeline from-systemflow examples/ptychopinn/systemflow_model.yaml \
    -o .scratch/sf_pipeline.yaml --force
./drava-pipeline validate .scratch/sf_pipeline.yaml
```

Smoke test with the derived config (`run_two_stages.sh:24` honours
`DRAVA_STAGE_CONFIG`):

```shell
cd ~/drava/examples/ptychopinn
DRAVA_STAGE_CONFIG=$HOME/drava/.scratch/sf_pipeline.yaml \
DRAVA_PUBLISH_NUM_FRAMES=2000 ./run_two_stages.sh
```

Check the banner prints the derived path:

```
[run] stage config: /home/<user>/drava/.scratch/sf_pipeline.yaml
```

Full run:

```shell
cd ~/drava/examples/ptychopinn
DRAVA_STAGE_CONFIG=$HOME/drava/.scratch/sf_pipeline.yaml ./run_two_stages.sh
```

Expect exactly the numbers from the normal path: `status=complete`,
`nan_px_crop=0`, `FRC AUC 0.587875`, E2E ~4.9 s.

## Tier 3 — A/B against the checked-in config

The point is that the two configs are interchangeable.

```shell
cd ~/drava/examples/ptychopinn

# Baseline: the checked-in pipeline.yaml
./run_two_stages.sh
python summarize_run.py

# Derived: the SystemFlow-generated config
DRAVA_STAGE_CONFIG=$HOME/drava/.scratch/sf_pipeline.yaml ./run_two_stages.sh
python summarize_run.py
```

Compare the two `run_logs/<stamp>/summary.csv` files.

`nan_px_crop` must be `0` in both, and frame accounting must be OK in both.
**FRC AUC will not match to the last digit, and should not be expected to.**
Stage 1 runs parallel callbacks (`callback_serialize: false`) and stage 2
scatter-adds overlapping patches, so float accumulation order varies between
runs; the same config re-run gives answers differing by ~1e-6. Measured on an
A100 (2026-09-29):

| Run | Config | FRC AUC | e2e s |
|---|---|---|---|
| `202326` | derived | 0.587875 | 4.885 |
| `202445` | checked-in | 0.587873 | 4.969 |
| `202529` | derived | 0.587874 | 4.916 |

The derived config alone produced both `0.587875` and `0.587874`, so the spread
is **run-to-run non-determinism, not a config difference**. Judge with a
tolerance, not equality — `verify_against_upstream.py` uses `|dAUC| < 0.01`,
four orders of magnitude looser than the observed 2e-6 spread:

```shell
python verify_against_upstream.py --dataset W --model PS_W   # expect PASS
```

Throughput and E2E also vary run to run; compare medians, not single runs.

A config-level diff should show only the `systemflow:` provenance block and the
loss of comments — no runtime key differences:

```shell
cd ~/drava
diff <(python -c "
import sys; sys.path.insert(0,'examples/common')
from drava_common import load_pipeline_config as L
c=L('examples/ptychopinn/pipeline.yaml')
print([(s.name,s.runtime,s.ingress,s.egress) for s in c.stages])") \
     <(python -c "
import sys; sys.path.insert(0,'examples/common')
from drava_common import load_pipeline_config as L
c=L('.scratch/sf_pipeline.yaml')
print([(s.name,s.runtime,s.ingress,s.egress) for s in c.stages])")
```

No output means the runtime configuration is identical.

## Do not clobber pipeline.yaml

Do **not** run:

```shell
# DON'T
./drava-pipeline from-systemflow examples/ptychopinn/systemflow_model.yaml \
    -o examples/ptychopinn/pipeline.yaml --force
```

The generated file is semantically identical but **loses every comment**
(71 → 47 lines), including load-bearing ones such as *"REQUIRED … parallel
callbacks would race on that in-place accumulation"*. YAML dumpers cannot
round-trip comments.

`examples/ptychopinn/pipeline.yaml` stays the checked-in authoritative file;
`systemflow_model.yaml` is its documented source, and
`examples/common/tests/test_systemflow.py` asserts the two cannot drift apart.
Always generate to `.scratch/` (git-ignored) and point `DRAVA_STAGE_CONFIG` at
it.

## Installing SystemFlow is optional

Nothing above needs it. Install it only if you want to run SystemFlow's own
cost model (FLOPs, energy, latency estimates) alongside Drava:

```shell
cd ~
git clone git@github.com:wilkieolin/system_flow.git
cd system_flow
pip install -e .
python -c "from systemflow.io import load_model; print('systemflow OK')"
```

It pulls `numpy`, `scipy`, `pandas`, `networkx`, `openpyxl`, `pyyaml`. When
present, Drava reuses SystemFlow's YAML loader; when absent, it uses an
equivalent local one. **Never add `systemflow` to a `requirements.txt`** — the
importer must keep working without it.

The fitted PtychoPINN resource model (measured A100/H200/MI300X coefficients)
is then available directly:

```shell
python -c "
from systemflow.xrs_models import PtychoPINNResourceModel
m = PtychoPINNResourceModel.from_bundled_data()
e = m.predict(num_images=20449, resolution=(64, 64), gpu='A100')
print(f'predicted latency {e.latency_s:.3f} s, energy {e.energy_j:.1f} J, '
      f'avg power {e.avg_power_w:.1f} W')
"
```

Comparing that prediction against the measured `summary.csv` is the manual
precursor to the (not yet implemented) calibration feedback loop.

## Validating the energy half — enable NVML first

SystemFlow predicts **energy and power**, not just latency. Those predictions
are unverifiable unless the runtime was built with NVML: without it drava
reports CPU/RAPL energy only and omits every GPU energy field, so there is
nothing to compare against.

Check your build log. If it says:

```
-- NVML not found: building without GPU-energy reporting
```

then rebuild with NVML enabled — see
[examples/ptychopinn/JLSE.md](../examples/ptychopinn/JLSE.md#gpu-energy-nvml).
Short version (`NVML_ROOT` is a cmake cache variable, so `-D` is required on an
existing build tree):

```shell
export CUDA_HOME=$(dirname "$(dirname "$(command -v nvcc)")")
cd ~/drava/build
CC=clang CXX=clang++ cmake -DCMAKE_BUILD_TYPE=Debug -DNVML_ROOT=$CUDA_HOME ..
make -j
```

Expect `-- NVML GPU-energy backend enabled`.

### Reference numbers (A100, dataset W, 20449 groups, 64x64)

SystemFlow's shipped A100 coefficients predict, for that workload:

| Quantity | Predicted |
|---|---|
| compute latency | 1.591 s |
| io latency | 3.424 s |
| **total latency** | **5.015 s** |
| energy | 252.5 J |
| avg power | 50.3 W |

Measured drava `pipeline e2e` on 2026-09-29 was 4.885 / 4.969 / 4.916 s —
within **2 %** of the latency prediction. The energy figure is the one still
unvalidated; that is what an NVML build unlocks.

Note SystemFlow's split says this workload is **IO-dominated** (3.42 s io vs
1.59 s compute, 68 % io). That is a testable hypothesis, not a measurement: if
true, adding GPU threads will not help and transport/batching changes will.

> **Caveat when reproducing these numbers.** `PtychoPINNResourceModel.predict()`
> reads `s_per_gflop` and `io_slope_s_per_grouped` from the shipped CSVs, and
> both are rounded to the point of damage — `s_per_gflop` is `0.0` for A100,
> which zeroes the entire workload-dependent compute term and yields a constant
> 0.366 s regardless of sample count (total 4.43 s, −10 % error). The
> full-precision equivalents `ms_per_tflop_work` (35.8472) and
> `io_slope_us_per_grouped` (168.814) sit unused in the same files; the table
> above uses those. This is an upstream SystemFlow data issue — do not patch the
> SystemFlow checkout, report it.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: yaml` | `pip install pyyaml` — the only hard dependency |
| `IMPORT FAILED: ... pick one with --graph` | The document defines several graphs; pass `--graph NAME` |
| `IMPORT FAILED: ... unrecognized drava parameter` | Typo in a `"drava ..."` key; the error lists the valid ones |
| `IMPORT FAILED: ... fans out / fans in` | Graph is not a linear chain; a Drava stage takes exactly one ingress |
| `refusing to overwrite ...` | Intentional. Pass `--force`, but not onto `examples/ptychopinn/pipeline.yaml` |
| Run still uses the old config | `DRAVA_STAGE_CONFIG` must be an **absolute** path; check the `[run] stage config:` banner |
| `test_cli.py` 7/9 | Pre-existing, unrelated: stale `.scratch/tests_cli/scaf_*` dirs. Remove them and re-run |
