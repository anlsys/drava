"""Read-only import of a SystemFlow model document into a Drava pipeline config.

SystemFlow (https://github.com/wilkieolin/system_flow) is a performance-modeling
framework. A SystemFlow *model document* ("Model Definition Standard v1.0")
describes a dataflow as ``graphs -> nodes / links / metrics``. Drava describes
the same dataflow operationally as a ``pipeline.yaml`` (``stages`` with
``runtime`` / ``ingress`` / ``egress``). This module maps the former onto the
latter so a Drava pipeline can be seeded from the performance model.

The interface is deliberately **one-way and read-only**: nothing here writes to
a SystemFlow checkout, and ``systemflow`` itself is an *optional* import -- the
importer works on a machine where SystemFlow is not installed, because a model
document is just YAML.

Design rules
------------
1. **Explicit beats inferred.** Drava runtime knobs are read only where the
   model document states them outright, in node/link parameters prefixed with
   ``"drava "``. We never derive ``threads`` or ``callback_batch`` from
   SystemFlow's FLOP/energy estimates -- that would be inventing physics.
2. **Both directions stay valid.** SystemFlow's ``parse_document``
   (``systemflow/io/schema.py:105``) ignores unknown top-level keys, so the
   ``drava:`` section added to a model document does not break SystemFlow.
   Drava's C++ reader (``src/drava_internal.cc:117``) reads only ``transport``
   and ``stages``, so the ``systemflow:`` provenance section emitted into
   ``pipeline.yaml`` is ignored by the runtime.
3. **Provenance is recorded.** Every generated ``pipeline.yaml`` carries a
   ``systemflow:`` block naming the source document, graph, and the
   SystemFlow node each stage came from. That block is what a future
   benchmark-feedback phase (``systemflow.io.calibrate``) will need in order to
   attribute measurements back to model nodes.

Topology mapping
----------------
The graph must be a **linear chain** (each node at most one predecessor and one
successor); branching/fan-in is rejected with a clear error rather than guessed
at. Chain order becomes stage order::

    SystemFlow node[0] -> stage1
    SystemFlow node[1] -> stage2
    ...

Each SystemFlow *link* is one Drava stream: the link supplies both the upstream
``egress.{stream,subject}`` and the downstream ``ingress.{stream,subject}``, so
the wiring check in :func:`drava_common.config.validate_pipeline` passes by
construction.

Recognized ``drava`` parameters
-------------------------------
On a **node** (all optional)::

    "drava stage (str)"                      -> stage name (default stage1..stageN)
    "drava threads (n)"                      -> runtime.threads
    "drava callback batch (n)"               -> runtime.callback_batch
    "drava callback flush timeout (ms)"      -> runtime.callback_flush_timeout_ms
    "drava callback serialize (bool)"        -> runtime.callback_serialize
    "drava nats async drain timeout (ms)"    -> runtime.nats_async_drain_timeout_ms
    "drava ingress durable (str)"            -> ingress.durable
    "drava ingress socket path (str)"        -> ingress.socket_path
    "drava fetch batch (n)"                  -> ingress.fetch_batch
    "drava fetch timeout (ms)"               -> ingress.fetch_timeout_ms
    "drava egress output fifo path (str)"    -> egress.output_fifo_path
    "drava forward eos (bool)"               -> egress.forward_eos
    "drava metrics output path (str)"        -> metrics.output_path

On a **link** (all optional)::

    "drava stream (str)"                     -> the NATS stream carrying it
    "drava subject (str)"                    -> the NATS subject carrying it

Top-level ``drava:`` section of the model document (all optional)::

    drava:
      pipeline_name: my_pipeline
      transport: {type: nats, nats_url: "nats://127.0.0.1:4222"}
      source:    {stream: FRAMES, subject: frames.raw}   # stage1 ingress
      durable_prefix: drava
      publisher: {...}     # copied verbatim into pipeline.yaml
      benchmark: {...}     # copied verbatim into pipeline.yaml

Public surface::

    from drava_common import (
        SystemFlowImportError, import_systemflow_pipeline,
        load_systemflow_document, systemflow_to_pipeline, dump_pipeline_yaml,
    )
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from .config import PipelineConfig, PipelineConfigError, StageConfig

#: Major schema version of the SystemFlow model document format we understand.
SYSTEMFLOW_SCHEMA_MAJOR = "1"

#: Prefix marking a Drava hint inside SystemFlow node/link parameters.
DRAVA_PARAM_PREFIX = "drava "

#: Version of the mapping implemented here, recorded in the provenance block.
IMPORTER_VERSION = 1


class SystemFlowImportError(Exception):
    """Raised when a SystemFlow model document cannot be mapped onto Drava."""


# --------------------------------------------------------------------------- #
# YAML loading
# --------------------------------------------------------------------------- #
# SystemFlow patches PyYAML's float resolver (systemflow/io/loader.py:27) so that
# unsigned-exponent literals like `40e6` parse as floats rather than strings.
# Stock yaml.safe_load does NOT do this. We replicate the same regex so a model
# document reads identically whether or not SystemFlow is installed.
_SYSTEMFLOW_FLOAT_RE = re.compile(
    r"""^(?:
         [-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+]?[0-9]+)?
        |[-+]?\.[0-9][0-9_]*(?:[eE][-+]?[0-9]+)?
        |[-+]?[0-9][0-9_]*(?:[eE][-+]?[0-9]+)
        |[-+]?\.(?:inf|Inf|INF)
        |\.(?:nan|NaN|NAN))$""",
    re.X,
)


def _systemflow_yaml_loader():
    """Return SystemFlow's own YAML loader class, or None if unavailable.

    Importing ``systemflow.io.loader`` also guards against this module
    shadowing the real package: if ``systemflow`` resolved to *us*, the
    ``.io.loader`` submodule lookup fails and we fall through to the
    replicated loader below.
    """
    try:
        from systemflow.io.loader import _make_yaml_loader  # type: ignore
    except Exception:  # pragma: no cover - depends on the environment
        return None
    try:
        return _make_yaml_loader()
    except Exception:  # pragma: no cover - defensive
        return None


def _local_yaml_loader():
    """Build a SafeLoader subclass with SystemFlow's float resolver applied."""
    import yaml  # noqa: F401  (import error handled by the caller)

    class _SystemFlowCompatLoader(yaml.SafeLoader):
        pass

    _SystemFlowCompatLoader.add_implicit_resolver(
        "tag:yaml.org,2002:float", _SYSTEMFLOW_FLOAT_RE, list("-+0123456789.")
    )
    return _SystemFlowCompatLoader


