"""Reviewable, process-local change tokens shared by MCP write tools."""

from __future__ import annotations

import hashlib
import secrets
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ChangeDiff(StrictModel):
    path: str
    before: Any = None
    after: Any = None


class PreparedChange(StrictModel):
    schema_version: Literal[1] = 1
    token: str
    expires_at: str
    operation: str
    summary: str
    diff: list[ChangeDiff] = Field(default_factory=list)
    affected_files: list[str]
    warnings: list[str] = Field(default_factory=list)


class ConfirmedChange(StrictModel):
    schema_version: Literal[1] = 1
    status: Literal["confirmed"] = "confirmed"
    operation: str
    affected_files: list[str]
    result: Any = None


@dataclass
class _PendingChange:
    prepared: PreparedChange
    paths: tuple[Path, ...]
    base_hashes: dict[Path, str | None]
    existing_directories: set[Path]
    action: Callable[[], Any]


class ChangeManager:
    """Store short-lived, single-use changes for one project-bound MCP process."""

    def __init__(
        self,
        project_path: Path,
        *,
        ttl_seconds: int = 600,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.project_path = project_path.resolve()
        self.ttl_seconds = ttl_seconds
        self._now = now or (lambda: datetime.now(UTC))
        self._pending: dict[str, _PendingChange] = {}
        self._lock = threading.Lock()

    def prepare(
        self,
        *,
        operation: str,
        summary: str,
        diff: list[ChangeDiff],
        affected_paths: list[Path],
        action: Callable[[], Any],
        warnings: list[str] | None = None,
    ) -> PreparedChange:
        paths = tuple(self._safe_path(path) for path in affected_paths)
        if len(paths) != len(set(paths)):
            raise ValueError("affected_files contains duplicate paths")
        token = secrets.token_urlsafe(32)
        expires_at = self._now() + timedelta(seconds=self.ttl_seconds)
        prepared = PreparedChange(
            token=token,
            expires_at=expires_at.replace(microsecond=0).isoformat(),
            operation=operation,
            summary=summary,
            diff=diff,
            affected_files=[
                path.relative_to(self.project_path).as_posix() for path in paths
            ],
            warnings=warnings or [],
        )
        existing_directories = {
            parent
            for path in paths
            for parent in path.parents
            if parent.is_relative_to(self.project_path) and parent.is_dir()
        }
        pending = _PendingChange(
            prepared,
            paths,
            {path: _file_hash(path) for path in paths},
            existing_directories,
            action,
        )
        with self._lock:
            self._discard_expired()
            self._pending[token] = pending
        return prepared

    def confirm(self, token: str) -> ConfirmedChange:
        with self._lock:
            pending = self._pending.pop(token, None)
        if pending is None:
            raise ValueError("unknown or already used change token")
        expires_at = datetime.fromisoformat(pending.prepared.expires_at)
        if self._now() >= expires_at:
            raise ValueError("change token has expired")
        current = {path: _file_hash(path) for path in pending.paths}
        if current != pending.base_hashes:
            raise ValueError("project files changed after the change was prepared")

        snapshots = {
            path: path.read_bytes() if path.is_file() else None
            for path in pending.paths
        }
        try:
            result = pending.action()
        except BaseException:
            _restore_files(
                self.project_path,
                snapshots,
                pending.existing_directories,
            )
            raise
        return ConfirmedChange(
            operation=pending.prepared.operation,
            affected_files=pending.prepared.affected_files,
            result=_json_value(result),
        )

    def _safe_path(self, path: Path) -> Path:
        resolved = path.resolve()
        if (
            not resolved.is_relative_to(self.project_path)
            or resolved == self.project_path
        ):
            raise ValueError("affected file must stay inside the bound project")
        return resolved

    def _discard_expired(self) -> None:
        now = self._now()
        expired = [
            token
            for token, pending in self._pending.items()
            if now >= datetime.fromisoformat(pending.prepared.expires_at)
        ]
        for token in expired:
            del self._pending[token]


def _file_hash(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _restore_files(
    project_path: Path,
    snapshots: dict[Path, bytes | None],
    existing_directories: set[Path],
) -> None:
    for path, content in snapshots.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    candidates = sorted(
        {
            parent
            for path in snapshots
            for parent in path.parents
            if parent.is_relative_to(project_path)
            and parent != project_path
            and parent not in existing_directories
        },
        key=lambda item: len(item.parts),
        reverse=True,
    )
    for directory in candidates:
        try:
            directory.rmdir()
        except OSError:
            pass


def _json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    return value
