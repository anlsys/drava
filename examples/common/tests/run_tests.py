"""Run all drava_common test modules with one command (no pytest required).

    python examples/common/tests/run_tests.py

Exits non-zero if any test fails. Each module also runs standalone
(`python examples/common/tests/test_config.py`) and under pytest if installed.
"""
import runpy
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_MODULES = [
    "test_config.py",
    "test_publisher.py",
    "test_cli.py",
    "test_examples_import.py",
]


def main() -> int:
    failures = 0
    for mod in _MODULES:
        print(f"\n===== {mod} =====")
        try:
            runpy.run_path(str(_HERE / mod), run_name="__main__")
        except SystemExit as exc:
            if exc.code:
                failures += 1
    print(f"\n{'ALL PASSED' if not failures else f'{failures} module(s) FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
