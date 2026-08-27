"""Minimal diagnostic bundles that exclude user career artifacts."""

from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path

from seriemacv.privacy import redact_sensitive_text
from seriemacv.project import validate_project


def write_diagnostic_bundle(project_path: Path, output_path: Path) -> Path:
    """Write only redacted structural validation results to an atomic ZIP artifact."""
    errors = validate_project(project_path)
    payload = {
        "schema_version": 1,
        "application": {"name": "seriemacv", "version": "0.1.0"},
        "project": {
            "valid": not errors,
            "diagnostics": [redact_sensitive_text(error) for error in errors],
        },
    }
    target = output_path.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    os.close(descriptor)
    temporary_path = Path(temporary)
    try:
        with zipfile.ZipFile(
            temporary_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            archive.writestr("diagnostics.json", json.dumps(payload, indent=2) + "\n")
        os.replace(temporary_path, target)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return target
