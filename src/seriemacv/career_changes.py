"""Typed, reviewable edits for canonical career and localized YAML documents."""

from __future__ import annotations

import copy
import os
import tempfile
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from seriemacv.applications import ApplicationDocument
from seriemacv.career import (
    CareerEvidence,
    CareerFactsDocument,
    CareerLocaleDocument,
    CareerStory,
    FactEducation,
    FactExperience,
    FactSkill,
    SavedAnswer,
    list_locales,
)
from seriemacv.variants import ResumeVariant, ResumeVariantLocale

CareerSection = Literal[
    "experience", "education", "skills", "evidence", "answers", "stories"
]
LocalizedSection = Literal["profile", "summary", "experience", "education", "skills"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ProfilePatch(StrictModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    portfolio: str | None = None
    links: dict[str, str] | None = None

    @model_validator(mode="after")
    def has_update(self) -> "ProfilePatch":
        if not self.model_dump(exclude_none=True):
            raise ValueError("profile update requires at least one field")
        return self


class ProfileUpdate(StrictModel):
    kind: Literal["profile_update"]
    values: ProfilePatch


class RecordCreate(StrictModel):
    kind: Literal["record_create"]
    section: CareerSection
    record: dict[str, Any]
    locales: dict[str, dict[str, Any]] = Field(default_factory=dict)


class RecordUpdate(StrictModel):
    kind: Literal["record_update"]
    section: CareerSection
    id: str
    values: dict[str, Any]
    locales: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def immutable_id_and_nonempty_change(self) -> "RecordUpdate":
        if "id" in self.values:
            raise ValueError("record ids are immutable")
        if not self.values and not self.locales:
            raise ValueError("record update requires values or locales")
        return self


class RecordDelete(StrictModel):
    kind: Literal["record_delete"]
    section: CareerSection
    id: str


class LocaleUpdate(StrictModel):
    kind: Literal["locale_update"]
    locale: str
    section: LocalizedSection
    values: dict[str, Any]
    record_id: str | None = None

    @model_validator(mode="after")
    def target_shape(self) -> "LocaleUpdate":
        record_section = self.section in {"experience", "education", "skills"}
        if record_section != (self.record_id is not None):
            raise ValueError("record_id is required only for localized record sections")
        if self.section == "summary" and set(self.values) != {"value"}:
            raise ValueError("summary update requires only a value field")
        if not self.values:
            raise ValueError("locale update requires values")
        return self


CareerOperation = Annotated[
    Union[ProfileUpdate, RecordCreate, RecordUpdate, RecordDelete, LocaleUpdate],
    Field(discriminator="kind"),
]


class CareerChange(StrictModel):
    operations: list[CareerOperation] = Field(min_length=1)


@dataclass(frozen=True)
class CareerDiff:
    path: str
    before: Any
    after: Any


@dataclass(frozen=True)
class CareerChangePlan:
    changes: dict[Path, str]
    diff: list[CareerDiff]


_RECORD_MODELS: dict[str, type[BaseModel]] = {
    "experience": FactExperience,
    "education": FactEducation,
    "skills": FactSkill,
    "evidence": CareerEvidence,
    "answers": SavedAnswer,
    "stories": CareerStory,
}


def plan_career_change(project_path: Path, change: CareerChange) -> CareerChangePlan:
    """Validate a typed change and render every affected YAML file in memory."""
    project_path = project_path.resolve()
    documents: dict[Path, CommentedMap] = {}
    originals: dict[Path, str] = {}
    changed: set[Path] = set()
    diffs: list[CareerDiff] = []

    career_path = project_path / "career.yml"
    career = _document(career_path, documents, originals)
    locale_documents = {
        locale: _document(
            project_path / "career.locales" / f"{locale}.yml",
            documents,
            originals,
        )
        for locale in list_locales(project_path)
    }

    for operation in change.operations:
        if isinstance(operation, ProfileUpdate):
            profile = career.setdefault("profile", CommentedMap())
            before = copy.deepcopy(dict(profile))
            values = operation.values.model_dump(exclude_none=True)
            if "links" in values:
                values["links"] = {**profile.get("links", {}), **values["links"]}
            profile.update(values)
            if dict(profile) != before:
                changed.add(career_path)
                diffs.append(CareerDiff("career.yml::profile", before, dict(profile)))
        elif isinstance(operation, RecordCreate):
            _create_record(
                project_path,
                career,
                career_path,
                locale_documents,
                operation,
                changed,
                diffs,
            )
        elif isinstance(operation, RecordUpdate):
            _update_record(
                project_path,
                career,
                career_path,
                locale_documents,
                operation,
                changed,
                diffs,
            )
        elif isinstance(operation, RecordDelete):
            _delete_record(
                project_path,
                career,
                career_path,
                locale_documents,
                operation,
                documents,
                originals,
                changed,
                diffs,
            )
        else:
            _update_locale(
                project_path,
                locale_documents,
                operation,
                changed,
                diffs,
            )

    facts = CareerFactsDocument.model_validate(career)
    _validate_locales(facts, locale_documents)
    _validate_variants(project_path, facts, documents, originals)
    _validate_applications(project_path, facts, documents, originals)

    changes = {
        path: content
        for path, document in documents.items()
        if path in changed and (content := _dump(document)) != originals[path]
    }
    changed_files = {path.relative_to(project_path).as_posix() for path in changes}
    return CareerChangePlan(
        changes=changes,
        diff=[item for item in diffs if item.path.split("::", 1)[0] in changed_files],
    )


def apply_career_change(plan: CareerChangePlan) -> list[Path]:
    """Atomically replace each prevalidated file; caller owns multifile rollback."""
    for path, content in plan.changes.items():
        _atomic_write(path, content)
    return list(plan.changes)


def _create_record(
    project_path: Path,
    career: CommentedMap,
    career_path: Path,
    locale_documents: dict[str, CommentedMap],
    operation: RecordCreate,
    changed: set[Path],
    diffs: list[CareerDiff],
) -> None:
    model = _RECORD_MODELS[operation.section]
    record = model.model_validate(operation.record).model_dump(mode="python")
    records = career.setdefault(operation.section, [])
    if any(item.get("id") == record["id"] for item in records):
        raise ValueError(f"{operation.section} already contains id '{record['id']}'")
    localized = operation.section in {"experience", "education", "skills"}
    if localized and set(operation.locales) != set(locale_documents):
        raise ValueError(
            f"new {operation.section} requires localized values for every locale"
        )
    if not localized and operation.locales:
        raise ValueError(f"{operation.section} does not accept localized values")
    records.append(CommentedMap(record))
    changed.add(career_path)
    diffs.append(
        CareerDiff(f"career.yml::{operation.section}.{record['id']}", None, record)
    )
    for locale, values in operation.locales.items():
        document = locale_documents[locale]
        document.setdefault(operation.section, CommentedMap())[record["id"]] = (
            CommentedMap(values)
        )
        path = project_path / "career.locales" / f"{locale}.yml"
        changed.add(path)
        diffs.append(
            CareerDiff(
                f"{path.relative_to(project_path).as_posix()}::{operation.section}.{record['id']}",
                None,
                values,
            )
        )


def _update_record(
    project_path: Path,
    career: CommentedMap,
    career_path: Path,
    locale_documents: dict[str, CommentedMap],
    operation: RecordUpdate,
    changed: set[Path],
    diffs: list[CareerDiff],
) -> None:
    if operation.locales and operation.section not in {
        "experience",
        "education",
        "skills",
    }:
        raise ValueError(f"{operation.section} does not accept localized values")
    record = _find_record(career, operation.section, operation.id)
    before = copy.deepcopy(dict(record))
    proposed = {**record, **operation.values}
    _RECORD_MODELS[operation.section].model_validate(proposed)
    record.update(operation.values)
    if dict(record) != before:
        changed.add(career_path)
        diffs.append(
            CareerDiff(
                f"career.yml::{operation.section}.{operation.id}",
                before,
                dict(record),
            )
        )
    for locale, values in operation.locales.items():
        if locale not in locale_documents:
            raise ValueError(f"unknown locale: {locale}")
        localized = locale_documents[locale].get(operation.section)
        if not isinstance(localized, dict) or operation.id not in localized:
            raise ValueError(
                f"locale {locale} has no {operation.section} '{operation.id}'"
            )
        localized_record = localized[operation.id]
        localized_before = copy.deepcopy(dict(localized_record))
        localized_record.update(values)
        path = project_path / "career.locales" / f"{locale}.yml"
        if dict(localized_record) != localized_before:
            changed.add(path)
            diffs.append(
                CareerDiff(
                    f"{path.relative_to(project_path).as_posix()}::{operation.section}.{operation.id}",
                    localized_before,
                    dict(localized_record),
                )
            )


def _delete_record(
    project_path: Path,
    career: CommentedMap,
    career_path: Path,
    locale_documents: dict[str, CommentedMap],
    operation: RecordDelete,
    documents: dict[Path, CommentedMap],
    originals: dict[Path, str],
    changed: set[Path],
    diffs: list[CareerDiff],
) -> None:
    records = career.get(operation.section, [])
    index = next(
        (index for index, item in enumerate(records) if item.get("id") == operation.id),
        None,
    )
    if index is None:
        raise ValueError(f"unknown {operation.section} id: {operation.id}")
    before = copy.deepcopy(dict(records[index]))
    del records[index]
    changed.add(career_path)
    diffs.append(
        CareerDiff(f"career.yml::{operation.section}.{operation.id}", before, None)
    )

    if operation.section in {"experience", "education", "skills"}:
        for locale, document in locale_documents.items():
            localized = document.get(operation.section, {})
            removed = localized.pop(operation.id, None)
            if removed is not None:
                path = project_path / "career.locales" / f"{locale}.yml"
                changed.add(path)
                diffs.append(
                    CareerDiff(
                        f"{path.relative_to(project_path).as_posix()}::{operation.section}.{operation.id}",
                        dict(removed),
                        None,
                    )
                )
        _cascade_variants(
            project_path,
            operation.section,
            operation.id,
            set(),
            documents,
            originals,
            changed,
            diffs,
        )

    evidence_ids: set[str] = set()
    if operation.section == "experience":
        evidence = career.get("evidence", [])
        retained = []
        for item in evidence:
            if item.get("experience_id") == operation.id:
                evidence_ids.add(str(item["id"]))
                diffs.append(
                    CareerDiff(f"career.yml::evidence.{item['id']}", dict(item), None)
                )
            else:
                retained.append(item)
        career["evidence"] = retained
    elif operation.section == "evidence":
        evidence_ids.add(operation.id)
    if evidence_ids:
        _cascade_evidence(
            project_path,
            career,
            evidence_ids,
            documents,
            originals,
            changed,
            diffs,
        )
    if operation.section == "answers":
        _cascade_saved_answer(
            project_path,
            operation.id,
            documents,
            originals,
            changed,
            diffs,
        )


def _update_locale(
    project_path: Path,
    locale_documents: dict[str, CommentedMap],
    operation: LocaleUpdate,
    changed: set[Path],
    diffs: list[CareerDiff],
) -> None:
    if operation.locale not in locale_documents:
        raise ValueError(f"unknown locale: {operation.locale}")
    document = locale_documents[operation.locale]
    path = project_path / "career.locales" / f"{operation.locale}.yml"
    if operation.section == "summary":
        before = document.get("summary", "")
        document["summary"] = operation.values["value"]
        after: Any = document["summary"]
        target = "summary"
    elif operation.section == "profile":
        profile = document.setdefault("profile", CommentedMap())
        before = copy.deepcopy(dict(profile))
        profile.update(operation.values)
        after = dict(profile)
        target = "profile"
    else:
        records = document.get(operation.section, {})
        if operation.record_id not in records:
            raise ValueError(
                f"locale {operation.locale} has no {operation.section} '{operation.record_id}'"
            )
        record = records[operation.record_id]
        before = copy.deepcopy(dict(record))
        record.update(operation.values)
        after = dict(record)
        target = f"{operation.section}.{operation.record_id}"
    if before != after:
        changed.add(path)
        diffs.append(
            CareerDiff(
                f"{path.relative_to(project_path).as_posix()}::{target}",
                before,
                after,
            )
        )


def _cascade_evidence(
    project_path: Path,
    career: CommentedMap,
    evidence_ids: set[str],
    documents: dict[Path, CommentedMap],
    originals: dict[Path, str],
    changed: set[Path],
    diffs: list[CareerDiff],
) -> None:
    for section in ("answers", "stories"):
        for record in career.get(section, []):
            before = list(record.get("evidence_ids", []))
            after = [item for item in before if item not in evidence_ids]
            if after != before:
                record["evidence_ids"] = after
                diffs.append(
                    CareerDiff(
                        f"career.yml::{section}.{record['id']}.evidence_ids",
                        before,
                        after,
                    )
                )
    _cascade_variants(
        project_path,
        "evidence",
        "",
        evidence_ids,
        documents,
        originals,
        changed,
        diffs,
    )


def _cascade_variants(
    project_path: Path,
    section: str,
    record_id: str,
    evidence_ids: set[str],
    documents: dict[Path, CommentedMap],
    originals: dict[Path, str],
    changed: set[Path],
    diffs: list[CareerDiff],
) -> None:
    root = project_path / "resume" / "variants"
    for path in sorted(root.glob("*/variant.yml")):
        document = _document(path, documents, originals)
        selected = document.get("selection", {}).get(section)
        if isinstance(selected, list) and record_id in selected:
            before = list(selected)
            selected.remove(record_id)
            changed.add(path)
            diffs.append(
                CareerDiff(
                    f"{path.relative_to(project_path).as_posix()}::selection.{section}",
                    before,
                    list(selected),
                )
            )
    for path in sorted(root.glob("*/locales/*.yml")):
        document = _document(path, documents, originals)
        if section in {"experience", "education", "skills"}:
            overrides = document.get(section, {})
            removed = overrides.pop(record_id, None)
            if removed is not None:
                changed.add(path)
                diffs.append(
                    CareerDiff(
                        f"{path.relative_to(project_path).as_posix()}::{section}.{record_id}",
                        dict(removed),
                        None,
                    )
                )
        if evidence_ids:
            before = list(document.get("evidence_ids", []))
            after = [item for item in before if item not in evidence_ids]
            if after != before:
                document["evidence_ids"] = after
                if not after:
                    document.pop("summary", None)
                    for localized_section in ("experience", "education"):
                        for override in document.get(localized_section, {}).values():
                            override.pop("highlights", None)
                changed.add(path)
                diffs.append(
                    CareerDiff(
                        f"{path.relative_to(project_path).as_posix()}::evidence_ids",
                        before,
                        after,
                    )
                )


def _cascade_saved_answer(
    project_path: Path,
    answer_id: str,
    documents: dict[Path, CommentedMap],
    originals: dict[Path, str],
    changed: set[Path],
    diffs: list[CareerDiff],
) -> None:
    for path in sorted((project_path / "applications").glob("*.yml")):
        document = _document(path, documents, originals)
        for answer in document.get("answers", []):
            if answer.get("saved_answer_id") == answer_id:
                answer["saved_answer_id"] = None
                changed.add(path)
                diffs.append(
                    CareerDiff(
                        f"{path.relative_to(project_path).as_posix()}::answers.{answer.get('field_id')}.saved_answer_id",
                        answer_id,
                        None,
                    )
                )


def _validate_locales(
    facts: CareerFactsDocument, locale_documents: dict[str, CommentedMap]
) -> None:
    expected = {
        "experience": {item.id for item in facts.experience},
        "education": {item.id for item in facts.education},
        "skills": {item.id for item in facts.skills},
    }
    for locale, raw in locale_documents.items():
        document = CareerLocaleDocument.model_validate(raw)
        if document.locale != locale:
            raise ValueError(
                f"locale document declares '{document.locale}', expected '{locale}'"
            )
        for section, identifiers in expected.items():
            localized = getattr(document, section)
            if set(localized) != identifiers:
                raise ValueError(
                    f"locale {locale} {section} ids do not match career.yml"
                )
        if not document.profile.title.strip():
            raise ValueError(f"locale {locale} profile.title is required")
        for experience in facts.experience:
            if not document.experience[experience.id].title.strip():
                raise ValueError(
                    f"locale {locale} experience '{experience.id}' title is required"
                )
        for education in facts.education:
            if not document.education[education.id].degree.strip():
                raise ValueError(
                    f"locale {locale} education '{education.id}' degree is required"
                )
        for skill in facts.skills:
            if not document.skills[skill.id].name.strip():
                raise ValueError(f"locale {locale} skill '{skill.id}' name is required")


def _validate_variants(
    project_path: Path,
    facts: CareerFactsDocument,
    documents: dict[Path, CommentedMap],
    originals: dict[Path, str],
) -> None:
    known = {
        "experience": {item.id for item in facts.experience},
        "education": {item.id for item in facts.education},
        "skills": {item.id for item in facts.skills},
    }
    verified = {item.id for item in facts.evidence if item.verified}
    root = project_path / "resume" / "variants"
    for path in sorted(root.glob("*/variant.yml")):
        variant = ResumeVariant.model_validate(_document(path, documents, originals))
        for section, identifiers in known.items():
            selected = getattr(variant.selection, section)
            unknown = set(selected or []) - identifiers
            if unknown:
                unknown_list = ", ".join(sorted(unknown))
                raise ValueError(
                    f"variant {variant.id} references unknown {section}: {unknown_list}"
                )
    for path in sorted(root.glob("*/locales/*.yml")):
        locale = ResumeVariantLocale.model_validate(
            _document(path, documents, originals)
        )
        unknown_evidence = set(locale.evidence_ids) - verified
        if unknown_evidence:
            unknown_list = ", ".join(sorted(unknown_evidence))
            raise ValueError(
                f"variant locale references unknown evidence: {unknown_list}"
            )
        for section in ("experience", "education", "skills"):
            unknown = set(getattr(locale, section)) - known[section]
            if unknown:
                unknown_list = ", ".join(sorted(unknown))
                raise ValueError(
                    f"variant locale references unknown {section}: {unknown_list}"
                )


def _validate_applications(
    project_path: Path,
    facts: CareerFactsDocument,
    documents: dict[Path, CommentedMap],
    originals: dict[Path, str],
) -> None:
    answer_ids = {item.id for item in facts.answers}
    for path in sorted((project_path / "applications").glob("*.yml")):
        application = ApplicationDocument.model_validate(
            _document(path, documents, originals)
        )
        for answer in application.answers:
            if answer.saved_answer_id and answer.saved_answer_id not in answer_ids:
                raise ValueError(
                    f"application {application.id} references unknown saved answer"
                )


def _find_record(document: CommentedMap, section: str, record_id: str) -> CommentedMap:
    for item in document.get(section, []):
        if item.get("id") == record_id:
            return item
    raise ValueError(f"unknown {section} id: {record_id}")


def _document(
    path: Path,
    documents: dict[Path, CommentedMap],
    originals: dict[Path, str],
) -> CommentedMap:
    if path not in documents:
        text = path.read_text(encoding="utf-8")
        value = YAML(typ="rt").load(text)
        if not isinstance(value, CommentedMap):
            raise ValueError(f"{path.name} must contain a mapping")
        documents[path] = value
        originals[path] = text
    return documents[path]


def _dump(document: CommentedMap) -> str:
    stream = StringIO()
    YAML(typ="rt").dump(document, stream)
    return stream.getvalue()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(content)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
