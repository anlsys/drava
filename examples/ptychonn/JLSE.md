# PtychoNN on JLSE

Commands only. Background and options: [README.md](README.md),
[../../docs/jlse.md](../../docs/jlse.md).

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
```

## 3. Build (only after a C/C++ change)

```shell
cd ~/drava/build && make -j
```

Re-run `cmake` only when changing compiler, Python, or `*_ROOT`:

```shell
CC=clang CXX=clang++ cmake -DCMAKE_BUILD_TYPE=Debug .. && make -j
```

## 4. One-time setup

```shell
cd ~/drava/examples/ptychonn
pip install -r requirements.txt
python download_partial.py      # -> PtychoNN_data_partial/ (~100 MB)
```

## 5. Run the benchmark

Starts NATS, both stages and the publisher; prints a table.

```shell
cd ~/drava/examples/ptychonn
python benchmark_two_stages.py \
  --batches 256 --runs 1 --num-frames 10000 \
  --threads 4 --timeout-ms 200 --rate-hz 1000 \
  --nats-url nats://127.0.0.1:4222
```

Reference (1x A100-PCIE-40GB): publisher ~1000 fps, stage1 ~918 fps,
stage2 ~653 fps, E2E ~9.7 s.

Results: `bench_logs_two_stages/<stamp>/summary.csv`

Send logs to scratch if `$HOME` is tight:

```shell
python benchmark_two_stages.py --out-dir /scratch/$USER/ptychonn_bench ...
```

## 6. Run manually (3 terminals)

```shell
cd ~/drava/examples/ptychonn
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml

DRAVA_STAGE_NAME=stage2 python app_stage2.py    # terminal 1
DRAVA_STAGE_NAME=stage1 python app.py           # terminal 2
python publisher_jetstream.py                   # terminal 3
```

Launch downstream-first. Stages do not exit on their own with the NATS
transport; `Ctrl-C` them after `[stage2-final]` appears.

## 7. Check the result

```shell
grep "\[stage2-final\]" <stage2 log>
```

`frames`, `stitched_frames` and the publisher's frame count must all match.

## 8. Disk

```shell
du -sh ~/drava/examples/ptychonn/* | sort -h
pgrep -af nats-server            # must be empty before deleting any store
```

| Path | Keep? |
|---|---|
| `bench_logs_two_stages/`, `tune_logs_*/` | delete after reading `summary.csv` |
| `jsdata/` (manual runs only) | delete |
| `PtychoNN_data_partial/` | keep, else re-download |
| `aggregate.csv` | **keep — tracked in git** |

The benchmark writes its JetStream store per run to
`bench_logs_two_stages/<stamp>/nats-store`, not to `jsdata/`; `jsdata/` only
appears if you start `nats-server -c nats.conf` by hand.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `import drava` fails | `export PYTHONPATH="$HOME/drava/build:$PYTHONPATH"` |
| `undefined symbol` on import | build used another Python; rebuild with `-DPython3_EXECUTABLE=$(which python)` |
| `Fetch error: Limit reached` | stage outlived the run; normal after `[stage2-final]` |
| Port 4222 in use | `pgrep -af nats-server`, or pass `--reuse-nats` |
| Disk quota exceeded | see §8; `export PIP_CACHE_DIR=/scratch/$USER/pipcache` |