def load_systemflow_document(path: Path | str) -> tuple[dict, Path]:
    """Load a SystemFlow model document as a raw mapping.

    Uses SystemFlow's own YAML loader when the package is importable, and an
    equivalent locally-defined loader otherwise, so scientific-notation
    parameters agree either way. Returns ``(document, resolved_path)``.

    Raises :exc:`SystemFlowImportError` if the file is missing, is not YAML/JSON
    we can parse, or is not a mapping.
    """
    p = Path(path)
    if not p.exists():
        raise SystemFlowImportError(f"SystemFlow model document not found: {p}")
    text = p.read_text(encoding="utf-8")

    if p.suffix == ".json":
        import json

        try:
            doc = json.loads(text)
        except ValueError as exc:
            raise SystemFlowImportError(f"{p}: invalid JSON: {exc}") from exc
    else:
        loader = _systemflow_yaml_loader()
        if loader is None:
            try:
                loader = _local_yaml_loader()
            except ImportError as exc:  # pragma: no cover - yaml-less env
                raise SystemFlowImportError(
                    f"{p}: reading a SystemFlow model document needs either the "
                    f"'systemflow' package or PyYAML installed."
                ) from exc
        import yaml  # safe: _local_yaml_loader or systemflow already pulled it

        try:
            doc = yaml.load(text, Loader=loader)
        except Exception as exc:
            raise SystemFlowImportError(f"{p}: invalid YAML: {exc}") from exc

    if not isinstance(doc, dict):
        raise SystemFlowImportError(
            f"{p}: a SystemFlow model document must be a mapping, got "
            f"{type(doc).__name__}."
        )
    return doc, p


