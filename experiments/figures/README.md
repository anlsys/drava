# Experiment Figure Packages

Each subdirectory keeps the plotting script, plot input data, and generated
PDF/PNG output for one paper experiment. This keeps generated figures out of
the repository root and makes reruns predictable.

Final submitted copies are collected separately in `../../docs/figures/paper_figs/`.

| Package | Purpose |
|---|---|
| `sc5_bare_runtime_ceiling/` | Runtime message-rate ceiling figure |
| `pvapy_drava_comparison/` | PvaPy versus Drava baseline comparison |
| `manual_config/` | Manual PtychoNN throughput-latency trade-off |
| `exp1_runtime_observability/` | Runtime-observability diagnostic figure |
| `agentic_config_search/` | Agentic/Ytopt search figures |
| `tomogan_energy/` | TomoGAN GPU energy-efficiency figure |
