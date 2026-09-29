"""Shared helpers for Drava example apps, publishers, and orchestration.

This package removes the copy-paste that used to live in every
``examples/<name>/`` directory (hand-rolled YAML parsers, publisher pacing
loops, metrics writers, benchmark plumbing). A new example should only need an
``app.py`` (a callback + ``drava.run``) and a ``pipeline.yaml``; everything
generic lives here.

Public surface (import from ``drava_common``):

- Config: :func:`load_pipeline_config`, :class:`PipelineConfig`,
  :func:`validate_pipeline`, :exc:`PipelineConfigError`.
- Publisher: :func:`load_transport_config`, :func:`load_publish_config`,
  :func:`write_publisher_metrics`, :func:`publish_stream`,
  :func:`socket_publish_stream`, ``EOS_PREFIX``.
- SystemFlow: :func:`import_systemflow_pipeline`,
  :func:`load_systemflow_document`, :func:`systemflow_to_pipeline`,
  :func:`dump_pipeline_yaml`, :exc:`SystemFlowImportError`. Read-only import
  of a SystemFlow performance model into an initial ``pipeline.yaml``; the
  ``systemflow`` package is optional.
"""

from .config import (
    PipelineConfig,
    PipelineConfigError,
    StageConfig,
    load_pipeline_config,
    load_yaml,
    validate_pipeline,
)
from .publisher import (
    EOS_PREFIX,
    connect_jetstream,
    load_publish_config,
    load_transport_config,
    publish_stream,
    socket_publish_stream,
    write_publisher_metrics,
)
from .systemflow import (
    SystemFlowImportError,
    dump_pipeline_yaml,
    import_systemflow_pipeline,
    load_systemflow_document,
    pipeline_config_from_mapping,
    systemflow_to_pipeline,
)

__all__ = [
    "PipelineConfig",
    "PipelineConfigError",
    "StageConfig",
    "load_pipeline_config",
    "load_yaml",
    "validate_pipeline",
    "EOS_PREFIX",
    "connect_jetstream",
    "load_publish_config",
    "load_transport_config",
    "publish_stream",
    "socket_publish_stream",
    "write_publisher_metrics",
    "SystemFlowImportError",
    "dump_pipeline_yaml",
    "import_systemflow_pipeline",
    "load_systemflow_document",
    "pipeline_config_from_mapping",
    "systemflow_to_pipeline",
]