def dump_pipeline_yaml(mapping: dict) -> str:
    """Serialize a pipeline mapping to YAML text (requires PyYAML)."""
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - yaml-less env
        raise SystemFlowImportError(
            "writing a pipeline.yaml requires PyYAML (pip install pyyaml)."
        ) from exc
    return yaml.safe_dump(mapping, sort_keys=False, default_flow_style=False)


# --------------------------------------------------------------------------- #
# Parameter mapping tables
# --------------------------------------------------------------------------- #
def _as_int(value: Any, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SystemFlowImportError(f"{key!r} must be a number, got {value!r}.")
    if isinstance(value, float) and not value.is_integer():
        raise SystemFlowImportError(f"{key!r} must be a whole number, got {value!r}.")
    return int(value)


def _as_bool(value: Any, key: str) -> bool:
    if not isinstance(value, bool):
        raise SystemFlowImportError(f"{key!r} must be true or false, got {value!r}.")
    return value


def _as_str(value: Any, key: str) -> str:
    if not isinstance(value, str):
        raise SystemFlowImportError(f"{key!r} must be a string, got {value!r}.")
    return value


# node parameter name -> (pipeline.yaml section, key, coercion)
_NODE_PARAM_MAP: dict[str, tuple[str, str, Any]] = {
    "drava threads (n)": ("runtime", "threads", _as_int),
    "drava callback batch (n)": ("runtime", "callback_batch", _as_int),
    "drava callback flush timeout (ms)": (
        "runtime",
        "callback_flush_timeout_ms",
        _as_int,
    ),
    "drava callback serialize (bool)": ("runtime", "callback_serialize", _as_bool),
    "drava nats async drain timeout (ms)": (
        "runtime",
        "nats_async_drain_timeout_ms",
        _as_int,
    ),
    "drava ingress durable (str)": ("ingress", "durable", _as_str),
    "drava ingress socket path (str)": ("ingress", "socket_path", _as_str),
    "drava fetch batch (n)": ("ingress", "fetch_batch", _as_int),
    "drava fetch timeout (ms)": ("ingress", "fetch_timeout_ms", _as_int),
    "drava egress output fifo path (str)": ("egress", "output_fifo_path", _as_str),
    "drava forward eos (bool)": ("egress", "forward_eos", _as_bool),
    "drava metrics output path (str)": ("metrics", "output_path", _as_str),
}

#: Node parameters handled outside :data:`_NODE_PARAM_MAP`.
_NODE_PARAM_SPECIAL = {"drava stage (str)"}

#: Link parameters recognized by the importer.
_LINK_PARAM_SPECIAL = {"drava stream (str)", "drava subject (str)"}


def _check_unknown_drava_params(params: dict, where: str, known: set) -> None:
    unknown = sorted(
        k
        for k in params
        if isinstance(k, str) and k.startswith(DRAVA_PARAM_PREFIX) and k not in known
    )
    if unknown:
        raise SystemFlowImportError(
            f"{where}: unrecognized drava parameter(s) {unknown}. "
            f"Known keys: {sorted(known)}."
        )


# --------------------------------------------------------------------------- #
# Graph -> stage chain
# --------------------------------------------------------------------------- #
def _select_graph(doc: dict, graph: Optional[str], where: str) -> dict:
    graphs = doc.get("graphs")
    if not isinstance(graphs, list) or not graphs:
        raise SystemFlowImportError(
            f"{where}: 'graphs' must be a non-empty list (SystemFlow schema v1.0)."
        )
    named = []
    for i, g in enumerate(graphs):
        if not isinstance(g, dict):
            raise SystemFlowImportError(f"{where}: graphs[{i}] must be a mapping.")
        named.append((str(g.get("name", f"graph_{i}")), g))

    if graph is not None:
        for name, g in named:
            if name == graph:
                return g
        raise SystemFlowImportError(
            f"{where}: no graph named {graph!r}. Available: "
            f"{[n for n, _ in named]}."
        )
    if len(named) > 1:
        raise SystemFlowImportError(
            f"{where}: document has {len(named)} graphs "
            f"{[n for n, _ in named]}; pick one with --graph."
        )
    return named[0][1]


def _order_chain(nodes: list[str], links: list[dict], where: str) -> list[str]:
    """Return node names in dataflow order, requiring a single linear chain."""
    if not nodes:
        raise SystemFlowImportError(f"{where}: graph has no nodes.")

    succ: dict[str, str] = {}
    pred: dict[str, str] = {}
    for link in links:
        tx, rx = link["tx"], link["rx"]
        if tx in succ:
            raise SystemFlowImportError(
                f"{where}: node {tx!r} fans out to {succ[tx]!r} and {rx!r}. "
                f"The importer supports linear chains only; split the model "
                f"into single-path graphs or extend the importer."
            )
        if rx in pred:
            raise SystemFlowImportError(
                f"{where}: node {rx!r} fans in from {pred[rx]!r} and {tx!r}. "
                f"The importer supports linear chains only; Drava stages take "
                f"exactly one ingress."
            )
        succ[tx] = rx
        pred[rx] = tx

    sources = [n for n in nodes if n not in pred]
    if len(sources) != 1:
        raise SystemFlowImportError(
            f"{where}: expected exactly one source node (no inbound link), "
            f"found {sorted(sources)}. Disconnected nodes are not supported."
        )

    order = []
    seen = set()
    cur = sources[0]
    while cur is not None:
        if cur in seen:
            raise SystemFlowImportError(f"{where}: link cycle through {cur!r}.")
        seen.add(cur)
        order.append(cur)
        cur = succ.get(cur)

    missing = [n for n in nodes if n not in seen]
    if missing:
        raise SystemFlowImportError(
            f"{where}: node(s) {sorted(missing)} are not connected to the chain "
            f"starting at {sources[0]!r}."
        )
    return order


def _slug(text: str) -> str:
    out = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return out or "stage"


# --------------------------------------------------------------------------- #
# The mapping
# --------------------------------------------------------------------------- #
def systemflow_to_pipeline(
    doc: dict,
    *,
    source_path: Path | str | None = None,
    graph: Optional[str] = None,
) -> dict:
    """Map a SystemFlow model document onto a Drava ``pipeline.yaml`` mapping.

    Args:
        doc: Parsed SystemFlow model document (see :func:`load_systemflow_document`).
        source_path: Path the document came from; recorded as provenance.
        graph: Which graph to import. Required when the document has more
            than one.

    Returns:
        A dict with the ``pipeline`` / ``systemflow`` / ``transport`` /
        ``stages`` shape that Drava's runtime and
        :func:`drava_common.config.load_pipeline_config` both accept.

    Raises:
        SystemFlowImportError: on an unsupported schema version, a non-linear
            graph, or an unrecognized ``drava`` parameter.
    """
    where = str(source_path) if source_path else "<systemflow document>"

    version = str(doc.get("schema_version", "1.0"))
    if version.split(".")[0] != SYSTEMFLOW_SCHEMA_MAJOR:
        raise SystemFlowImportError(
            f"{where}: unsupported SystemFlow schema_version {version!r}; "
            f"this importer understands major version "
            f"{SYSTEMFLOW_SCHEMA_MAJOR!r}."
        )

    opts = doc.get("drava", {}) or {}
    if not isinstance(opts, dict):
        raise SystemFlowImportError(f"{where}: top-level 'drava' must be a mapping.")

    g = _select_graph(doc, graph, where)
    graph_name = str(g.get("name", "graph_0"))

    raw_nodes = g.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise SystemFlowImportError(f"{where}: graph {graph_name!r} has no nodes.")

    nodes: dict[str, dict] = {}
    node_order_declared: list[str] = []
    for i, n in enumerate(raw_nodes):
        if not isinstance(n, dict) or "name" not in n:
            raise SystemFlowImportError(
                f"{where}: graph {graph_name!r} nodes[{i}] needs a 'name'."
            )
        name = str(n["name"])
        if name in nodes:
            raise SystemFlowImportError(
                f"{where}: duplicate node name {name!r} in graph {graph_name!r}."
            )
        nodes[name] = n
        node_order_declared.append(name)

    raw_links = g.get("links", []) or []
    if not isinstance(raw_links, list):
        raise SystemFlowImportError(f"{where}: graph {graph_name!r} 'links' must be a list.")
    links: list[dict] = []
    for i, ln in enumerate(raw_links):
        if not isinstance(ln, dict) or "tx" not in ln or "rx" not in ln:
            raise SystemFlowImportError(
                f"{where}: graph {graph_name!r} links[{i}] needs 'tx' and 'rx'."
            )
        tx, rx = str(ln["tx"]), str(ln["rx"])
        for end, label in ((tx, "tx"), (rx, "rx")):
            if end not in nodes:
                raise SystemFlowImportError(
                    f"{where}: links[{i}].{label}={end!r} is not a node in graph "
                    f"{graph_name!r}."
                )
        links.append({"tx": tx, "rx": rx, "raw": ln})

    chain = _order_chain(node_order_declared, links, f"{where}: graph {graph_name!r}")
    link_by_tx = {ln["tx"]: ln for ln in links}

    pipeline_name = str(opts.get("pipeline_name") or doc.get("name") or graph_name)

    transport_opts = opts.get("transport", {}) or {}
    if not isinstance(transport_opts, dict):
        raise SystemFlowImportError(f"{where}: 'drava.transport' must be a mapping.")
    transport_type = str(transport_opts.get("type", "nats"))
    nats_url = str(transport_opts.get("nats_url", "nats://127.0.0.1:4222"))

    source_opts = opts.get("source", {}) or {}
    if not isinstance(source_opts, dict):
        raise SystemFlowImportError(f"{where}: 'drava.source' must be a mapping.")
    durable_prefix = str(opts.get("durable_prefix", "drava"))

    # ---- resolve stage names first, so durables and errors can use them ----
    stage_names: list[str] = []
    for idx, node_name in enumerate(chain):
        params = nodes[node_name].get("parameters", {}) or {}
        if not isinstance(params, dict):
            raise SystemFlowImportError(
                f"{where}: node {node_name!r} 'parameters' must be a mapping."
            )
        _check_unknown_drava_params(
            params,
            f"{where}: node {node_name!r}",
            set(_NODE_PARAM_MAP) | _NODE_PARAM_SPECIAL,
        )
        explicit = params.get("drava stage (str)")
        name = (
            _as_str(explicit, f"node {node_name!r} 'drava stage (str)'")
            if explicit is not None
            else f"stage{idx + 1}"
        )
        if name in stage_names:
            raise SystemFlowImportError(
                f"{where}: duplicate Drava stage name {name!r}."
            )
        stage_names.append(name)

    # ---- build the stages ----
    stages: list[dict] = []
    for idx, node_name in enumerate(chain):
        node = nodes[node_name]
        params = node.get("parameters", {}) or {}
        stage_name = stage_names[idx]
        is_first = idx == 0
        is_last = idx == len(chain) - 1

        sections: dict[str, dict] = {
            "runtime": {},
            "ingress": {},
            "egress": {},
            "metrics": {},
        }

        # ingress: first stage from drava.source, later stages from the inbound link
        if is_first:
            if source_opts.get("stream") is not None:
                sections["ingress"]["stream"] = _as_str(
                    source_opts["stream"], "drava.source.stream"
                )
            if source_opts.get("subject") is not None:
                sections["ingress"]["subject"] = _as_str(
                    source_opts["subject"], "drava.source.subject"
                )
            if transport_type == "nats":
                sections["ingress"].setdefault("stream", "FRAMES")
                sections["ingress"].setdefault("subject", "frames.raw")
        else:
            prev_link = link_by_tx[chain[idx - 1]]
            sections["ingress"]["stream"] = prev_link["stream"]
            sections["ingress"]["subject"] = prev_link["subject"]

        # egress: from the outbound link; terminal stages get forward_eos: false
        if is_last:
            sections["egress"]["forward_eos"] = False
        else:
            link = link_by_tx[node_name]
            lparams = link["raw"].get("parameters", {}) or {}
            if not isinstance(lparams, dict):
                raise SystemFlowImportError(
                    f"{where}: link {link['tx']!r} -> {link['rx']!r} 'parameters' "
                    f"must be a mapping."
                )
            _check_unknown_drava_params(
                lparams,
                f"{where}: link {link['tx']!r} -> {link['rx']!r}",
                _LINK_PARAM_SPECIAL,
            )
            lname = str(link["raw"].get("name", f"{link['tx']} -> {link['rx']}"))
            stream = lparams.get("drava stream (str)")
            subject = lparams.get("drava subject (str)")
            link["stream"] = (
                _as_str(stream, f"link {lname!r} 'drava stream (str)'")
                if stream is not None
                else _slug(lname).upper()
            )
            link["subject"] = (
                _as_str(subject, f"link {lname!r} 'drava subject (str)'")
                if subject is not None
                else f"frames.{stage_name}"
            )
            sections["egress"]["stream"] = link["stream"]
            sections["egress"]["subject"] = link["subject"]

        # explicit per-node drava knobs override everything derived above
        for key, (section, field_name, coerce) in _NODE_PARAM_MAP.items():
            if key in params:
                sections[section][field_name] = coerce(
                    params[key], f"node {node_name!r} {key!r}"
                )

        if transport_type == "nats":
            sections["ingress"].setdefault(
                "durable", f"{durable_prefix}_{_slug(pipeline_name)}_{stage_name}"
            )

        stage: dict = {"name": stage_name}
        for section in ("runtime", "ingress", "egress", "metrics"):
            if sections[section]:
                stage[section] = sections[section]
        stages.append(stage)

    # ---- assemble, in Drava's conventional key order ----
    out: dict = {"pipeline": {"name": pipeline_name}}
    out["systemflow"] = {
        "schema_version": version,
        "model_name": str(doc.get("name", "")) or graph_name,
        "model_path": str(source_path) if source_path else None,
        "graph": graph_name,
        "imported_by": f"drava_common.systemflow v{IMPORTER_VERSION}",
        "stage_nodes": {stage_names[i]: chain[i] for i in range(len(chain))},
    }
    out["transport"] = {"type": transport_type}
    if transport_type == "nats":
        out["transport"]["nats_url"] = nats_url
    for passthrough in ("publisher", "benchmark"):
        if passthrough in opts:
            value = opts[passthrough]
            if not isinstance(value, dict):
                raise SystemFlowImportError(
                    f"{where}: 'drava.{passthrough}' must be a mapping."
                )
            out[passthrough] = dict(value)
    out["stages"] = stages
    return out


def import_systemflow_pipeline(
    path: Path | str,
    *,
    graph: Optional[str] = None,
) -> tuple[dict, PipelineConfig]:
    """Load a SystemFlow model document and return ``(mapping, PipelineConfig)``.

    The :class:`~drava_common.config.PipelineConfig` is built from the generated
    mapping without touching disk, so callers can validate the result before
    deciding whether to write a ``pipeline.yaml``.
    """
    doc, resolved = load_systemflow_document(path)
    mapping = systemflow_to_pipeline(doc, source_path=resolved, graph=graph)
    return mapping, pipeline_config_from_mapping(mapping, resolved)


def pipeline_config_from_mapping(
    mapping: dict, path: Path | str
) -> PipelineConfig:
    """Build a :class:`PipelineConfig` from an in-memory pipeline mapping.

    Mirrors :func:`drava_common.config.load_pipeline_config` without reading a
    file, so the importer can reuse the existing validator.
    """
    pipeline = mapping.get("pipeline", {}) or {}
    transport = mapping.get("transport", {}) or {}
    raw_stages = mapping.get("stages", []) or []
    if not isinstance(raw_stages, list):
        raise PipelineConfigError("'stages' must be a list")

    stages = []
    for entry in raw_stages:
        if not isinstance(entry, dict) or "name" not in entry:
            raise PipelineConfigError(f"each stage needs a 'name'; got: {entry!r}")
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
        path=Path(path),
        raw=mapping,
        name=str(pipeline.get("name", Path(path).stem)),
        transport_type=str(transport.get("type", "socket")),
        nats_url=str(transport.get("nats_url", "nats://127.0.0.1:4222")),
        stages=stages,
    )


__all__ = [
    "DRAVA_PARAM_PREFIX",
    "IMPORTER_VERSION",
    "SYSTEMFLOW_SCHEMA_MAJOR",
    "SystemFlowImportError",
    "dump_pipeline_yaml",
    "import_systemflow_pipeline",
    "load_systemflow_document",
    "pipeline_config_from_mapping",
    "systemflow_to_pipeline",
]
