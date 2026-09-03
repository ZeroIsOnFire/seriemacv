"""Canonical, reviewable application records and question workflow."""

from __future__ import annotations

import os
import re
import tempfile
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from seriemacv.career import add_record, load_career
from seriemacv.jobs import job_path, load_job
from seriemacv.variants import load_variant

APPLICATIONS_DIRECTORY = "applications"
_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ApplicationStatus = Literal[
    "saved", "preparing", "needs_user_input", "ready_for_review", "applied",
    "recruiter", "interview", "offer", "rejected", "withdrawn",
]
_TRANSITIONS: dict[str, set[str]] = {
    "saved": {"preparing", "withdrawn"},
    "preparing": {"needs_user_input", "ready_for_review", "withdrawn"},
    "needs_user_input": {"preparing", "ready_for_review", "withdrawn"},
    "ready_for_review": {"preparing", "applied", "withdrawn"},
    "applied": {"recruiter", "interview", "offer", "rejected", "withdrawn"},
    "recruiter": {"interview", "offer", "rejected", "withdrawn"},
    "interview": {"offer", "rejected", "withdrawn"},
    "offer": {"withdrawn"}, "rejected": set(), "withdrawn": set(),
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ApplicationAnswer(StrictModel):
    field_id: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    saved_answer_id: str | None = None
    sensitive: bool = False
    confirmed_for_application: bool = False


class ApplicationQuestion(StrictModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    context: str = ""
    required: bool = True
    sensitive: bool = False
    field_id: str = Field(min_length=1)
    proposed_answer: str | None = None
    proposed_evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def stable_id(cls, value: str) -> str:
        if not _ID.fullmatch(value):
            raise ValueError("must use lowercase kebab-case")
        return value


class ApplicationAudit(StrictModel):
    action: str
    at: str
    detail: str = ""


class ApplicationDocument(StrictModel):
    schema_version: Literal[1] = 1
    id: str
    job_id: str
    variant_id: str | None = None
    url: str = ""
    cover_letter_path: str | None = None
    attachments: list[str] = Field(default_factory=list)
    status: ApplicationStatus = "saved"
    answers: list[ApplicationAnswer] = Field(default_factory=list)
    questions: list[ApplicationQuestion] = Field(default_factory=list)
    audit: list[ApplicationAudit] = Field(default_factory=list)

    @field_validator("id", "job_id", "variant_id")
    @classmethod
    def identifier(cls, value: str | None) -> str | None:
        if value is not None and not _ID.fullmatch(value):
            raise ValueError("must use lowercase kebab-case")
        return value

    @field_validator("url")
    @classmethod
    def safe_url(cls, value: str) -> str:
        if not value:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("must be an http(s) URL")
        return value

    @model_validator(mode="after")
    def identifiers_unique(self) -> "ApplicationDocument":
        for name, records in (("answers", self.answers), ("questions", self.questions)):
            values = [record.field_id if name == "answers" else record.id for record in records]
            if len(values) != len(set(values)):
                raise ValueError(f"{name} contains duplicate ids")
        return self


def application_path(project_path: Path, application_id: str) -> Path:
    if not _ID.fullmatch(application_id):
        raise ValueError("application id must use lowercase kebab-case")
    return project_path / APPLICATIONS_DIRECTORY / f"{application_id}.yml"


def create_application(project_path: Path, document: ApplicationDocument) -> Path:
    path = application_path(project_path, document.id)
    if path.exists():
        raise FileExistsError(f"application '{document.id}' already exists")
    _validate_links(project_path, document)
    _write(path, document)
    return path


def load_application(project_path: Path, application_id: str) -> ApplicationDocument:
    path = application_path(project_path, application_id)
    document = _load(path)
    result = ApplicationDocument.model_validate(document)
    if result.id != application_id:
        raise ValueError(f"application declares '{result.id}', expected '{application_id}'")
    _validate_links(project_path, result)
    return result


def list_applications(project_path: Path) -> list[ApplicationDocument]:
    return [load_application(project_path, path.stem) for path in sorted((project_path / APPLICATIONS_DIRECTORY).glob("*.yml"))]


def validate_applications(project_path: Path) -> list[tuple[Path, str]]:
    diagnostics: list[tuple[Path, str]] = []
    for path in sorted((project_path / APPLICATIONS_DIRECTORY).glob("*.yml")):
        try:
            load_application(project_path, path.stem)
        except (OSError, ValueError) as error:
            diagnostics.append((path, str(error)))
    return diagnostics


def update_status(project_path: Path, application_id: str, status: ApplicationStatus) -> ApplicationDocument:
    document = load_application(project_path, application_id)
    if status == document.status:
        return document
    if status not in _TRANSITIONS[document.status]:
        raise ValueError(f"invalid status transition: {document.status} -> {status}")
    updated = document.model_copy(update={"status": status, "audit": [*document.audit, _audit("status", status)]})
    _write(application_path(project_path, application_id), updated)
    return updated


def add_questions(project_path: Path, application_id: str, questions: list[ApplicationQuestion]) -> ApplicationDocument:
    document = load_application(project_path, application_id)
    existing = {item.id for item in document.questions}
    duplicates = existing.intersection(item.id for item in questions)
    if duplicates:
        raise ValueError(f"questions already exist: {', '.join(sorted(duplicates))}")
    status: ApplicationStatus = "needs_user_input" if questions else document.status
    updated = document.model_copy(update={"questions": [*document.questions, *questions], "status": status, "audit": [*document.audit, _audit("questions_detected", str(len(questions)))]})
    _write(application_path(project_path, application_id), updated)
    return updated


def replace_questions(project_path: Path, application_id: str, questions: list[ApplicationQuestion]) -> ApplicationDocument:
    """Refresh browser-detected questions without retaining stale optional fields."""
    document = load_application(project_path, application_id)
    answered = {item.field_id for item in document.answers}
    pending = [item for item in questions if item.field_id not in answered]
    status: ApplicationStatus = "needs_user_input" if pending else "ready_for_review"
    updated = document.model_copy(update={
        "questions": pending,
        "status": status,
        "audit": [*document.audit, _audit("questions_refreshed", str(len(pending)))],
    })
    _write(application_path(project_path, application_id), updated)
    return updated


def propose_answer(project_path: Path, application_id: str, question_id: str, answer: str, evidence_ids: list[str] | None = None) -> ApplicationDocument:
    document = load_application(project_path, application_id)
    evidence_ids = evidence_ids or []
    verified = {item.id for item in load_career(project_path / "career.yml").evidence if item.verified}
    if unknown := set(evidence_ids) - verified:
        raise ValueError(f"proposal references unverified or unknown evidence: {', '.join(sorted(unknown))}")
    questions = []
    found = False
    for question in document.questions:
        if question.id == question_id:
            questions.append(question.model_copy(update={"proposed_answer": answer, "proposed_evidence_ids": evidence_ids}))
            found = True
        else:
            questions.append(question)
    if not found:
        raise ValueError(f"unknown question: {question_id}")
    updated = document.model_copy(update={"questions": questions})
    _write(application_path(project_path, application_id), updated)
    return updated


def apply_answer(
    project_path: Path,
    application_id: str,
    question_id: str,
    answer: str | None = None,
    *,
    save_answer_id: str | None = None,
    save_prompt: str | None = None,
    save_role_scope: list[str] | None = None,
    save_language_scope: list[str] | None = None,
) -> ApplicationDocument:
    document = load_application(project_path, application_id)
    question = next((item for item in document.questions if item.id == question_id), None)
    if question is None:
        raise ValueError(f"unknown question: {question_id}")
    resolved = answer or question.proposed_answer
    if not resolved:
        raise ValueError("an explicit answer or a proposal is required")
    if save_answer_id:
        add_record(project_path / "career.yml", "answers", {
            "id": save_answer_id,
            "prompt": save_prompt or question.label,
            "answer": resolved,
            "evidence_ids": question.proposed_evidence_ids,
            "sensitive": question.sensitive,
            "role_scope": save_role_scope or [],
            "language_scope": save_language_scope or [],
        })
    record = ApplicationAnswer(field_id=question.field_id, answer=resolved, saved_answer_id=save_answer_id, sensitive=question.sensitive, confirmed_for_application=True)
    answers = [item for item in document.answers if item.field_id != question.field_id] + [record]
    questions = [item for item in document.questions if item.id != question_id]
    status: ApplicationStatus = "ready_for_review" if not questions else "needs_user_input"
    updated = document.model_copy(update={"answers": answers, "questions": questions, "status": status, "audit": [*document.audit, _audit("answer_confirmed", question.id)]})
    _write(application_path(project_path, application_id), updated)
    return updated


def pending_questions(project_path: Path, application_id: str) -> list[ApplicationQuestion]:
    return load_application(project_path, application_id).questions


def set_cover_letter_path(project_path: Path, application_id: str, relative_path: str) -> ApplicationDocument:
    document = load_application(project_path, application_id)
    updated = document.model_copy(update={"cover_letter_path": relative_path, "audit": [*document.audit, _audit("cover_letter_accepted")]})
    _validate_links(project_path, updated)
    _write(application_path(project_path, application_id), updated)
    return updated


def dump_application(value: ApplicationDocument | list[ApplicationDocument] | list[ApplicationQuestion]) -> str:
    stream = StringIO()
    dumped = [item.model_dump(mode="python") for item in value] if isinstance(value, list) else value.model_dump(mode="python")
    YAML().dump(dumped, stream)
    return stream.getvalue()


def _validate_links(project_path: Path, document: ApplicationDocument) -> None:
    load_job(job_path(project_path, document.job_id))
    if document.variant_id:
        load_variant(project_path, document.variant_id)
    root = project_path.resolve()
    for relative in [*document.attachments, *([document.cover_letter_path] if document.cover_letter_path else [])]:
        resolved = (root / relative).resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise ValueError(f"attachment path is invalid: {relative}")
    answers = {item.id: item for item in load_career(project_path / "career.yml").answers}
    for answer in document.answers:
        if answer.saved_answer_id and answer.saved_answer_id not in answers:
            raise ValueError(f"unknown saved answer: {answer.saved_answer_id}")


def _audit(action: str, detail: str = "") -> ApplicationAudit:
    return ApplicationAudit(action=action, at=datetime.now(UTC).replace(microsecond=0).isoformat(), detail=detail)


def _load(path: Path) -> CommentedMap:
    document = YAML(typ="rt").load(path.read_text(encoding="utf-8"))
    if not isinstance(document, CommentedMap):
        raise ValueError(f"{path.name} must contain a mapping")
    return document


def _write(path: Path, document: ApplicationDocument) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = StringIO()
    YAML().dump(document.model_dump(mode="python"), stream)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(stream.getvalue())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
