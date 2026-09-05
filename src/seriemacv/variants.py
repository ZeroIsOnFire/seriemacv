"""Structured resume variants and job-specific locale overrides."""

from __future__ import annotations

import re
from dataclasses import dataclass
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

from seriemacv.career import (
    CareerDocument,
    CareerFactsDocument,
    load_career,
    load_localized_career,
    validate_locale,
)
from seriemacv.jobs import job_path, validate_job
from seriemacv.styles import ResumeStyleId

VARIANTS_DIRECTORY = Path("resume") / "variants"
_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_LOCALE_PATTERN = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{2,8})*$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class VariantSelection(StrictModel):
    """Optional ordered selections; omitted sections inherit every canonical record."""

    experience: list[str] | None = None
    education: list[str] | None = None
    skills: list[str] | None = None

    @model_validator(mode="after")
    def ids_are_valid_and_unique(self) -> "VariantSelection":
        for section in ("experience", "education", "skills"):
            identifiers = getattr(self, section)
            if identifiers is None:
                continue
            invalid = [item for item in identifiers if not _ID_PATTERN.fullmatch(item)]
            if invalid:
                raise ValueError(f"{section} ids must use lowercase kebab-case")
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(f"{section} contains duplicate ids")
        return self


class ResumeVariant(StrictModel):
    schema_version: Literal[1]
    id: str = Field(min_length=1)
    job_id: str | None = None
    style: ResumeStyleId | None = None
    selection: VariantSelection = Field(default_factory=VariantSelection)

    @field_validator("id")
    @classmethod
    def stable_id(cls, value: str) -> str:
        if not _ID_PATTERN.fullmatch(value):
            raise ValueError("must use lowercase kebab-case")
        return value

    @field_validator("job_id")
    @classmethod
    def stable_job_id(cls, value: str | None) -> str | None:
        if value is not None and not _ID_PATTERN.fullmatch(value):
            raise ValueError("must use lowercase kebab-case")
        return value


class VariantProfileOverride(StrictModel):
    title: str | None = None


class VariantExperienceOverride(StrictModel):
    title: str | None = None
    location: str | None = None
    employment_type: str | None = None
    bullets: list[str] | None = None
    highlights: list[str] | None = Field(default=None, max_length=1)


class VariantEducationOverride(StrictModel):
    degree: str | None = None
    field_of_study: str | None = None
    location: str | None = None
    highlights: list[str] | None = None


class VariantSkillOverride(StrictModel):
    name: str | None = None
    category: str | None = None


class ResumeVariantLocale(StrictModel):
    """Partial editorial overrides layered on top of a static career locale."""

    schema_version: Literal[1]
    locale: str
    evidence_ids: list[str] = Field(default_factory=list)
    profile: VariantProfileOverride = Field(default_factory=VariantProfileOverride)
    summary: str | None = None
    experience: dict[str, VariantExperienceOverride] = Field(default_factory=dict)
    education: dict[str, VariantEducationOverride] = Field(default_factory=dict)
    skills: dict[str, VariantSkillOverride] = Field(default_factory=dict)

    @field_validator("locale")
    @classmethod
    def valid_locale(cls, value: str) -> str:
        if not _LOCALE_PATTERN.fullmatch(value):
            raise ValueError("must be a BCP 47 locale identifier")
        return value

    @field_validator("evidence_ids")
    @classmethod
    def unique_evidence_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("contains duplicate ids")
        return value

    @model_validator(mode="after")
    def tailored_claims_have_evidence(self) -> "ResumeVariantLocale":
        has_summary = self.summary is not None and bool(self.summary.strip())
        has_highlights = any(
            item.highlights
            for item in (*self.experience.values(), *self.education.values())
        )
        if (has_summary or has_highlights) and not self.evidence_ids:
            raise ValueError(
                "evidence_ids is required for a tailored summary or highlights"
            )
        return self


@dataclass(frozen=True)
class VariantDiagnostic:
    file_path: Path
    path: str
    message: str
    line: int | None = None
    column: int | None = None

    def format(self) -> str:
        location = str(self.file_path)
        if self.line is not None:
            location += f":{self.line}:{self.column or 1}"
        return f"{location}: {self.path}: {self.message}"


def variant_directory(project_path: Path, variant_id: str) -> Path:
    if not _ID_PATTERN.fullmatch(variant_id):
        raise ValueError("variant id must use lowercase kebab-case")
    return project_path / VARIANTS_DIRECTORY / variant_id


def load_variant(project_path: Path, variant_id: str) -> ResumeVariant:
    directory = variant_directory(project_path, variant_id)
    document = _load_yaml(directory / "variant.yml")
    variant = ResumeVariant.model_validate(document)
    if variant.id != variant_id:
        raise ValueError(
            f"variant document declares '{variant.id}', expected directory id '{variant_id}'"
        )
    return variant


