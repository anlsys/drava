#!/usr/bin/env python3
"""pvaPy HPC UserDataProcessor for the PtychoNN stage-2 (stitching) consumer.

This is the *supported* pvaPy way to scale a high-rate stream: instead of a
single low-level PvaServer overwrite record + client monitor (which drops
updates under load), stage 1 publishes to a distributor-enabled channel and
stage 2 runs as one or more ``pvapy-hpc-consumer`` processes that the pvAccess
data distributor (``pydistributor``) load-balances. With N consumers in a
distributor group and no distributor set specified, each update is routed to
exactly one client (a true partition), so the N consumers collectively receive
every stage-1 prediction without loss, provided their aggregate throughput keeps
up.

Each consumer accumulates the predictions in its partition and, on the EOS
marker, writes a small per-consumer result file:

    {out_dir}/hpc_stage2_result_c{consumerId}.json

recording how many unique predictions/frames it received. A separate aggregator
(in the benchmark) unions the per-consumer coverage to determine whether the
full scan was received loss-free and to perform the final stitch.

Usage (per consumer, launched by pvapy-hpc-consumer):

  pvapy-hpc-consumer \
    -ic ptychonn:stage1 \
    -nc <N> \
    -dpn pydistributor -dg ptychonn -du 1 \
    -of uniqueId \
    -pf pvapy_hpc_stage2_processor.py -pc PtychoNNStitchProcessor \
    -pa '{"out_dir": "hpc_logs/<ts>", "expected_frames": 3600}' \
    -rt <runtime_s>
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PTYCHONN_DIR = HERE.parent
if str(PTYCHONN_DIR) not in sys.path:
    sys.path.insert(0, str(PTYCHONN_DIR))

from pipeline_schema import decode_stage1_prediction  # noqa: E402
from pva_records import payload_bytes_from_pv, pv_field  # noqa: E402

try:
    from pvapy.hpc.userDataProcessor import UserDataProcessor
except Exception:  # pragma: no cover - only importable in the pvaPy env
    UserDataProcessor = object


def stitch_component(pred_patches_2d, tst_side=60, patch_size=64, point_size=3):
    """Overlap-add stitching identical to Drava's app_stage2.stitch_component."""
    overlap = 4 * point_size
    composite = np.zeros((tst_side * point_size + overlap,
                          tst_side * point_size + overlap), float)
    ctr = np.zeros_like(composite)
    data = pred_patches_2d.reshape(tst_side, tst_side, patch_size, patch_size)[
        :, :,
        patch_size // 2 - overlap // 2: patch_size // 2 + overlap // 2,
        patch_size // 2 - overlap // 2: patch_size // 2 + overlap // 2,
    ]
    for i in range(tst_side):
        for j in range(tst_side):
            r0, c0 = point_size * i, point_size * j
            composite[r0:r0 + overlap, c0:c0 + overlap] += data[i, j]
            ctr[r0:r0 + overlap, c0:c0 + overlap] += 1
    return (composite[overlap // 2:-overlap // 2, overlap // 2:-overlap // 2]
            / ctr[overlap // 2:-overlap // 2, overlap // 2:-overlap // 2])


class PtychoNNStitchProcessor(UserDataProcessor):
    """Per-consumer stage-2 processor: accumulate this consumer's partition of
    stage-1 predictions and, when the stream ends, emit a coverage result."""

    def __init__(self, configDict=None):
        configDict = configDict or {}
        try:
            super().__init__(configDict)
        except Exception:
            pass
        self.out_dir = Path(configDict.get("out_dir", "hpc_logs"))
        self.expected_frames = int(configDict.get("expected_frames", 0))
        self.save_arrays = bool(configDict.get("save_arrays", False))
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.received_index = set()      # global frame indices this consumer saw
        self.amp = {}                    # index -> 2D amp (only if save_arrays)
        self.phi = {}
        self.rx_msgs = 0
        self.rx_frames = 0
        self.n_total = 0
        self.t0 = None
        self.t_final = None
        self.finalized = False

    # UserDataProcessor hook: called on every distributed PV update.
    def process(self, pvObject):
        now = time.time()
        if self.t0 is None:
            self.t0 = now
        try:
            is_eos = bool(pv_field(pvObject, "eos"))
        except Exception:
            is_eos = False
        n_total = int(pv_field(pvObject, "nTotal") or 0)
        if n_total > self.n_total:
            self.n_total = n_total

        if is_eos:
            self._finalize()
            return pvObject

        payload = payload_bytes_from_pv(pvObject)
        item = decode_stage1_prediction(payload)
        start, end = item["start"], item["end"]
        self.rx_msgs += 1
        for k, idx in enumerate(range(start, end)):
            if idx not in self.received_index:
                self.received_index.add(idx)
                self.rx_frames += 1
                if self.save_arrays:
                    self.amp[idx] = item["pred_amp"][k]
                    self.phi[idx] = item["pred_phi"][k]
        return pvObject

    def _finalize(self):
        if self.finalized:
            return
        self.finalized = True
        self.t_final = time.time()
        cid = getattr(self, "processorId", os.getpid())
        result = {
            "consumer_id": cid,
            "rx_msgs": self.rx_msgs,
            "rx_frames": self.rx_frames,
            "n_total": self.n_total or self.expected_frames,
            "received_index": sorted(self.received_index),
            "t0": self.t0,
            "t_final": self.t_final,
            "elapsed_s": (self.t_final - self.t0) if self.t0 else 0.0,
        }
        out = self.out_dir / f"hpc_stage2_result_c{cid}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(result, f)
        if self.save_arrays:
            np.savez_compressed(
                self.out_dir / f"hpc_stage2_arrays_c{cid}.npz",
                index=np.array(sorted(self.amp.keys())),
                amp=np.stack([self.amp[i] for i in sorted(self.amp)]) if self.amp else np.empty((0,)),
                phi=np.stack([self.phi[i] for i in sorted(self.phi)]) if self.phi else np.empty((0,)),
            )
        print(f"[hpc-stage2] consumer {cid} finalized: rx_msgs={self.rx_msgs} "
              f"rx_frames={self.rx_frames} n_total={self.n_total}", flush=True)

    # Called by the framework at shutdown; ensure a result is written even if
    # the EOS update was routed to a different consumer.
    def stop(self):
        self._finalize()
        try:
            return super().stop()
        except Exception:
            return {}

    def getStats(self):
        return {"rxMsgs": self.rx_msgs, "rxFrames": self.rx_frames}

    def getStatsPvaTypes(self):
        # Declares the PVA types for the stats fields published on the status
        # channel; must match the keys returned by getStats().
        try:
            import pvaccess as pva
            return {"rxMsgs": pva.UINT, "rxFrames": pva.UINT}
        except Exception:
            return {}
