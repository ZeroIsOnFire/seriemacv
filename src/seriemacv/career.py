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

from seriemacv.i18n import translate

CAREER_FILE = "career.yml"
LOCALES_DIRECTORY = "career.locales"
I18N_DIRECTORY = "i18n"
_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_YEAR_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_LOCALE_PATTERN = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{2,8})*$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CareerProfile(StrictModel):
    name: str = ""
    title: str = ""
    location: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    portfolio: str = ""
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

    @field_validator("linkedin", "portfolio")
    @classmethod
    def profile_urls(cls, value: str) -> str:
        if not value:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("must be an http(s) URL")
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
    bullets: list[str] = Field(default_factory=list)
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
    level: Literal["beginner", "intermediate", "advanced", "expert"] | None = None
    core: bool = False


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
    evidence_ids: list[str] = Field(default_factory=list)
    sensitive: bool = False
    role_scope: list[str] = Field(default_factory=list)
    language_scope: list[str] = Field(default_factory=list)

    @field_validator("evidence_ids")
    @classmethod
    def unique_evidence_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("contains duplicate ids")
        return value

    @field_validator("role_scope", "language_scope")
    @classmethod
    def valid_answer_scope(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("contains duplicate scopes")
        if invalid := [item for item in value if not _ID_PATTERN.fullmatch(item)]:
            raise ValueError(f"contains invalid scopes: {', '.join(invalid)}")
        return value


class CareerStory(IdentifiedRecord):
    title: str = Field(min_length=1)
    situation: str = ""
    action: str = ""
    result: str = ""
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("evidence_ids")
    @classmethod
    def unique_evidence_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("contains duplicate ids")
        return value


class CareerDocument(StrictModel):
    """The fully localized document consumed by resume renderers."""

    schema_version: Literal[1, 2]
    profile: CareerProfile = Field(default_factory=CareerProfile)
    summary: str = ""
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    evidence: list[CareerEvidence] = Field(default_factory=list)
    answers: list[SavedAnswer] = Field(default_factory=list)
    stories: list[CareerStory] = Field(default_factory=list)
    catalog: "LocaleCatalog | None" = None

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
        _ensure_verified_evidence_references(
            self.answers, self.stories, self.evidence, evidence_ids
        )
        return self


class CareerFactsProfile(StrictModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    portfolio: str = ""
    links: dict[str, str] = Field(default_factory=dict)

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

    @field_validator("linkedin", "portfolio")
    @classmethod
    def profile_urls(cls, value: str) -> str:
        if not value:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("must be an http(s) URL")
        return value


class FactExperience(DatedRecord):
    company: str = Field(min_length=1)


class FactEducation(DatedRecord):
    institution: str = Field(min_length=1)


class FactSkill(IdentifiedRecord):
    tags: list[str] = Field(default_factory=list)
    level: Literal["beginner", "intermediate", "advanced", "expert"] | None = None
    core: bool = False


class CareerFactsDocument(StrictModel):
    """Language-independent, user-owned career facts (schema version 2)."""

    schema_version: Literal[2]
    profile: CareerFactsProfile = Field(default_factory=CareerFactsProfile)
    experience: list[FactExperience] = Field(default_factory=list)
    education: list[FactEducation] = Field(default_factory=list)
    skills: list[FactSkill] = Field(default_factory=list)
    evidence: list[CareerEvidence] = Field(default_factory=list)
    answers: list[SavedAnswer] = Field(default_factory=list)
    stories: list[CareerStory] = Field(default_factory=list)

    @model_validator(mode="after")
    def references_are_valid(self) -> "CareerFactsDocument":
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
                raise ValueError(f"evidence '{record.id}' references unknown experience_id '{record.experience_id}'")
        _ensure_verified_evidence_references(
            self.answers, self.stories, self.evidence, evidence_ids
        )
        return self


def _ensure_verified_evidence_references(
    answers: list[SavedAnswer],
    stories: list[CareerStory],
    evidence: list[CareerEvidence],
    evidence_ids: set[str],
) -> None:
    verified_evidence_ids = {record.id for record in evidence if record.verified}
    for section, records in (("answer", answers), ("story", stories)):
        for record in records:
            references = set(record.evidence_ids)
            unknown = references - evidence_ids
            if unknown:
                raise ValueError(
                    f"{section} '{record.id}' references unknown evidence_ids: "
                    f"{', '.join(sorted(unknown))}"
                )
            unverified = references - verified_evidence_ids
            if unverified:
                raise ValueError(
                    f"{section} '{record.id}' references unverified evidence_ids: "
                    f"{', '.join(sorted(unverified))}"
                )


class LocaleCatalog(StrictModel):
    labels: dict[str, str]
    months: list[str] = Field(min_length=12, max_length=12)
    date_format: str = "{month} {year}"

    @model_validator(mode="after")
    def complete_labels_and_date_format(self) -> "LocaleCatalog":
        required = {"summary", "experience", "education", "skills", "languages", "current", "other", "level.beginner", "level.intermediate", "level.advanced", "level.expert"}
        missing = required - set(self.labels)
        if missing:
            raise ValueError(f"labels is missing required keys: {', '.join(sorted(missing))}")
        if "{month}" not in self.date_format or "{year}" not in self.date_format:
            raise ValueError("date_format must contain {month} and {year}")
        return self


class I18nDocument(LocaleCatalog):
    """Project-owned translations for labels, months, and date formatting."""

    schema_version: Literal[1]
    locale: str

    @field_validator("locale")
    @classmethod
    def valid_locale(cls, value: str) -> str:
        if not _LOCALE_PATTERN.fullmatch(value):
            raise ValueError("must be a BCP 47 locale identifier")
        return value


class LocalizedProfile(StrictModel):
    title: str = ""
    location: str = ""
    languages: list[str] = Field(default_factory=list)
    work_preference: str = ""
    work_authorization: str = ""
    notice_period: str = ""


class LocalizedExperience(StrictModel):
    title: str = ""
    location: str = ""
    employment_type: str = ""
    bullets: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class LocalizedEducation(StrictModel):
    degree: str = ""
    field_of_study: str = ""
    location: str = ""
    highlights: list[str] = Field(default_factory=list)


class LocalizedSkill(StrictModel):
    name: str = ""
    category: str = ""


class CareerLocaleDocument(StrictModel):
    schema_version: Literal[1]
    locale: str
    profile: LocalizedProfile = Field(default_factory=LocalizedProfile)
    summary: str = ""
    experience: dict[str, LocalizedExperience] = Field(default_factory=dict)
    education: dict[str, LocalizedEducation] = Field(default_factory=dict)
    skills: dict[str, LocalizedSkill] = Field(default_factory=dict)

    @field_validator("locale")
    @classmethod
    def valid_locale(cls, value: str) -> str:
        if not _LOCALE_PATTERN.fullmatch(value):
            raise ValueError("must be a BCP 47 locale identifier")
        return value


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


def load_career(path: Path) -> CareerFactsDocument:
    """Load v2 canonical facts.

    Use :func:`load_localized_career` when a renderable document is required.
    """
    document = _load_yaml(path)
    return CareerFactsDocument.model_validate(document)


def validate_career(path: Path) -> list[CareerDiagnostic]:
    try:
        document = _load_yaml(path)
    except (OSError, ValueError, YAMLError) as error:
        return [CareerDiagnostic("document", f"invalid YAML: {error}")]
    try:
        career = CareerFactsDocument.model_validate(document)
    except ValidationError as error:
        return [_diagnostic_from_error(document, item) for item in error.errors()]

    diagnostics: list[CareerDiagnostic] = []
    for field in ("name", "email"):
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
    CareerFactsDocument.model_validate(document)
    _write_yaml(path, document)


def add_record(path: Path, section: str, values: dict[str, Any]) -> None:
    if section not in {"experience", "education", "skills", "evidence", "answers", "stories"}:
        raise ValueError(f"Unsupported editable section: {section}")
    document = _load_yaml(path)
    records = document.setdefault(section, [])
    if not isinstance(records, list):
        raise ValueError(f"{section} must be a list")
    records.append(values)
    CareerFactsDocument.model_validate(document)
    _write_yaml(path, document)


def list_section(path: Path, section: str) -> Any:
    career = load_career(path)
    if section not in CareerFactsDocument.model_fields:
        raise ValueError(f"Unknown career section: {section}")
    return getattr(career, section)


def locale_path(project_path: Path, locale: str) -> Path:
    if not _LOCALE_PATTERN.fullmatch(locale):
        raise ValueError(f"Invalid locale identifier: {locale}")
    return project_path / LOCALES_DIRECTORY / f"{locale}.yml"


def list_locales(project_path: Path) -> list[str]:
    directory = project_path / LOCALES_DIRECTORY
    if not directory.is_dir():
        return []
    return sorted(path.stem for path in directory.glob("*.yml") if _LOCALE_PATTERN.fullmatch(path.stem))


def i18n_path(project_path: Path, locale: str) -> Path:
    if not _LOCALE_PATTERN.fullmatch(locale):
        raise ValueError(f"Invalid locale identifier: {locale}")
    return project_path / I18N_DIRECTORY / f"{locale}.yml"


def load_i18n_catalog(
    project_path: Path,
    locale: str,
) -> LocaleCatalog:
    path = i18n_path(project_path, locale)
    if path.is_file():
        document = I18nDocument.model_validate(_load_yaml(path))
        if document.locale != locale:
            raise ValueError(
                f"i18n document declares '{document.locale}', expected '{locale}'"
            )
        return LocaleCatalog.model_validate(
            document.model_dump(exclude={"schema_version", "locale"})
        )
    raise ValueError(f"i18n document is missing: {path.relative_to(project_path)}")


def load_localized_career(project_path: Path, locale: str) -> CareerDocument:
    facts = CareerFactsDocument.model_validate(_load_yaml(project_path / CAREER_FILE))
    path = locale_path(project_path, locale)
    if not path.is_file():
        raise ValueError(f"Locale document is missing: {path.relative_to(project_path)}")
    translated = CareerLocaleDocument.model_validate(_load_yaml(path))
    if translated.locale != locale:
        raise ValueError(f"locale document declares '{translated.locale}', expected '{locale}'")
    _ensure_locale_references(facts, translated)
    catalog = load_i18n_catalog(project_path, locale)
    labels = dict(catalog.labels)
    labels.setdefault(
        "highlight",
        translate(locale, "highlight") if locale in {"pt-BR", "en"} else "Highlight",
    )
    catalog = catalog.model_copy(update={"labels": labels})
    return CareerDocument.model_validate({
        "schema_version": 2,
        "profile": {**facts.profile.model_dump(), **translated.profile.model_dump()},
        "summary": translated.summary,
        "experience": [
            {**item.model_dump(), **translated.experience[item.id].model_dump()}
            for item in facts.experience
        ],
        "education": [
            {**item.model_dump(), **translated.education[item.id].model_dump()}
            for item in facts.education
        ],
        "skills": [
            {**item.model_dump(), **translated.skills[item.id].model_dump()}
            for item in facts.skills
        ],
        "evidence": [item.model_dump() for item in facts.evidence],
        "answers": [item.model_dump() for item in facts.answers],
        "stories": [item.model_dump() for item in facts.stories],
        "catalog": catalog.model_dump(),
    })


def validate_locale(project_path: Path, locale: str) -> list[CareerDiagnostic]:
    try:
        load_localized_career(project_path, locale)
    except (OSError, ValueError, YAMLError, ValidationError) as error:
        return [CareerDiagnostic("document", str(error))]
    return []


def _ensure_locale_references(facts: CareerFactsDocument, locale: CareerLocaleDocument) -> None:
    for name, source, translated in (
        ("experience", facts.experience, locale.experience),
        ("education", facts.education, locale.education),
        ("skills", facts.skills, locale.skills),
    ):
        source_ids = {item.id for item in source}
        unknown = set(translated) - source_ids
        missing = source_ids - set(translated)
        if unknown:
            raise ValueError(f"locale {name} references unknown ids: {', '.join(sorted(unknown))}")
        if missing:
            raise ValueError(f"locale {name} is missing ids: {', '.join(sorted(missing))}")
    if not locale.profile.title.strip():
        raise ValueError("profile.title is required in every locale")
    for item in facts.experience:
        if not locale.experience[item.id].title.strip():
            raise ValueError(f"experience '{item.id}' title is required in every locale")
    for item in facts.education:
        if not locale.education[item.id].degree.strip():
            raise ValueError(f"education '{item.id}' degree is required in every locale")
    for item in facts.skills:
        if not locale.skills[item.id].name.strip():
            raise ValueError(f"skill '{item.id}' name is required in every locale")


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
