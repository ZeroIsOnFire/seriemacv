"""Run the repository's reproducible local quality gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    ("compile", [sys.executable, "-m", "compileall", "-q", "src", "tests", "scripts"]),
    ("lint", [sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"]),
    (
        "format",
        [sys.executable, "-m", "ruff", "format", "--check", "src", "tests", "scripts"],
    ),
    ("types", [sys.executable, "-m", "mypy"]),
    (
        "tests",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
    ),
)


def main() -> int:
    failures: list[str] = []
    for name, command in CHECKS:
        print(f":: quality:{name}", flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            failures.append(name)
    if failures:
        print(f"Quality checks failed: {', '.join(failures)}", file=sys.stderr)
        return 1
    print("All quality checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
