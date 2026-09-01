"""One place that reads and validates a Drava ``pipeline.yaml``.

Previously the same schema was parsed three different ways (yaml-cpp in the
runtime, a hand-rolled indent parser in ``publisher_util.py``, and *another*
hand-rolled parser in ``benchmark_two_stages.py``). This module is the single
Python reader: it uses PyYAML when available and degrades to a tiny built-in
scalar parser otherwise, so examples do not hard-depend on PyYAML.

The runtime itself (C++) remains authoritative and reads the same YAML via
yaml-cpp; this module intentionally mirrors that schema and never invents new
runtime behavior.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:  # PyYAML is preferred; fall back to a minimal parser when it is absent.
    import yaml  # type: ignore

    _HAVE_YAML = True
except ImportError:  # pragma: no cover - exercised only in yaml-less envs
    yaml = None  # type: ignore
    _HAVE_YAML = False


class PipelineConfigError(Exception):
    """Raised when a pipeline.yaml is missing, malformed, or mis-wired."""


# --------------------------------------------------------------------------- #
# YAML loading (PyYAML with a minimal fallback)
# --------------------------------------------------------------------------- #
def load_yaml(path: Path | str) -> dict:
    """Load a YAML mapping from ``path``.

    Uses PyYAML if installed; otherwise a small fallback parser that supports
    the subset of YAML the Drava schema uses (nested maps, ``- name:`` list
    items, scalar values, ``#`` comments). Always returns a dict.
    """
    p = Path(path)
    if not p.exists():
        raise PipelineConfigError(f"pipeline config not found: {p}")
    text = p.read_text(encoding="utf-8")
    if _HAVE_YAML:
        data = yaml.safe_load(text) or {}
    else:  # pragma: no cover - only when PyYAML missing
        data = _fallback_parse(text)
    if not isinstance(data, dict):
        raise PipelineConfigError(f"top-level YAML must be a mapping: {p}")
    return data


def _coerce_scalar(value: str) -> Any:
    v = value.strip()
    if v == "" or v in ("~", "null", "None"):
        return None
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    if (v[0] == v[-1]) and v[0] in ("'", '"') and len(v) >= 2:
        return v[1:-1]
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def _fallback_parse(text: str) -> dict:  # pragma: no cover - simple indent parser
    """Minimal YAML subset parser used only when PyYAML is unavailable.

    Handles the Drava pipeline schema: top-level maps, one level of nested
    maps, and a ``stages:`` list whose items start with ``- name: ...``.
    """
    root: dict = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    cur_list: Optional[list] = None
    cur_list_indent = -1

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()

        # List item (only used for `stages:`)
        if body.startswith("- "):
            item: dict = {}
            if cur_list is None or indent <= cur_list_indent:
                # find the most recent key expecting a list
                pass
            if cur_list is not None:
                cur_list.append(item)
                stack = [s for s in stack if s[0] < indent]
                stack.append((indent, item))
                kv = body[2:]
                if ":" in kv:
                    k, v = kv.split(":", 1)
                    item[k.strip()] = _coerce_scalar(v) if v.strip() else {}
            continue

        # Pop to parent by indent
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]

        key, _, val = body.partition(":")
        key = key.strip()
        val = val.strip()
        if val == "":
            # Could be a nested map or a list
            child: Any = {}
            parent[key] = child
            stack.append((indent, child))
            if key == "stages":
                cur_list = []
                parent[key] = cur_list
                cur_list_indent = indent
        else:
            parent[key] = _coerce_scalar(val)
    return root


# --------------------------------------------------------------------------- #
# Typed view of a pipeline.yaml
# --------------------------------------------------------------------------- #
@dataclass
class StageConfig:
    """One ``stages:`` entry from a ``pipeline.yaml``.

    The ``runtime``, ``ingress``, ``egress``, and ``metrics`` sections are kept
    as raw dicts so unknown keys are preserved.
    """

    name: str                                    #: Stage name (e.g. ``"stage1"``).
    runtime: dict = field(default_factory=dict)  #: ``runtime:`` block (threads, batching).
    ingress: dict = field(default_factory=dict)  #: ``ingress:`` block (input stream/subject).
    egress: dict = field(default_factory=dict)   #: ``egress:`` block (output stream/subject, forward_eos).
    metrics: dict = field(default_factory=dict)  #: ``metrics:`` block (output_path).

    @property
    def threads(self) -> Optional[int]:
        """Worker thread count (``runtime.threads``), or None if unset."""
        return self.runtime.get("threads")

    @property
    def callback_batch(self) -> Optional[int]:
        """Callback batch size (``runtime.callback_batch``), or None if unset."""
        return self.runtime.get("callback_batch")


@dataclass
class PipelineConfig:
    """A parsed, normalized ``pipeline.yaml``.

    Returned by :func:`load_pipeline_config`. ``raw`` holds the full parsed
    mapping; the other fields are convenience views over it.
    """

    path: Path                    #: Path the config was loaded from.
    raw: dict                     #: The full parsed YAML mapping.
    name: str                     #: Pipeline name (``pipeline.name``).
    transport_type: str           #: Transport backend (``transport.type``: ``nats``/``socket``).
    nats_url: str                 #: NATS URL (``transport.nats_url``).
    stages: list[StageConfig]     #: Stages in declaration order.

    def stage(self, name: str) -> StageConfig:
        """Return the stage named ``name``, or raise :class:`PipelineConfigError`."""
        for s in self.stages:
            if s.name == name:
                return s
        raise PipelineConfigError(
            f"stage '{name}' not found in {self.path} "
            f"(have: {', '.join(s.name for s in self.stages) or 'none'})"
        )

    @property
    def stage_names(self) -> list[str]:
        """Stage names in declaration order."""
        return [s.name for s in self.stages]


def load_pipeline_config(path: Path | str | None = None) -> PipelineConfig:
    """Load and normalize a pipeline.yaml into a :class:`PipelineConfig`.

    If ``path`` is None, uses ``$DRAVA_STAGE_CONFIG`` (the same env var the
    runtime reads). Raises :exc:`PipelineConfigError` on missing/invalid config.
    """
    if path is None:
        env_path = os.getenv("DRAVA_STAGE_CONFIG", "")
        if not env_path:
            raise PipelineConfigError(
                "no pipeline config path given and DRAVA_STAGE_CONFIG is unset"
            )
        path = env_path
    path = Path(path)
    raw = load_yaml(path)

    pipeline = raw.get("pipeline", {}) or {}
    transport = raw.get("transport", {}) or {}
    if not isinstance(transport, dict):
        transport = {}

    raw_stages = raw.get("stages", []) or []
    if not isinstance(raw_stages, list):
        raise PipelineConfigError(f"'stages' must be a list in {path}")

    stages: list[StageConfig] = []
    for entry in raw_stages:
        if not isinstance(entry, dict) or "name" not in entry:
            raise PipelineConfigError(
                f"each stage needs a 'name' in {path}; got: {entry!r}"
            )
        stages.append(
            StageConfig(
                name=str(entry["name"]),
                runtime=dict(entry.get("runtime", {}) or {}),
                ingress=dict(entry.get("ingress", {}) or {}),
                egress=dict(entry.get("egress", {}) or {}),
                metrics=dict(entry.get("metrics", {}) or {}),
            )
        )

    return PipelineConfig(
        path=path,
        raw=raw,
        name=str(pipeline.get("name", path.stem)),
        transport_type=str(transport.get("type", "socket")),
        nats_url=str(transport.get("nats_url", "nats://127.0.0.1:4222")),
        stages=stages,
    )


# --------------------------------------------------------------------------- #
# Wiring validation
# --------------------------------------------------------------------------- #
def validate_pipeline(cfg: PipelineConfig) -> list[str]:
    """Check that a pipeline is internally consistent and return warnings.

    Errors (raise :exc:`PipelineConfigError`):
    - no stages;
    - duplicate stage names;
    - for NATS transport, a non-terminal stage whose egress stream/subject does
      not match the next stage's ingress stream/subject (the classic "nothing is
      flowing" typo).

    Warnings (returned, not raised):
    - a non-terminal stage with ``egress.forward_eos: false`` (downstream will
      never see end-of-stream);
    - a stage missing ingress stream/subject on NATS transport.
    """
    if not cfg.stages:
        raise PipelineConfigError(f"{cfg.path}: pipeline has no stages")

    seen: set[str] = set()
    for s in cfg.stages:
        if s.name in seen:
            raise PipelineConfigError(f"{cfg.path}: duplicate stage name '{s.name}'")
        seen.add(s.name)

    warnings: list[str] = []
    is_nats = cfg.transport_type == "nats"

    for i, s in enumerate(cfg.stages):
        is_last = i == len(cfg.stages) - 1

        if is_nats and not is_last:
            nxt = cfg.stages[i + 1]
            e_stream = s.egress.get("stream")
            e_subject = s.egress.get("subject")
            i_stream = nxt.ingress.get("stream")
            i_subject = nxt.ingress.get("subject")
            if e_stream is None or e_subject is None:
                raise PipelineConfigError(
                    f"{cfg.path}: stage '{s.name}' is not terminal but has no "
                    f"egress.stream/egress.subject to feed '{nxt.name}'"
                )
            if (e_stream, e_subject) != (i_stream, i_subject):
                raise PipelineConfigError(
                    f"{cfg.path}: broken wiring between '{s.name}' and "
                    f"'{nxt.name}': egress ({e_stream}/{e_subject}) != ingress "
                    f"({i_stream}/{i_subject}). They must match for data to flow."
                )
            if s.egress.get("forward_eos") is False:
                warnings.append(
                    f"stage '{s.name}' has forward_eos:false but is not terminal; "
                    f"'{nxt.name}' will never receive end-of-stream."
                )

        if is_nats and (not s.ingress.get("stream") or not s.ingress.get("subject")):
            warnings.append(
                f"stage '{s.name}' is missing ingress.stream/ingress.subject "
                f"(required for the NATS transport)."
            )

        if is_last and s.egress.get("forward_eos") is True:
            warnings.append(
                f"terminal stage '{s.name}' has forward_eos:true but has no "
                f"downstream; set it to false and use an on_end_of_stream hook."
            )

    return warnings
