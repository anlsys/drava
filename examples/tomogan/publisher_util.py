import os
from pathlib import Path
import numpy as np
import h5py
import yaml

from config import DATASET_PATH, TEST_INPUT_KEY


def _parse_yaml_scalar(path: Path, section: str, key_name: str):
    if not path.exists():
        return None
    in_section = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if indent == 0 and body == f"{section}:":
            in_section = True
            continue
        if indent == 0 and body.endswith(":") and body != f"{section}:":
            in_section = False
            continue
        if in_section and indent >= 2 and ":" in body:
            key, value = body.split(":", 1)
            if key.strip() == key_name:
                return value.strip().strip("\"'")
    return None


def _load_yaml_config(path: Path | None):
    if path is None or not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def load_transport_config():
    cfg_path = os.getenv("DRAVA_STAGE_CONFIG", "")
    cfg = _load_yaml_config(Path(cfg_path)) if cfg_path else {}
    transport = cfg.get("transport", {})
    if not isinstance(transport, dict):
        transport = {}

    stages = cfg.get("stages", [])
    stage1_ingress = {}
    if isinstance(stages, list):
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            if stage.get("name") != "stage1":
                continue
            ingress = stage.get("ingress", {})
            if isinstance(ingress, dict):
                stage1_ingress = ingress
            break

    nats_url = os.getenv(
        "NATS_URL",
        str(transport.get("nats_url", "nats://0.0.0.0:4222")),
    )
    stream = os.getenv(
        "DRAVA_STREAM",
        str(stage1_ingress.get("stream", "FRAMES")),
    )
    subject = os.getenv(
        "DRAVA_SUBJECT",
        str(stage1_ingress.get("subject", "frames.raw")),
    )
    return nats_url, stream, subject


def load_publish_config():
    cfg_path = os.getenv("DRAVA_STAGE_CONFIG", "")
    cfg = Path(cfg_path) if cfg_path else None

    yaml_rate = _parse_yaml_scalar(cfg, "publisher", "rate_hz") if cfg else None
    yaml_num_frames = _parse_yaml_scalar(cfg, "publisher", "num_frames") if cfg else None

    rate_hz = float(os.getenv("DRAVA_PUBLISH_RATE_HZ", yaml_rate or "0"))
    num_frames_default = yaml_num_frames or ""
    if not num_frames_default and DATASET_PATH.exists():
        with h5py.File(DATASET_PATH, "r") as h5fd:
            num_frames_default = str(int(h5fd[TEST_INPUT_KEY].shape[0]))

    num_frames = int(os.getenv("DRAVA_PUBLISH_NUM_FRAMES", num_frames_default))
    print(
        f"DRAVA_PUBLISH_RATE_HZ: {rate_hz},"
        f" DRAVA_PUBLISH_NUM_FRAMES: {num_frames}"
    )
    return rate_hz, num_frames


def load_dataset_payloads():
    if not DATASET_PATH.exists():
        raise RuntimeError(f"TomoGAN dataset not found: {DATASET_PATH}")
    with h5py.File(DATASET_PATH, "r") as h5fd:
        frames = h5fd[TEST_INPUT_KEY][:].astype(np.float32)
    payloads = [frame.tobytes(order="C") for frame in frames]
    if not payloads:
        raise RuntimeError(f"No frames found in dataset {DATASET_PATH}:{TEST_INPUT_KEY}")
    return payloads
