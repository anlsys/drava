# Drava Experiments

This directory contains the experiment drivers, preserved outputs, and
figure-generation packages used for the Drava paper. The short version:

- `exp1_runtime_overhead.py` and `sc5_bare_runtime_ceiling.py` are active
  top-level drivers.
- `figures/` contains reproducible figure packages: plotting script, input CSV
  or embedded data, and generated PDF/PNG output.
- `logs/` contains captured command output and copied terminal logs from the
  paper runs.
- `results/` contains checked-in result CSVs that are still useful for
  regenerating figures.
- `archive/` preserves older exploratory scripts, prototype agent code, and
  rough figures without presenting them as the current workflow.

For the submitted-paper experiment map, start with `../experiments.md`.

## Active Drivers

### Observability-Guided Runtime Tuning

`exp1_runtime_overhead.py` sweeps callback batch size for the PtychoNN pipeline
and records the latency decomposition used by the observability figure.

```bash
python experiments/exp1_runtime_overhead.py \
    --workload ptychonn \
    --runs 1 \
    --ptychonn-num-frames 10000
```

The checked-in result used by the paper figure is:

```text
experiments/results/exp1_20260513_205018/exp1_summary.csv
```

Regenerate the figure:

```bash
python experiments/figures/exp1_runtime_observability/plot_exp1_runtime_observability.py \
    experiments/results/exp1_20260513_205018/exp1_summary.csv
```

### Runtime Message-Rate Ceiling

`sc5_bare_runtime_ceiling.py` removes dataset loading and model inference while
preserving the normal publisher, JetStream, Drava listen/callback, EOS, and
metrics cycle. Use it to characterize the runtime message-rate ceiling.

```bash
python experiments/sc5_bare_runtime_ceiling.py \
    --batches 8,32,128,256,512 \
    --thread-list 2,4,8 \
    --payload-bytes 1 \
    --gpu-backend none \
    --kernel-launches 0 \
    --num-frames 100000 \
    --runs 1
```

Useful variants:

```bash
# Blank GPU kernel path.
python experiments/sc5_bare_runtime_ceiling.py --gpu-backend cupy --kernel-launches 1 --runs 1

# Exercise egress by publishing one cached output payload per input.
python experiments/sc5_bare_runtime_ceiling.py --publish-mode one_per_frame --runs 1
```

Outputs land under:

```text
experiments/results/sc5_bare_runtime_ceiling_<timestamp>/
```

## Figure Packages

Each package is intentionally self-contained so it can be rerun without
searching through examples:

| Experiment | Package | Main command |
|---|---|---|
| Runtime ceiling | `figures/sc5_bare_runtime_ceiling/` | `python experiments/figures/sc5_bare_runtime_ceiling/plot_bare_runtime_ceiling.py` |
| PvaPy comparison | `figures/pvapy_drava_comparison/` | `python experiments/figures/pvapy_drava_comparison/plot_pvapy_drava_ptychonn.py` |
| Manual configuration | `figures/manual_config/` | `python experiments/figures/manual_config/plot_manual_config.py` |
| Runtime observability | `figures/exp1_runtime_observability/` | `python experiments/figures/exp1_runtime_observability/plot_exp1_runtime_observability.py experiments/results/exp1_20260513_205018/exp1_summary.csv` |
| Agentic search | `figures/agentic_config_search/` | `python experiments/figures/agentic_config_search/plot_agentic_search.py <aggregate.csv>` |
| TomoGAN energy | `figures/tomogan_energy/` | `python experiments/figures/tomogan_energy/plot_tomogan_energy_efficiency.py` |

Final paper-ready copies are in `../figs/paper_figs/`.

## Logs

`logs/` consolidates the paper-run terminal logs that used to be scattered
under the example applications. They are evidence and debugging records, not
the preferred place to run from.

| Log | Purpose |
|---|---|
| `logs/sc5_bare_runtime_ceiling.md` | Bare-runtime ceiling runs |
| `logs/pvapy_drava_comparison.md` | PvaPy and Drava baseline comparison |
| `logs/manual_config_throughput_latency.md` | Manual PtychoNN configuration rows |
| `logs/exp1_runtime_observability.md` | Observability-guided runtime tuning |
| `logs/agentic_config_search.md` | Ytopt/agentic configuration search |
| `logs/tomogan_energy.md` | TomoGAN GPU energy run evidence |
| `logs/tomogan_baseline.md` | TomoGAN functional/benchmark run evidence |
| `logs/archive/` | Older rough tuning and callback/inference logs |

## Archive

`archive/rough/` preserves older decomposition and SC-draft drivers that may
still be useful for reviewer follow-up experiments. `archive/ptychonn_agents_old/`
preserves an older agent prototype and its generated figures.

Nothing in `archive/` is deleted or invalidated; the folder just marks those
files as historical rather than part of the current paper workflow.
