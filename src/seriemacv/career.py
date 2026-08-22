"""Canonical career YAML schema, validation and safe editing helpers."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

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

CAREER_FILE = "career.yml"
_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_YEAR_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CareerProfile(StrictModel):
    name: str = ""
    title: str = ""
    location: str = ""
    email: str = ""
    phone: str = ""
    links: dict[str, str] = Field(default_factory=dict)
    languages: list[str] = Field(default_factory=list)
    work_preference: str = ""
    work_authorization: str = ""
    notice_period: str = ""

    @field_validator("email")
    @classmethod
    def email_format(cls, value: str) -> str:
        if value and ("@" not in value or value.startswith("@") or value.endswith("@")):
            raise ValueError("must be a valid email address")
        return value

    @field_validator("links")
    @classmethod
    def http_links(cls, value: dict[str, str]) -> dict[str, str]:
        for name, url in value.items():
            parsed = urlparse(url)
            if not name.strip() or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("must contain named http(s) URLs")
        return value


class IdentifiedRecord(StrictModel):
    id: str = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def stable_id(cls, value: str) -> str:
        if not _ID_PATTERN.fullmatch(value):
            raise ValueError("must use lowercase kebab-case")
        return value


class DatedRecord(IdentifiedRecord):
    start_date: str
    end_date: str | None = None

    @field_validator("start_date", "end_date")
    @classmethod
    def year_month(cls, value: str | None) -> str | None:
        if value is not None and not _YEAR_MONTH_PATTERN.fullmatch(value):
            raise ValueError("must use YYYY-MM")
        return value

    @model_validator(mode="after")
    def chronological_dates(self) -> "DatedRecord":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must not be earlier than start_date")
        return self


class Experience(DatedRecord):
    company: str = Field(min_length=1)
    title: str = Field(min_length=1)
    location: str = ""
    employment_type: str = ""
    highlights: list[str] = Field(default_factory=list)


class Education(DatedRecord):
    institution: str = Field(min_length=1)
    degree: str = Field(min_length=1)
    field_of_study: str = ""
    location: str = ""
    highlights: list[str] = Field(default_factory=list)


class Skill(IdentifiedRecord):
    name: str = Field(min_length=1)
    category: str = ""
    tags: list[str] = Field(default_factory=list)


class CareerEvidence(IdentifiedRecord):
    statement: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    details: list[str] = Field(default_factory=list)
    experience_id: str | None = None
    verified: bool = False


class SavedAnswer(IdentifiedRecord):
    prompt: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class CareerStory(IdentifiedRecord):
    title: str = Field(min_length=1)
    situation: str = ""
    action: str = ""
    result: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class CareerDocument(StrictModel):
    schema_version: Literal[1]
    profile: CareerProfile = Field(default_factory=CareerProfile)
    summary: str = ""
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    evidence: list[CareerEvidence] = Field(default_factory=list)
    answers: list[SavedAnswer] = Field(default_factory=list)
    stories: list[CareerStory] = Field(default_factory=list)

    @model_validator(mode="after")
    def references_are_valid(self) -> "CareerDocument":
        _ensure_unique_ids(self.experience, "experience")
        _ensure_unique_ids(self.education, "education")
        _ensure_unique_ids(self.skills, "skills")
        _ensure_unique_ids(self.evidence, "evidence")
        _ensure_unique_ids(self.answers, "answers")
        _ensure_unique_ids(self.stories, "stories")
        experience_ids = {record.id for record in self.experience}
        evidence_ids = {record.id for record in self.evidence}
        for record in self.evidence:
            if record.experience_id and record.experience_id not in experience_ids:
                raise ValueError(
                    f"evidence '{record.id}' references unknown experience_id "
                    f"'{record.experience_id}'"
                )
        for record in self.stories:
            unknown = set(record.evidence_ids) - evidence_ids
            if unknown:
                raise ValueError(
                    f"story '{record.id}' references unknown evidence_ids: "
                    f"{', '.join(sorted(unknown))}"
                )
        return self


def _ensure_unique_ids(records: list[IdentifiedRecord], section: str) -> None:
    ids = [record.id for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{section} contains duplicate ids")


@dataclass(frozen=True)
class CareerDiagnostic:
    path: str
    message: str
    line: int | None = None
    column: int | None = None

    def format(self, file_path: Path) -> str:
        location = str(file_path)
        if self.line is not None:
            location += f":{self.line}:{self.column or 1}"
        return f"{location}: {self.path}: {self.message}"


def load_career(path: Path) -> CareerDocument:
    document = _load_yaml(path)
    return CareerDocument.model_validate(document)


def validate_career(path: Path) -> list[CareerDiagnostic]:
    try:
        document = _load_yaml(path)
    except (OSError, ValueError, YAMLError) as error:
        return [CareerDiagnostic("document", f"invalid YAML: {error}")]
    try:
        career = CareerDocument.model_validate(document)
    except ValidationError as error:
        return [_diagnostic_from_error(document, item) for item in error.errors()]

    diagnostics: list[CareerDiagnostic] = []
    for field in ("name", "title", "email"):
        if not getattr(career.profile, field).strip():
            diagnostics.append(
                _diagnostic_for_path(
                    document,
                    ("profile", field),
                    "is required; set it with 'career set-profile'",
                )
            )
    return diagnostics


def set_profile(path: Path, values: dict[str, Any]) -> None:
    document = _load_yaml(path)
    profile = document.setdefault("profile", CommentedMap())
    if not isinstance(profile, dict):
        raise ValueError("profile must be a mapping")
    updates = {key: value for key, value in values.items() if value is not None}
    if "links" in updates and isinstance(profile.get("links", {}), dict):
        updates["links"] = {**profile.get("links", {}), **updates["links"]}
    profile.update(updates)
    CareerDocument.model_validate(document)
    _write_yaml(path, document)


def add_record(path: Path, section: str, values: dict[str, Any]) -> None:
    if section not in {"experience", "education", "skills", "evidence"}:
        raise ValueError(f"Unsupported editable section: {section}")
    document = _load_yaml(path)
    records = document.setdefault(section, [])
    if not isinstance(records, list):
        raise ValueError(f"{section} must be a list")
    records.append(values)
    CareerDocument.model_validate(document)
    _write_yaml(path, document)


def list_section(path: Path, section: str) -> Any:
    career = load_career(path)
    if section not in CareerDocument.model_fields:
        raise ValueError(f"Unknown career section: {section}")
    return getattr(career, section)


def dump_section(value: Any) -> str:
    yaml = YAML()
    yaml.default_flow_style = False
    from io import StringIO

    stream = StringIO()
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
    elif isinstance(value, list):
        value = [
            item.model_dump(mode="python") if isinstance(item, BaseModel) else item
            for item in value
        ]
    yaml.dump(value, stream)
    return stream.getvalue()


def _load_yaml(path: Path) -> CommentedMap:
    yaml = YAML(typ="rt")
    document = yaml.load(path.read_text(encoding="utf-8"))
    if not isinstance(document, CommentedMap):
        raise ValueError(f"{CAREER_FILE} must contain a mapping")
    return document


def _write_yaml(path: Path, document: CommentedMap) -> None:
    yaml = YAML(typ="rt")
    from io import StringIO

    stream = StringIO()
    yaml.dump(document, stream)
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


def _diagnostic_from_error(document: Any, error: dict[str, Any]) -> CareerDiagnostic:
    location = tuple(error["loc"])
    return _diagnostic_for_path(document, location, error["msg"])


def _diagnostic_for_path(
    document: Any, location: tuple[Any, ...], message: str
) -> CareerDiagnostic:
    line = column = None
    current = document
    for part in location:
        try:
            position = (
                current.lc.item(part)
                if isinstance(part, int)
                else current.lc.key(part)
            )
            if position is not None:
                line, column = position[0] + 1, position[1] + 1
            current = current[part]
        except (AttributeError, KeyError, IndexError, TypeError):
            break
    path = ".".join(str(part) for part in location) or "document"
    return CareerDiagnostic(path, message, line, column)
