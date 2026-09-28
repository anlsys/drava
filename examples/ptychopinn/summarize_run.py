"""Summarise a PtychoPINN pipeline run: timings, throughput, and the FRC.

Reads the file-based metrics the runtime and publisher emit (never scraped
stdout, per the repo's metrics convention) plus the terminal stage's own
`[stage2-final]` line, prints a console table, and writes summary.csv in the
same spirit as ptychonn's benchmark driver.

Usage::

    python summarize_run.py                      # newest run_logs/* directory
    python summarize_run.py run_logs/20260928_150551
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import config as cfg

STAGE2_FINAL_RE = re.compile(
    r"\[stage2-final\]\s+frames=(?P<frames>\d+)\s+groups=(?P<groups>\d+)\s+"
    r"expected_groups=(?P<expected_groups>\d+)\s+duplicates=(?P<duplicates>\d+)\s+"
    r"canvas_side=(?P<canvas_side>\d+)\s+window=(?P<window>\d+)\s+"
    r"recon_shape=(?P<recon_shape>\d+x\d+)\s+gt_shape=(?P<gt_shape>\S+)\s+"
    r"status=(?P<status>\w+)\s+nan_px_crop=(?P<nan_px_crop>\d+)\s+"
    r"nan_px_canvas=(?P<nan_px_canvas>\d+)\s+frc_auc=(?P<frc_auc>\S+)"
)


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _read_metrics(path: Path, stage: str, reason: str = "rx_eos"):
    """Last JSONL record matching stage/reason. Unknown keys are ignored."""
    found = None
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("stage") == stage and rec.get("reason") == reason:
                found = rec
    except OSError:
        return None
    return found


def _read_stage2_final(path: Path):
    try:
        for line in reversed(path.read_text(encoding="utf-8",
                                            errors="replace").splitlines()):
            m = STAGE2_FINAL_RE.search(line)
            if m:
                return m.groupdict()
    except OSError:
        pass
    return None


def _fmt(value, spec="{:.3f}", na="n/a"):
    if value is None:
        return na
    try:
        return spec.format(float(value))
    except (TypeError, ValueError):
        return str(value)


def _newest_run_dir() -> Path | None:
    root = cfg.EXAMPLE_DIR / "run_logs"
    if not root.is_dir():
        return None
    runs = sorted((d for d in root.iterdir() if d.is_dir()), key=lambda d: d.name)
    return runs[-1] if runs else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", nargs="?", default=None,
                        help="run directory (default: newest under run_logs/)")
    parser.add_argument("--no-csv", action="store_true",
                        help="print the table but do not write summary.csv")
    args = parser.parse_args()

    run_dir = Path(args.run_dir) if args.run_dir else _newest_run_dir()
    if run_dir is None or not run_dir.is_dir():
        print("No run directory found. Run ./run_two_stages.sh first.",
              file=sys.stderr)
        return 1

    meta = _read_json(cfg.META_FILE) or {}
    pub = _read_json(run_dir / "pub_metrics.json")
    s1 = _read_metrics(run_dir / "metrics_stage1.jsonl", "stage1")
    s2 = _read_metrics(run_dir / "metrics_stage2.jsonl", "stage2")
    final = _read_stage2_final(run_dir / "app_stage2.log")
    timing = _read_json(run_dir / "timing.json") or {}

    e2e = None
    if timing.get("t_final") and timing.get("t_pub_start"):
        e2e = float(timing["t_final"]) - float(timing["t_pub_start"])
    wall = None
    if timing.get("t_final") and timing.get("t_script_start"):
        wall = float(timing["t_final"]) - float(timing["t_script_start"])

    bar = "=" * 66
    sub = "-" * 66
    print()
    print(bar)
    print(f" PtychoPINN run summary   {run_dir.name}")
    print(bar)
    print(f" dataset / model     {meta.get('dataset', '?')} / {meta.get('model_key', '?')}"
          f"   run_id={str(meta.get('run_id', '?'))[:12]}...")
    print(f" grouping seed       {meta.get('grouping_seed', 'n/a')}"
          f"   n_groups={meta.get('n_groups', '?')}")
    if final:
        print(f" status              {final['status']}"
              f"   groups={final['groups']}/{final['expected_groups']}"
              f"   duplicates={final['duplicates']}")
    print(sub)
    # stage1 receives one item per group; stage2 receives one item per stage1
    # message, each carrying many groups. Label the unit so the counts are not
    # mistaken for a mismatch.
    print(f" {'stage':<11}{'rx_items':>10}{'time_s':>10}{'items/s':>12}  unit")
    if pub:
        print(f" {'publisher':<11}{int(pub.get('frames', 0)):>10}"
              f"{_fmt(pub.get('duration_s')):>10}"
              f"{_fmt(pub.get('avg_fps'), '{:.1f}'):>12}  groups")
    if s1:
        print(f" {'stage1':<11}{int(s1.get('rx_items', 0)):>10}"
              f"{_fmt(s1.get('stage_total_s')):>10}"
              f"{_fmt(s1.get('stage_total_fps'), '{:.1f}'):>12}  groups")
    if s2:
        note = "messages"
        if final:
            note = f"messages ({final['groups']} groups)"
        print(f" {'stage2':<11}{int(s2.get('rx_items', 0)):>10}"
              f"{_fmt(s2.get('stage_total_s')):>10}"
              f"{_fmt(s2.get('stage_total_fps'), '{:.1f}'):>12}  {note}")
    print(sub)
    if s1:
        print(f" stage1 compute      {_fmt(s1.get('compute_total_s'))} s"
              f"   (callback avg {_fmt(s1.get('cb_avg_ms'), '{:.1f}')} ms,"
              f" publish {_fmt(s1.get('publish_total_s'))} s)")
    if s2:
        print(f" stage2 compute      {_fmt(s2.get('compute_total_s'))} s"
              f"   (callback avg {_fmt(s2.get('cb_avg_ms'), '{:.1f}')} ms)")
    if e2e is not None:
        print(f" pipeline e2e        {_fmt(e2e)} s"
              "   (publisher start -> stage2 finalize)")
    if wall is not None:
        print(f" total wall clock    {_fmt(wall)} s   (includes startup)")
    print(sub)
    if final:
        print(f" FRC AUC (0..{cfg.FRC_AUC_CUTOFF})    {final['frc_auc']}")
        print(f" canvas {final['canvas_side']}x{final['canvas_side']}"
              f"   crop {final['recon_shape']}"
              f"   window {final['window']}"
              f"   nan_px_crop={final['nan_px_crop']}")
        if final["status"] != "complete":
            print(f" NOTE: status={final['status']}, so this FRC is NOT"
                  " comparable to the paper.")
        elif int(final["nan_px_crop"]) != 0:
            print(" NOTE: NaNs inside the evaluated crop; FRC is unreliable.")
    else:
        print(" FRC                 n/a (no [stage2-final] line found)")
    print(bar)

    # Frame accounting: every count must agree or the result is not a result.
    counts = {
        "publisher": int(pub["frames"]) if pub else None,
        "stage1_rx": int(s1["rx_items"]) if s1 else None,
        "stage2_groups": int(final["groups"]) if final else None,
    }
    present = [v for v in counts.values() if v is not None]
    if len(present) >= 2 and len(set(present)) != 1:
        print(" FRAME ACCOUNTING MISMATCH: "
              + ", ".join(f"{k}={v}" for k, v in counts.items() if v is not None))
        print(" Messages were dropped; treat this run as invalid.")
        print(bar)
    elif present:
        print(f" frame accounting OK ({present[0]} through every stage)")
        print(bar)
    print()

    if not args.no_csv:
        row = {
            "run": run_dir.name,
            "dataset": meta.get("dataset"),
            "model": meta.get("model_key"),
            "run_id": meta.get("run_id"),
            "grouping_seed": meta.get("grouping_seed"),
            "n_groups": meta.get("n_groups"),
            "status": final["status"] if final else None,
            "duplicates": final["duplicates"] if final else None,
            "publisher_frames": counts["publisher"],
            "publisher_time_s": pub.get("duration_s") if pub else None,
            "publisher_avg_fps": pub.get("avg_fps") if pub else None,
            "stage1_total_s": s1.get("stage_total_s") if s1 else None,
            "stage1_total_fps": s1.get("stage_total_fps") if s1 else None,
            "stage1_compute_s": s1.get("compute_total_s") if s1 else None,
            "stage2_total_s": s2.get("stage_total_s") if s2 else None,
            "stage2_total_fps": s2.get("stage_total_fps") if s2 else None,
            "stage2_compute_s": s2.get("compute_total_s") if s2 else None,
            "pipeline_e2e_s": e2e,
            "wall_clock_s": wall,
            "canvas_side": final["canvas_side"] if final else None,
            "nan_px_crop": final["nan_px_crop"] if final else None,
            "frc_auc": final["frc_auc"] if final else None,
        }
        out = run_dir / "summary.csv"
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(row))
            w.writeheader()
            w.writerow(row)
        print(f"wrote {out}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
