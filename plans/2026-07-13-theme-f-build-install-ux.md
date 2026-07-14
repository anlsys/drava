# Theme F — Build & install UX

Date: 2026-07-13
Status: Proposed
Impact: Medium-High · Effort: L · Local: Partial
Index: [2026-07-13-roadmap.md](2026-07-13-roadmap.md)

## Context

~8 manual build stages; 3 deps built from source (xkrt from INRIA GitLab,
yaml-cpp, nats.c) plus a no-GIL Python 3.14 build. No Dockerfile, devcontainer,
conda env, or spack package (only JLSE-specific `module load`). The SWIG Python
module isn't pip-installable and has no CMake install target — users manually
`export PYTHONPATH=<build dir>` ([README.md:72](../README.md#L72)).

## Fix (incremental)

- Add a `Dockerfile` / devcontainer building xkrt + yaml-cpp + nats.c + drava
  reproducibly (socket-only variant first; NATS variant second). Removes most
  onboarding pain and doubles as the CI base image (ties to Theme D).
- Add a CMake install target for the SWIG module + a `pip install -e` path or a
  `sitecustomize`/`.pth` so `import drava` works without manual PYTHONPATH.
- Optionally a spack package (project already lives in a spack/module world).

## Files to modify

- New: `Dockerfile` (and/or `.devcontainer/`).
- [../CMakeLists.txt](../CMakeLists.txt) (install target for the SWIG module).
- [../README.md](../README.md) (container-based quickstart).

## Verification

- `docker build` locally (socket-only image needs no JLSE); `import drava` + run
  `examples/dataflow` inside the container.
- NATS-variant image validated where NATS is available.
