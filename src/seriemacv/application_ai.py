"""Provider-neutral, reviewable AI assistance for difficult application forms."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from seriemacv.applications import (
    ApplicationDocument,
    ApplicationQuestion,
    application_path,
    load_application,
    propose_answer,
    set_cover_letter_path,
)
from seriemacv.career import CareerEvidence, load_career
from seriemacv.jobs import load_job

_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class AiEvidence(StrictModel):
    id: str
    statement: str
    tags: list[str] = Field(default_factory=list)
    details: list[str] = Field(default_factory=list)


class AiQuestion(StrictModel):
    id: str
    label: str
    context: str = ""
    required: bool
    sensitive: bool


class ApplicationAiRequest(StrictModel):
    schema_version: Literal[1] = 1
    id: str
    application_id: str
    job: dict[str, str]
    questions: list[AiQuestion]
    evidence: list[AiEvidence]
    rules: list[str]

    @field_validator("id", "application_id")
    @classmethod
    def stable_id(cls, value: str) -> str:
        if not _ID.fullmatch(value):
            raise ValueError("must use lowercase kebab-case")
        return value


class ApplicationAiAnswer(StrictModel):
    id: str
    question_id: str
    answer: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]
    pending_information: list[str] = Field(default_factory=list)


class ApplicationAiCoverLetter(StrictModel):
    id: str
    body: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]
    pending_information: list[str] = Field(default_factory=list)


class ApplicationAiResponse(StrictModel):
    schema_version: Literal[1] = 1
    request_id: str
    answers: list[ApplicationAiAnswer] = Field(default_factory=list)
    cover_letter: ApplicationAiCoverLetter | None = None

    @model_validator(mode="after")
    def item_ids_are_unique(self) -> "ApplicationAiResponse":
        ids = [item.id for item in self.answers]
        if self.cover_letter:
            ids.append(self.cover_letter.id)
        if len(ids) != len(set(ids)):
            raise ValueError("response contains duplicate item ids")
        return self


@dataclass(frozen=True)
class ApplicationAiDiff:
    id: str
    kind: str
    question_id: str | None
    confidence: str
    pending_information: list[str]
    evidence_ids: list[str]


def create_ai_request(project_path: Path, request_id: str, application_id: str) -> ApplicationAiRequest:
    application = load_application(project_path, application_id)
    if not _ID.fullmatch(request_id):
        raise ValueError("request id must use lowercase kebab-case")
    job = load_job(project_path / "jobs" / f"{application.job_id}.yml")
    evidence = [_evidence(item) for item in load_career(project_path / "career.yml").evidence if item.verified]
    return ApplicationAiRequest(
        id=request_id,
        application_id=application.id,
        job={"id": job.id, "title": job.title, "company": job.company},
        questions=[_question(item) for item in application.questions],
        evidence=evidence,
        rules=[
            "Propose answers only for non-sensitive questions.",
            "Use only supplied verified evidence ids for claims.",
            "Do not invent facts; list missing facts in pending_information.",
            "This request has no profile contacts, passwords, cookies, or form values.",
        ],
    )


def validate_ai_response(project_path: Path, request: ApplicationAiRequest, response: ApplicationAiResponse) -> list[ApplicationAiDiff]:
    if response.request_id != request.id:
        raise ValueError(f"response declares '{response.request_id}', expected '{request.id}'")
    application = load_application(project_path, request.application_id)
    questions = {item.id: item for item in application.questions}
    verified = {item.id for item in load_career(project_path / "career.yml").evidence if item.verified}
    seen: set[str] = set()
    diffs: list[ApplicationAiDiff] = []
    for item in response.answers:
        if item.question_id in seen:
            raise ValueError("response contains duplicate question ids")
        seen.add(item.question_id)
        question = questions.get(item.question_id)
        if question is None:
            raise ValueError(f"response references unknown question: {item.question_id}")
        if question.sensitive:
            raise ValueError(f"AI cannot propose a sensitive question: {item.question_id}")
        _ensure_evidence(item.evidence_ids, verified)
        diffs.append(ApplicationAiDiff(item.id, "answer", item.question_id, item.confidence, item.pending_information, item.evidence_ids))
    if response.cover_letter:
        _ensure_evidence(response.cover_letter.evidence_ids, verified)
        if not response.cover_letter.evidence_ids:
            raise ValueError("cover letter requires verified evidence ids")
        diffs.append(ApplicationAiDiff(response.cover_letter.id, "cover_letter", None, response.cover_letter.confidence, response.cover_letter.pending_information, response.cover_letter.evidence_ids))
    return diffs


def apply_ai_response(project_path: Path, request: ApplicationAiRequest, response: ApplicationAiResponse, accepted_ids: list[str]) -> ApplicationDocument:
    diffs = validate_ai_response(project_path, request, response)
    known = {item.id for item in diffs}
    unknown = set(accepted_ids) - known
    if unknown:
        raise ValueError(f"unknown accepted item ids: {', '.join(sorted(unknown))}")
    for item in response.answers:
        if item.id in accepted_ids:
            propose_answer(project_path, request.application_id, item.question_id, item.answer, item.evidence_ids)
    if response.cover_letter and response.cover_letter.id in accepted_ids:
        path = application_path(project_path, request.application_id).parent / request.application_id / "cover-letter.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(path, response.cover_letter.body + "\n")
        relative = path.relative_to(project_path).as_posix()
        set_cover_letter_path(project_path, request.application_id, relative)
    return load_application(project_path, request.application_id)


def dump_ai(value: Any) -> str:
    stream = StringIO()
    YAML().dump(value.model_dump(mode="python") if hasattr(value, "model_dump") else value, stream)
    return stream.getvalue()


def load_ai_request(path: Path) -> ApplicationAiRequest:
    return ApplicationAiRequest.model_validate(_load(path))


def load_ai_response(path: Path) -> ApplicationAiResponse:
    return ApplicationAiResponse.model_validate(_load(path))


def write_ai_request(path: Path, request: ApplicationAiRequest) -> None:
    _atomic_write(path, dump_ai(request))


def _question(value: ApplicationQuestion) -> AiQuestion:
    return AiQuestion(id=value.id, label=value.label, context=value.context, required=value.required, sensitive=value.sensitive)


def _evidence(value: CareerEvidence) -> AiEvidence:
    return AiEvidence(id=value.id, statement=value.statement, tags=value.tags, details=value.details)


def _ensure_evidence(ids: list[str], verified: set[str]) -> None:
    if unknown := set(ids) - verified:
        raise ValueError(f"response references unverified or unknown evidence: {', '.join(sorted(unknown))}")


def _load(path: Path) -> CommentedMap:
    document = YAML(typ="rt").load(path.read_text(encoding="utf-8"))
    if not isinstance(document, CommentedMap):
        raise ValueError(f"{path.name} must contain a mapping")
    return document


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(content)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
