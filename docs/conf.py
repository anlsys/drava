"""Sphinx configuration for the Drava documentation site.

Builds three things into one site:
- the Markdown guides in this directory (via myst-parser),
- the C API reference from Doxygen XML (via breathe),
- the Python `drava_common` API reference (via sphinx-autoapi, which parses the
  source statically so no compiled module needs to be importable).

Read the Docs runs Doxygen first (see .readthedocs.yaml) so the XML exists
before Sphinx runs. For a local build, `conf.py` also invokes Doxygen itself if
the XML is missing, so `sphinx-build docs docs/_build/html` works standalone.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

# --------------------------------------------------------------------------- #
# Project metadata
# --------------------------------------------------------------------------- #
project = "Drava"
copyright = "2025, UChicago Argonne, LLC"
author = "Argonne National Laboratory"
release = "0.1.0"

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
_DOCS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _DOCS_DIR.parent
_DOXYGEN_XML = _DOCS_DIR / "_doxygen" / "xml"

# --------------------------------------------------------------------------- #
# Extensions
# --------------------------------------------------------------------------- #
extensions = [
    "myst_parser",        # Markdown support
    "breathe",            # Doxygen (C/C++) bridge
    "autoapi.extension",  # Python API from source (no import needed)
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
]

myst_enable_extensions = ["colon_fence", "deflist"]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

# The Markdown guides are browsed both on GitHub and on this site, so they use
# repo-relative links to source files (../examples/..., ../README.md) that live
# outside the docs tree. Those resolve on GitHub; suppress the Sphinx warnings
# for links that intentionally point outside the built site.
# myst.xref_missing: repo-relative links to files outside the docs tree (resolve
#   on GitHub). duplicate_declaration: breathe re-emits typedef'd enums/structs
#   through the C domain, which is a harmless rendering artifact.
suppress_warnings = ["myst.xref_missing", "duplicate_declaration", "c.parse"]

# --------------------------------------------------------------------------- #
# HTML theme
# --------------------------------------------------------------------------- #
html_theme = "furo"
html_title = "Drava"
html_static_path = ["_static"] if (_DOCS_DIR / "_static").exists() else []

# --------------------------------------------------------------------------- #
# breathe (C API)
# --------------------------------------------------------------------------- #
breathe_projects = {"drava": str(_DOXYGEN_XML)}
breathe_default_project = "drava"
breathe_domain_by_extension = {"h": "c"}

# --------------------------------------------------------------------------- #
# sphinx-autoapi (Python API for the drava_common helper package)
# --------------------------------------------------------------------------- #
autoapi_type = "python"
autoapi_dirs = [str(_REPO_ROOT / "examples" / "common" / "drava_common")]
autoapi_root = "api/python"
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
]
autoapi_add_toctree_entry = False   # linked explicitly from the API page
autoapi_keep_files = False
autoapi_ignore = ["*/tests/*", "*/__main__.py"]

# --------------------------------------------------------------------------- #
# Run Doxygen for local builds if the XML isn't already present.
# On Read the Docs this is done by the build.jobs step in .readthedocs.yaml.
# --------------------------------------------------------------------------- #
def _ensure_doxygen() -> None:
    if _DOXYGEN_XML.exists():
        return
    doxyfile = _DOCS_DIR / "Doxyfile"
    if not doxyfile.exists():
        return
    try:
        subprocess.run(["doxygen", str(doxyfile)], cwd=str(_DOCS_DIR), check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"[conf.py] warning: could not run Doxygen ({exc}); "
              f"the C API reference will be empty.")


_ensure_doxygen()

exclude_patterns = ["_build", "_doxygen", "Thumbs.db", ".DS_Store",
                    "requirements.txt", "Doxyfile",
                    "figures/**",          # image assets, not doc pages
                    "artifact-description-form.txt"]
