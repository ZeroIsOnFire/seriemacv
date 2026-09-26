"""Local snapshots of canonical career source files."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Literal

from ruamel.yaml import YAML

CareerBackupReason = Literal["analyze", "create", "update"]
_BACKUP_REASONS = {"analyze", "create", "update"}


def create_career_backup(
    project_path: Path,
    reason: CareerBackupReason,
    *,
    now: Callable[[], datetime] | None = None,
) -> Path:
    """Copy the current canonical career sources into an immutable local snapshot."""
    project_path = project_path.expanduser().resolve()
    if reason not in _BACKUP_REASONS:
        raise ValueError("career backup reason must be analyze, create, or update")
    sources = _career_sources(project_path)
    if not sources:
        raise ValueError("project has no career source files to back up")

    created_at = (now or (lambda: datetime.now(UTC)))().astimezone(UTC)
    runtime_root = project_path / ".seriemacv"
    backup_root = runtime_root / "backups" / "career"
    for directory in (runtime_root, runtime_root / "backups", backup_root):
        if directory.exists() and directory.resolve() != directory.absolute():
            raise ValueError("career backup directory must not use symlinks")
    backup_root.mkdir(parents=True, exist_ok=True)
    name = f"{created_at.strftime('%Y%m%dT%H%M%SZ')}-{reason}"
    destination = _unique_destination(backup_root, name)
    temporary = Path(tempfile.mkdtemp(prefix=f".{name}-", dir=backup_root))

    manifest_files: list[dict[str, str]] = []
    try:
        for source in sources:
            relative = source.relative_to(project_path)
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            manifest_files.append(
                {
                    "path": relative.as_posix(),
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                }
            )
        manifest = {
            "schema_version": 1,
            "created_at": created_at.replace(microsecond=0).isoformat(),
            "reason": reason,
            "files": manifest_files,
        }
        stream = StringIO()
        YAML().dump(manifest, stream)
        (temporary / "manifest.yml").write_text(stream.getvalue(), encoding="utf-8")
        os.replace(temporary, destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination


def _career_sources(project_path: Path) -> list[Path]:
    candidates = [project_path / "career.yml"]
    locale_root = project_path / "career.locales"
    if locale_root.is_dir():
        candidates.extend(sorted(locale_root.glob("*.yml")))
    sources: list[Path] = []
    for candidate in candidates:
        if not candidate.is_file():
            continue
        if candidate.resolve() != candidate.absolute():
            raise ValueError("career backup sources must not use symlinks")
        if not candidate.resolve().is_relative_to(project_path):
            raise ValueError("career backup source must stay inside the project")
        sources.append(candidate)
    return sources


def _unique_destination(root: Path, name: str) -> Path:
    destination = root / name
    suffix = 2
    while destination.exists():
        destination = root / f"{name}-{suffix}"
        suffix += 1
    return destination