def list_variant_locales(project_path: Path, variant_id: str) -> list[str]:
    directory = variant_directory(project_path, variant_id) / "locales"
    if not directory.is_dir():
        return []
    return sorted(
        path.stem
        for path in directory.glob("*.yml")
        if _LOCALE_PATTERN.fullmatch(path.stem)
    )


def list_variants(project_path: Path) -> list[ResumeVariant]:
    variants: list[ResumeVariant] = []
    for variant_id in _variant_ids(project_path):
        diagnostics = validate_variant(project_path, variant_id)
        if diagnostics:
            raise ValueError(diagnostics[0].format())
        variants.append(load_variant(project_path, variant_id))
    return variants


def validate_variants(project_path: Path) -> list[VariantDiagnostic]:
    diagnostics: list[VariantDiagnostic] = []
    for variant_id in _variant_ids(project_path):
        diagnostics.extend(validate_variant(project_path, variant_id))
    return diagnostics


def validate_variant(project_path: Path, variant_id: str) -> list[VariantDiagnostic]:
    try:
        directory = variant_directory(project_path, variant_id)
    except ValueError as error:
        return [VariantDiagnostic(project_path / VARIANTS_DIRECTORY, "id", str(error))]
    manifest_path = directory / "variant.yml"
    try:
        document = _load_yaml(manifest_path)
    except (OSError, ValueError, YAMLError) as error:
        return [VariantDiagnostic(manifest_path, "document", f"invalid YAML: {error}")]
    try:
        variant = ResumeVariant.model_validate(document)
    except ValidationError as error:
        return [
            _diagnostic_from_error(manifest_path, document, item)
            for item in error.errors()
        ]

    diagnostics: list[VariantDiagnostic] = []
    if variant.id != variant_id:
        diagnostics.append(
            VariantDiagnostic(
                manifest_path,
                "id",
                f"declares '{variant.id}', expected directory id '{variant_id}'",
            )
        )
    try:
        facts = load_career(project_path / "career.yml")
    except (OSError, ValueError, YAMLError, ValidationError) as error:
        diagnostics.append(
            VariantDiagnostic(project_path / "career.yml", "document", str(error))
        )
        return diagnostics

    diagnostics.extend(_validate_selection(manifest_path, variant, facts))
    if variant.job_id:
        selected_job_path = job_path(project_path, variant.job_id)
        if not selected_job_path.is_file():
            diagnostics.append(
                VariantDiagnostic(
                    manifest_path,
                    "job_id",
                    f"references unknown job_id '{variant.job_id}'",
                )
            )
        else:
            for item in validate_job(selected_job_path):
                diagnostics.append(
                    VariantDiagnostic(
                        selected_job_path,
                        item.path,
                        item.message,
                        item.line,
                        item.column,
                    )
                )

    locales_directory = directory / "locales"
    locale_files = (
        sorted(locales_directory.glob("*.yml")) if locales_directory.is_dir() else []
    )
    for locale_file in locale_files:
        locale = locale_file.stem
        if not _LOCALE_PATTERN.fullmatch(locale):
            diagnostics.append(
                VariantDiagnostic(
                    locale_file,
                    "locale",
                    "filename must be a BCP 47 locale identifier",
                )
            )
            continue
        for item in validate_locale(project_path, locale):
            diagnostics.append(
                VariantDiagnostic(
                    project_path / "career.locales" / f"{locale}.yml",
                    item.path,
                    item.message,
                    item.line,
                    item.column,
                )
            )
        diagnostics.extend(
            _validate_variant_locale(project_path, variant, facts, locale)
        )
    return diagnostics


def load_variant_career(
    project_path: Path, variant_id: str, locale: str
) -> tuple[ResumeVariant, CareerDocument]:
    diagnostics = validate_variant(project_path, variant_id)
    if diagnostics:
        raise ValueError(diagnostics[0].format())
    variant = load_variant(project_path, variant_id)
    career = load_localized_career(project_path, locale)
    override_path = (
        variant_directory(project_path, variant_id) / "locales" / f"{locale}.yml"
    )
    override = (
        ResumeVariantLocale.model_validate(_load_yaml(override_path))
        if override_path.is_file()
        else None
    )
    return variant, _compose_variant(career, variant, override)


