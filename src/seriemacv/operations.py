"""Local, content-free operation metrics for CLI and MCP workflows."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator, TextIO

from ruamel.yaml import YAML

DEFAULT_OUTPUT_WARNING_BYTES = 65_536
DEFAULT_MAX_RECORDS = 1_000
METRICS_PATH = Path(".seriemacv/metrics/operations.jsonl")
_BROWSER_KINDS = ("navigation", "inspection", "fill", "upload")
_CURRENT: ContextVar[OperationRecorder | None] = ContextVar(
    "seriemacv_operation", default=None
)


def utf8_size(value: str) -> int:
    return len(value.encode("utf-8"))


@dataclass
class OperationRecorder:
    project_path: Path
    interface: str
    operation: str
    input_bytes: int = 0
    output_warning_bytes: int = DEFAULT_OUTPUT_WARNING_BYTES
    max_records: int = DEFAULT_MAX_RECORDS
    output_bytes: int = 0
    error_bytes: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    browser_calls: dict[str, int] = field(
        default_factory=lambda: {kind: 0 for kind in _BROWSER_KINDS}
    )
    status: str = "success"
    _started: float = field(default_factory=perf_counter)
    _warning_emitted: bool = False
    _original_stderr: TextIO = field(default_factory=lambda: sys.stderr)
    _token: Any = field(init=False, repr=False, default=None)

    def __enter__(self) -> OperationRecorder:
        self._token = _CURRENT.set(self)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is not None:
            self.status = "error"
        _CURRENT.reset(self._token)
        self.persist()

    def add_output(self, size: int) -> None:
        self.output_bytes += size
        if self.output_bytes > self.output_warning_bytes and not self._warning_emitted:
            self._warning_emitted = True
            self._warn(
                "Warning: operation output exceeded "
                f"{self.output_warning_bytes} bytes; run "
                "'seriemacv diagnostics operations PATH' for a local summary.\n"
            )

    def add_error(self, size: int) -> None:
        self.error_bytes += size

    def record(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "interface": self.interface,
            "operation": self.operation,
            "status": self.status,
            "duration_ms": max(0, round((perf_counter() - self._started) * 1_000)),
            "input_bytes": max(0, self.input_bytes),
            "output_bytes": max(0, self.output_bytes),
            "error_bytes": max(0, self.error_bytes),
            "cache": {"hits": self.cache_hits, "misses": self.cache_misses},
            "browser": dict(self.browser_calls),
            "output_limit_exceeded": self._warning_emitted,
        }

    def persist(self) -> None:
        if not (self.project_path / "seriemacv.yml").is_file():
            return
        try:
            records = read_operation_records(self.project_path)
            records.append(self.record())
            _write_records(
                self.project_path,
                records[-max(1, self.max_records) :],
            )
        except OSError:
            self._warn("Warning: local operation metrics could not be written.\n")

    def _warn(self, message: str) -> None:
        try:
            self._original_stderr.write(message)
            self._original_stderr.flush()
        except (OSError, ValueError):
            pass


class _CountingStream:
    def __init__(self, stream: TextIO, callback: Any) -> None:
        self._stream = stream
        self._callback = callback

    def write(self, value: str) -> int:
        result = self._stream.write(value)
        self._callback(utf8_size(value))
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


@contextmanager
def capture_cli_output(recorder: OperationRecorder) -> Iterator[None]:
    stdout, stderr = sys.stdout, sys.stderr
    recorder._original_stderr = stderr
    sys.stdout = _CountingStream(stdout, recorder.add_output)
    sys.stderr = _CountingStream(stderr, recorder.add_error)
    try:
        yield
    finally:
        sys.stdout, sys.stderr = stdout, stderr


def record_cache(hit: bool) -> None:
    recorder = _CURRENT.get()
    if recorder is not None:
        if hit:
            recorder.cache_hits += 1
        else:
            recorder.cache_misses += 1


def record_browser_call(kind: str) -> None:
    recorder = _CURRENT.get()
    if recorder is not None and kind in recorder.browser_calls:
        recorder.browser_calls[kind] += 1


def load_operation_settings(project_path: Path) -> tuple[int, int]:
    """Return project settings while keeping instrumentation non-blocking."""
    try:
        from ruamel.yaml.error import YAMLError

        from seriemacv.project import load_project_configuration

        settings = load_project_configuration(project_path).operation_metrics
        return settings.output_warning_bytes, settings.max_records
    except (OSError, ValueError, YAMLError):
        return DEFAULT_OUTPUT_WARNING_BYTES, DEFAULT_MAX_RECORDS


def read_operation_records(project_path: Path) -> list[dict[str, Any]]:
    path = project_path / METRICS_PATH
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return []
    records = []
    for line in lines:
        try:
            value = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        record = _validated_record(value)
        if record is not None:
            records.append(record)
    return records


def operation_summary(project_path: Path, limit: int = 10) -> dict[str, Any]:
    records = read_operation_records(project_path)
    largest = sorted(
        records,
        key=lambda item: int(item.get("output_bytes", 0)),
        reverse=True,
    )[: max(0, limit)]
    slowest = sorted(
        records,
        key=lambda item: int(item.get("duration_ms", 0)),
        reverse=True,
    )[: max(0, limit)]
    browser_heaviest = sorted(
        records,
        key=_browser_call_count,
        reverse=True,
    )[: max(0, limit)]
    return {
        "operations": len(records),
        "status": {
            "success": sum(item.get("status") == "success" for item in records),
            "error": sum(item.get("status") == "error" for item in records),
        },
        "duration_ms": sum(int(item.get("duration_ms", 0)) for item in records),
        "input_bytes": sum(int(item.get("input_bytes", 0)) for item in records),
        "output_bytes": sum(int(item.get("output_bytes", 0)) for item in records),
        "error_bytes": sum(int(item.get("error_bytes", 0)) for item in records),
        "cache": {
            "hits": sum(int(item.get("cache", {}).get("hits", 0)) for item in records),
            "misses": sum(
                int(item.get("cache", {}).get("misses", 0)) for item in records
            ),
        },
        "browser_calls": {
            kind: sum(int(item.get("browser", {}).get(kind, 0)) for item in records)
            for kind in _BROWSER_KINDS
        },
        "largest_results": [_summary_record(item) for item in largest],
        "slowest_operations": [_summary_record(item) for item in slowest],
        "most_browser_calls": [_summary_record(item) for item in browser_heaviest],
    }


def _browser_call_count(item: dict[str, Any]) -> int:
    return sum(int(item.get("browser", {}).get(kind, 0)) for kind in _BROWSER_KINDS)


def _summary_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": item.get("timestamp"),
        "interface": item.get("interface"),
        "operation": item.get("operation"),
        "status": item.get("status"),
        "duration_ms": item.get("duration_ms", 0),
        "output_bytes": item.get("output_bytes", 0),
        "browser_calls": _browser_call_count(item),
        "output_limit_exceeded": item.get("output_limit_exceeded", False),
    }


def dump_operation_summary(project_path: Path, limit: int = 10) -> str:
    from io import StringIO

    stream = StringIO()
    YAML().dump(operation_summary(project_path, limit), stream)
    return stream.getvalue()


def _write_records(project_path: Path, records: list[dict[str, Any]]) -> None:
    path = project_path / METRICS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(
        json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n"
        for item in records
    )
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _validated_record(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return None
    interface = value.get("interface")
    operation = value.get("operation")
    status = value.get("status")
    timestamp = value.get("timestamp")
    if (
        interface not in {"cli", "mcp"}
        or status not in {"success", "error"}
        or not isinstance(operation, str)
        or re.fullmatch(r"[a-z][a-z0-9._-]{0,79}", operation) is None
        or not isinstance(timestamp, str)
        or re.fullmatch(r"\d{4}-\d{2}-\d{2}T[0-9:.]+Z", timestamp) is None
    ):
        return None
    numeric_names = ("duration_ms", "input_bytes", "output_bytes", "error_bytes")
    if any(
        not isinstance(value.get(name), int) or int(value[name]) < 0
        for name in numeric_names
    ):
        return None
    cache = value.get("cache")
    browser = value.get("browser")
    if not isinstance(cache, dict) or not isinstance(browser, dict):
        return None
    if any(
        not isinstance(cache.get(name), int) or cache[name] < 0
        for name in ("hits", "misses")
    ):
        return None
    if any(
        not isinstance(browser.get(name), int) or browser[name] < 0
        for name in _BROWSER_KINDS
    ):
        return None
    return {
        "schema_version": 1,
        "timestamp": timestamp,
        "interface": interface,
        "operation": operation,
        "status": status,
        **{name: value[name] for name in numeric_names},
        "cache": {"hits": cache["hits"], "misses": cache["misses"]},
        "browser": {name: browser[name] for name in _BROWSER_KINDS},
        "output_limit_exceeded": value.get("output_limit_exceeded") is True,
    }
