"""Fetch the published PtychoPINN artifacts from Zenodo.

Record: https://doi.org/10.5281/zenodo.16968020
Files:  data.tar.gz   -- Ptychodus-formatted experimental datasets
        mlruns.tar.gz -- MLflow runs holding the trained model artifacts

The upstream repo has no downloader (its ``initialize_data.py`` only rewrites
MLflow artifact URIs), so this script fills that gap. It resolves the real file
URLs through the Zenodo REST API instead of hardcoding them, verifies the MD5
checksums Zenodo publishes, and optionally unpacks in place.

Usage::

    python download_zenodo.py                 # download + verify + extract
    python download_zenodo.py --list          # just show what is in the record
    python download_zenodo.py --no-extract
    python download_zenodo.py --dest /scratch/ptychopinn
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

import config as cfg

ZENODO_RECORD_ID = "16968020"
ZENODO_API = f"https://zenodo.org/api/records/{ZENODO_RECORD_ID}"
DEFAULT_FILES = ("data.tar.gz", "mlruns.tar.gz")
CHUNK = 1 << 20


def fetch_record() -> dict:
    req = urllib.request.Request(ZENODO_API, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Could not reach Zenodo ({exc}).\n"
            "On a JLSE login node you may need the proxy, e.g.:\n"
            "    export https_proxy=http://proxy.ftm.alcf.anl.gov:3128"
        ) from exc


def record_files(record: dict) -> dict[str, dict]:
    out = {}
    for entry in record.get("files", []):
        key = entry.get("key") or entry.get("filename")
        link = (entry.get("links") or {}).get("self") or entry.get("links", {}).get("download")
        if not key or not link:
            continue
        out[key] = {
            "url": link,
            "size": int(entry.get("size", 0)),
            "checksum": entry.get("checksum", ""),
        }
    return out


def human(n: int) -> str:
    step = 1024.0
    value = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < step:
            return f"{value:.1f} {unit}"
        value /= step
    return f"{value:.1f} PiB"


def md5_of(path: Path) -> str:
    digest = hashlib.md5()  # noqa: S324 - Zenodo publishes md5, not our choice
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(path: Path, checksum: str) -> bool:
    if not checksum:
        return True
    algo, _, expected = checksum.partition(":")
    if algo != "md5":
        print(f"  ! unsupported checksum algorithm {algo!r}, skipping verification")
        return True
    actual = md5_of(path)
    if actual != expected:
        print(f"  ! checksum mismatch: expected {expected}, got {actual}")
        return False
    print("  checksum ok")
    return True


def download(url: str, dest: Path, size: int) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"  downloading {human(size)} -> {dest}")
    with urllib.request.urlopen(url, timeout=120) as resp, tmp.open("wb") as out:
        done = 0
        last_pct = -1
        while True:
            block = resp.read(CHUNK)
            if not block:
                break
            out.write(block)
            done += len(block)
            if size:
                pct = int(done * 100 / size)
                if pct != last_pct and pct % 5 == 0:
                    print(f"    {pct:3d}%  {human(done)}", flush=True)
                    last_pct = pct
    tmp.replace(dest)


def extract(archive: Path, dest: Path) -> None:
    print(f"  extracting {archive.name} -> {dest}")
    with tarfile.open(archive, "r:gz") as tar:
        # Python 3.12+ understands the safe extraction filter; older versions
        # silently ignore the kwarg, so guard it.
        try:
            tar.extractall(dest, filter="data")
        except TypeError:
            tar.extractall(dest)  # noqa: S202


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dest", default=str(cfg.DATA_ROOT),
                        help="destination directory (default: %(default)s)")
    parser.add_argument("--files", nargs="*", default=list(DEFAULT_FILES),
                        help="file names to fetch (default: %(default)s)")
    parser.add_argument("--list", action="store_true",
                        help="list the record's files and exit")
    parser.add_argument("--no-extract", action="store_true",
                        help="download only, do not unpack")
    parser.add_argument("--keep-archives", action="store_true",
                        help="keep the .tar.gz files after extracting")
    parser.add_argument("--force", action="store_true",
                        help="re-download even if the file is already present")
    args = parser.parse_args()

    record = fetch_record()
    available = record_files(record)

    title = (record.get("metadata") or {}).get("title", "<untitled>")
    print(f"Zenodo record {ZENODO_RECORD_ID}: {title}")

    if args.list or not available:
        for name, info in sorted(available.items()):
            print(f"  {name:24s} {human(info['size']):>12s}  {info['checksum']}")
        if not available:
            print("  (no files reported; the record may be restricted)")
        return 0

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)

    missing = [f for f in args.files if f not in available]
    if missing:
        print(f"Not in the record: {', '.join(missing)}")
        print(f"Available: {', '.join(sorted(available))}")
        return 1

    for name in args.files:
        info = available[name]
        archive = dest / name
        print(f"\n{name}")

        if archive.exists() and not args.force:
            print("  already present")
        else:
            download(info["url"], archive, info["size"])

        if not verify(archive, info["checksum"]):
            print("  re-run with --force to download again")
            return 1

        if not args.no_extract:
            extract(archive, dest)
            if not args.keep_archives:
                archive.unlink()
                print(f"  removed {archive.name}")

    print(f"\nDone. Data root: {dest}")
    print("Expected layout:")
    print(f"  {dest}/data/<DATASET>/*.npz")
    print(f"  {dest}/mlruns/<experiment_id>/<run_id>/artifacts/model/")
    if shutil.which("python"):
        print("\nNext: rewrite the MLflow artifact URIs to this location, using")
        print("upstream's own script from the PtychoPINN-torch-pub checkout:")
        print(f"    python initialize_data.py --repo-root {dest} --no-dry-run")
        print("then:")
        print("    python prepare_dataset.py --dataset W --model PS_W")
    return 0


if __name__ == "__main__":
    sys.exit(main())
