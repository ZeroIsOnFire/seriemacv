"""Canonical job YAML schema, validation, and safe local storage."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLError

JOB_DIRECTORY = "jobs"
_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class IdentifiedRecord(StrictModel):
    id: str = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def stable_id(cls, value: str) -> str:
        if not _ID_PATTERN.fullmatch(value):
            raise ValueError("must use lowercase kebab-case")
        return value


class JobRequirement(IdentifiedRecord):
    statement: str = Field(min_length=1)
    priority: Literal["required", "preferred"] = "required"

    @field_validator("statement")
    @classmethod
    def statement_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class JobSource(StrictModel):
    format: Literal["manual", "json", "yaml"]
    filename: str = ""
    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def content_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class JobImportPayload(IdentifiedRecord):
    """Structured fields accepted from a JSON source before source metadata is added."""

    schema_version: Literal[1]
    title: str = Field(min_length=1)
    description: str = ""
    company: str = ""
    location: str = ""
    work_model: str = ""
    employment_type: str = ""
    seniority: str = ""
    language: str = ""
    salary_range: str = ""
    requirements: list[JobRequirement] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def title_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def requirement_ids_are_unique(self) -> "JobImportPayload":
        _ensure_unique_requirement_ids(self.requirements)
        return self


class JobDocument(JobImportPayload):
    source: JobSource


def _ensure_unique_requirement_ids(requirements: list[JobRequirement]) -> None:
    ids = [requirement.id for requirement in requirements]
    if len(ids) != len(set(ids)):
        raise ValueError("requirements contains duplicate ids")


@dataclass(frozen=True)
class JobDiagnostic:
    path: str
    message: str
    line: int | None = None
    column: int | None = None

    def format(self, file_path: Path) -> str:
        location = str(file_path)
        if self.line is not None:
            location += f":{self.line}:{self.column or 1}"
        return f"{location}: {self.path}: {self.message}"


def load_job(path: Path) -> JobDocument:
    document = _load_yaml(path)
    return JobDocument.model_validate(document)


def validate_job(path: Path) -> list[JobDiagnostic]:
    try:
        document = _load_yaml(path)
    except (OSError, ValueError, YAMLError) as error:
        return [JobDiagnostic("document", f"invalid YAML: {error}")]
    try:
        JobDocument.model_validate(document)
    except ValidationError as error:
        return [_diagnostic_from_error(document, item) for item in error.errors()]
    return []


def validate_jobs(project_path: Path) -> list[tuple[Path, JobDiagnostic]]:
    jobs_path = project_path / JOB_DIRECTORY
    diagnostics: list[tuple[Path, JobDiagnostic]] = []
    for path in sorted(jobs_path.glob("*.yml")):
        diagnostics.extend((path, diagnostic) for diagnostic in validate_job(path))
    return diagnostics


def create_job(project_path: Path, payload: JobImportPayload, source: JobSource) -> Path:
    document = JobDocument(**payload.model_dump(), source=source)
    path = job_path(project_path, document.id)
    if path.exists():
        raise FileExistsError(f"A job with id '{document.id}' already exists")
    _write_yaml(path, document)
    return path


def load_jobs(project_path: Path) -> list[JobDocument]:
    diagnostics = validate_jobs(project_path)
    if diagnostics:
        path, diagnostic = diagnostics[0]
        raise ValueError(diagnostic.format(path))
    return [load_job(path) for path in sorted((project_path / JOB_DIRECTORY).glob("*.yml"))]


def job_path(project_path: Path, job_id: str) -> Path:
    if not _ID_PATTERN.fullmatch(job_id):
        raise ValueError("job id must use lowercase kebab-case")
    return project_path / JOB_DIRECTORY / f"{job_id}.yml"


def dump_job(value: JobDocument | list[JobDocument]) -> str:
    yaml = YAML()
    yaml.default_flow_style = False
    stream = StringIO()
    if isinstance(value, list):
        dumped: Any = [item.model_dump(mode="python") for item in value]
    else:
        dumped = value.model_dump(mode="python")
    yaml.dump(dumped, stream)
    return stream.getvalue()


def source_format_for_path(path: Path) -> Literal["json", "yaml"]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in {".yml", ".yaml"}:
        return "yaml"
    raise ValueError(f"Unsupported job source format: {path.suffix or '(no extension)'}")


def load_json_payload(content: str) -> JobImportPayload:
    import json

    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON: {error}") from error
    return JobImportPayload.model_validate(_normalize_identifiers(value))


def load_yaml_payload(content: str) -> JobImportPayload:
    yaml = YAML(typ="rt")
    value = yaml.load(content)
    if not isinstance(value, CommentedMap):
        raise ValueError("structured YAML job input must contain a mapping")
    return JobImportPayload.model_validate(_normalize_identifiers(value))


def _normalize_identifiers(value: Any) -> Any:
    """Canonicalize letter case while retaining strict kebab-case validation."""
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    if isinstance(normalized.get("id"), str):
        normalized["id"] = normalized["id"].lower()
    requirements = normalized.get("requirements")
    if isinstance(requirements, list):
        normalized["requirements"] = [
            {**item, "id": item["id"].lower()}
            if isinstance(item, dict) and isinstance(item.get("id"), str)
            else item
            for item in requirements
        ]
    return normalized


def _load_yaml(path: Path) -> CommentedMap:
    yaml = YAML(typ="rt")
    document = yaml.load(path.read_text(encoding="utf-8"))
    if not isinstance(document, CommentedMap):
        raise ValueError(f"{path.name} must contain a mapping")
    return document


def _write_yaml(path: Path, document: JobDocument) -> None:
    yaml = YAML(typ="rt")
    stream = StringIO()
    yaml.dump(document.model_dump(mode="python"), stream)
    _atomic_write(path, stream.getvalue())


def _atomic_write(path: Path, content: str) -> None:
    descriptor, temporary_path = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
        os.replace(temporary_path, path)
    except BaseException:
        Path(temporary_path).unlink(missing_ok=True)
        raise


def _diagnostic_from_error(document: Any, error: dict[str, Any]) -> JobDiagnostic:
    return _diagnostic_for_path(document, tuple(error["loc"]), error["msg"])


def _diagnostic_for_path(
    document: Any, location: tuple[Any, ...], message: str
) -> JobDiagnostic:
    line = column = None
    current = document
    for part in location:
        try:
            position = current.lc.item(part) if isinstance(part, int) else current.lc.key(part)
            if position is not None:
                line, column = position[0] + 1, position[1] + 1
            current = current[part]
        except (AttributeError, KeyError, IndexError, TypeError):
            break
    path = ".".join(str(part) for part in location) or "document"
    return JobDiagnostic(path, message, line, column)
