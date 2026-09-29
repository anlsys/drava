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

Compare the two `run_logs/<stamp>/summary.csv` files. FRC AUC and
`nan_px_crop` must match exactly; throughput/E2E will vary run to run.

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
