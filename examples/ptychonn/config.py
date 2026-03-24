import os


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


DATA_DIR = os.getenv("PTYCHONN_DATA_DIR", "PtychoNN_data_partial")
WT_DIR = f"{DATA_DIR}/wts4"

PATCH_SIDE = _get_int("DRAVA_PATCH_SIDE", 64)
TOTAL_FRAMES = _get_int("DRAVA_TOTAL_FRAMES", 3600)
DRAVA_INFER_BATCH = _get_int("DRAVA_INFER_BATCH", 128)
LOG_EVERY = _get_int("DRAVA_LOG_EVERY", DRAVA_INFER_BATCH)

STAGE1_JOB_ID = _get_int("DRAVA_STAGE1_JOB_ID", 1)
STAGE2_SCAN_SIDE = _get_int("DRAVA_STAGE2_SCAN_SIDE", 60)