def _compose_variant(
    career: CareerDocument,
    variant: ResumeVariant,
    override: ResumeVariantLocale | None,
) -> CareerDocument:
    experience = _select_records(career.experience, variant.selection.experience)
    education = _select_records(career.education, variant.selection.education)
    skills = _select_records(career.skills, variant.selection.skills)
    profile = career.profile
    summary = career.summary
    if override is not None:
        profile = profile.model_copy(
            update=override.profile.model_dump(exclude_none=True)
        )
        if override.summary is not None:
            summary = override.summary
        experience = _apply_record_overrides(experience, override.experience)
        education = _apply_record_overrides(education, override.education)
        skills = _apply_record_overrides(skills, override.skills)
    return career.model_copy(
        update={
            "profile": profile,
            "summary": summary,
            "experience": experience,
            "education": education,
            "skills": skills,
        }
    )


def _select_records(records: list[Any], identifiers: list[str] | None) -> list[Any]:
    if identifiers is None:
        return records
    by_id = {record.id: record for record in records}
    return [by_id[identifier] for identifier in identifiers]


def _apply_record_overrides(records: list[Any], overrides: dict[str, Any]) -> list[Any]:
    return [
        record.model_copy(update=overrides[record.id].model_dump(exclude_none=True))
        if record.id in overrides
        else record
        for record in records
    ]


def _validate_selection(
    path: Path, variant: ResumeVariant, facts: CareerFactsDocument
) -> list[VariantDiagnostic]:
    diagnostics: list[VariantDiagnostic] = []
    for section in ("experience", "education", "skills"):
        selected = getattr(variant.selection, section)
        if selected is None:
            continue
        known = {item.id for item in getattr(facts, section)}
        unknown = set(selected) - known
        if unknown:
            diagnostics.append(
                VariantDiagnostic(
                    path,
                    f"selection.{section}",
                    f"references unknown {section} ids: {', '.join(sorted(unknown))}",
                )
            )
    return diagnostics


def _validate_variant_locale(
    project_path: Path,
    variant: ResumeVariant,
    facts: CareerFactsDocument,
    locale: str,
) -> list[VariantDiagnostic]:
    path = variant_directory(project_path, variant.id) / "locales" / f"{locale}.yml"
    try:
        document = _load_yaml(path)
    except (OSError, ValueError, YAMLError) as error:
        return [VariantDiagnostic(path, "document", f"invalid YAML: {error}")]
    try:
        override = ResumeVariantLocale.model_validate(document)
    except ValidationError as error:
        return [_diagnostic_from_error(path, document, item) for item in error.errors()]

    diagnostics: list[VariantDiagnostic] = []
    if override.locale != locale:
        diagnostics.append(
            VariantDiagnostic(
                path,
                "locale",
                f"declares '{override.locale}', expected filename locale '{locale}'",
            )
        )
    evidence_ids = {item.id for item in facts.evidence}
    unknown_evidence = set(override.evidence_ids) - evidence_ids
    if unknown_evidence:
        diagnostics.append(
            VariantDiagnostic(
                path,
                "evidence_ids",
                f"references unknown evidence_ids: {', '.join(sorted(unknown_evidence))}",
            )
        )
    unverified_evidence = {
        item.id
        for item in facts.evidence
        if item.id in override.evidence_ids and not item.verified
    }
    if unverified_evidence:
        diagnostics.append(
            VariantDiagnostic(
                path,
                "evidence_ids",
                "references unverified evidence_ids: "
                f"{', '.join(sorted(unverified_evidence))}",
            )
        )
    for section in ("experience", "education", "skills"):
        known = {item.id for item in getattr(facts, section)}
        selected = getattr(variant.selection, section)
        if selected is not None:
            known &= set(selected)
        unknown = set(getattr(override, section)) - known
        if unknown:
            diagnostics.append(
                VariantDiagnostic(
                    path,
                    section,
                    f"references unavailable {section} ids: {', '.join(sorted(unknown))}",
                )
            )
    return diagnostics


def _variant_ids(project_path: Path) -> list[str]:
    root = project_path / VARIANTS_DIRECTORY
    if not root.is_dir():
        return []
    return sorted(
        path.name
        for path in root.iterdir()
        if path.is_dir() and (path / "variant.yml").is_file()
    )


def _load_yaml(path: Path) -> CommentedMap:
    yaml = YAML(typ="rt")
    document = yaml.load(path.read_text(encoding="utf-8"))
    if not isinstance(document, CommentedMap):
        raise ValueError(f"{path.name} must contain a mapping")
    return document


def _diagnostic_from_error(
    path: Path, document: Any, error: dict[str, Any]
) -> VariantDiagnostic:
    location = tuple(error["loc"])
    line = column = None
    current = document
    for part in location:
        try:
            position = (
                current.lc.item(part) if isinstance(part, int) else current.lc.key(part)
            )
            if position is not None:
                line, column = position[0] + 1, position[1] + 1
            current = current[part]
        except (AttributeError, KeyError, IndexError, TypeError):
            break
    dotted_path = ".".join(str(part) for part in location) or "document"
    return VariantDiagnostic(path, dotted_path, error["msg"], line, column)
