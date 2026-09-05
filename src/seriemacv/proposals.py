"""Provider-neutral, file-based proposals for resume variants and cover letters."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Annotated, Any, Literal, Union

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

from seriemacv.career import CareerEvidence, load_career, load_localized_career
from seriemacv.jobs import load_job, validate_job
from seriemacv.matching import MatchReport, match_job
from seriemacv.project import load_project_configuration
from seriemacv.styles import ResumeStyleId
from seriemacv.variants import (
    ResumeVariant,
    ResumeVariantLocale,
    VariantEducationOverride,
    VariantExperienceOverride,
    VariantProfileOverride,
    VariantSelection,
    VariantSkillOverride,
    variant_directory,
)

_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_LOCALE_PATTERN = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{2,8})*$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ProposalEvidence(StrictModel):
    id: str
    statement: str
    tags: list[str] = Field(default_factory=list)
    details: list[str] = Field(default_factory=list)
    experience_id: str | None = None


class ProposalProfileContext(StrictModel):
    title: str = ""


class ProposalExperienceContext(StrictModel):
    id: str
    company: str
    title: str
    highlights: list[str] = Field(default_factory=list, max_length=1)


class ProposalEducationContext(StrictModel):
    id: str
    institution: str
    degree: str
    highlights: list[str] = Field(default_factory=list)


class ProposalSkillContext(StrictModel):
    id: str
    name: str
    category: str = ""
    level: str | None = None
    core: bool = False


class ProposalCareerContext(StrictModel):
    """Deliberately excludes profile contacts and all unverified evidence."""

    profile: ProposalProfileContext
    summary: str = ""
    experience: list[ProposalExperienceContext] = Field(default_factory=list)
    education: list[ProposalEducationContext] = Field(default_factory=list)
    skills: list[ProposalSkillContext] = Field(default_factory=list)


class ProposalJobContext(StrictModel):
    id: str
    title: str
    company: str = ""
    match: MatchReport


class ProposalRequest(StrictModel):
    schema_version: Literal[1]
    id: str
    variant_id: str
    locale: str
    career: ProposalCareerContext
    evidence: list[ProposalEvidence] = Field(default_factory=list)
    job: ProposalJobContext | None = None

    @field_validator("id", "variant_id")
    @classmethod
    def stable_id(cls, value: str) -> str:
        if not _ID_PATTERN.fullmatch(value):
            raise ValueError("must use lowercase kebab-case")
        return value

    @field_validator("locale")
    @classmethod
    def valid_locale(cls, value: str) -> str:
        if not _LOCALE_PATTERN.fullmatch(value):
            raise ValueError("must be a BCP 47 locale identifier")
        return value


class ProposalItemBase(StrictModel):
    id: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]
    pending_information: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def stable_id(cls, value: str) -> str:
        if not _ID_PATTERN.fullmatch(value):
            raise ValueError("must use lowercase kebab-case")
        return value

    @field_validator("evidence_ids")
    @classmethod
    def unique_evidence_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("contains duplicate ids")
        return value


class VariantSelectionProposal(ProposalItemBase):
    kind: Literal["variant_selection"]
    selection: VariantSelection
    style: ResumeStyleId | None = None


class ProposalLocaleOverride(StrictModel):
    profile: VariantProfileOverride = Field(default_factory=VariantProfileOverride)
    summary: str | None = None
    experience: dict[str, VariantExperienceOverride] = Field(default_factory=dict)
    education: dict[str, VariantEducationOverride] = Field(default_factory=dict)
    skills: dict[str, VariantSkillOverride] = Field(default_factory=dict)


class VariantLocaleProposal(ProposalItemBase):
    kind: Literal["variant_locale"]
    locale_override: ProposalLocaleOverride

    @model_validator(mode="after")
    def claims_require_evidence(self) -> "VariantLocaleProposal":
        has_summary = bool(
            self.locale_override.summary and self.locale_override.summary.strip()
        )
        has_highlights = any(
            item.highlights
            for item in (
                *self.locale_override.experience.values(),
                *self.locale_override.education.values(),
            )
        )
        if (has_summary or has_highlights) and not self.evidence_ids:
            raise ValueError(
                "evidence_ids is required for tailored summary or highlights"
            )
        return self


class CoverLetterProposal(ProposalItemBase):
    kind: Literal["cover_letter"]
    body: str = Field(min_length=1)

    @model_validator(mode="after")
    def body_requires_evidence(self) -> "CoverLetterProposal":
        if not self.body.strip():
            raise ValueError("body must not be blank")
        if not self.evidence_ids:
            raise ValueError("evidence_ids is required for a cover letter")
        return self


ProposalItem = Annotated[
    Union[VariantSelectionProposal, VariantLocaleProposal, CoverLetterProposal],
    Field(discriminator="kind"),
]


class ProposalResponse(StrictModel):
    schema_version: Literal[1]
    request_id: str
    items: list[ProposalItem] = Field(min_length=1)

    @field_validator("request_id")
    @classmethod
    def stable_request_id(cls, value: str) -> str:
        if not _ID_PATTERN.fullmatch(value):
            raise ValueError("must use lowercase kebab-case")
        return value

    @model_validator(mode="after")
    def item_ids_and_kinds_are_unique(self) -> "ProposalResponse":
        ids = [item.id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("items contains duplicate ids")
        kinds = [item.kind for item in self.items]
        if len(kinds) != len(set(kinds)):
            raise ValueError("contains more than one item of the same kind")
        return self


@dataclass(frozen=True)
class ProposalDiagnostic:
    path: str
    message: str


@dataclass(frozen=True)
class ProposalDiff:
    id: str
    kind: str
    before: None
    after: dict[str, Any]
    confidence: str
    pending_information: list[str]


@dataclass(frozen=True)
class AppliedProposal:
    variant_path: Path | None
    cover_letter_path: Path | None


def create_proposal_request(
    project_path: Path,
    proposal_id: str,
    variant_id: str,
    locale: str,
    *,
    job_id: str | None = None,
) -> ProposalRequest:
    """Build the minimal local context an external agent may inspect."""
    career = load_localized_career(project_path, locale)
    facts = load_career(project_path / "career.yml")
    job_context = None
    if job_id:
        job_path = project_path / "jobs" / f"{job_id}.yml"
        diagnostics = validate_job(job_path)
        if diagnostics:
            raise ValueError("; ".join(item.format(job_path) for item in diagnostics))
        job = load_job(job_path)
        job_context = ProposalJobContext(
            id=job.id,
            title=job.title,
            company=job.company,
            match=match_job(
                project_path,
                job,
                weights=load_project_configuration(project_path).match_weights,
            ),
        )
    return ProposalRequest(
        schema_version=1,
        id=proposal_id,
        variant_id=variant_id,
        locale=locale,
        career=ProposalCareerContext(
            profile={"title": career.profile.title},
            summary=career.summary,
            experience=[
                {
                    "id": item.id,
                    "company": item.company,
                    "title": item.title,
                    "highlights": item.highlights,
                }
                for item in career.experience
            ],
            education=[
                {
                    "id": item.id,
                    "institution": item.institution,
                    "degree": item.degree,
                    "highlights": item.highlights,
                }
                for item in career.education
            ],
            skills=[
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "level": item.level,
                    "core": item.core,
                }
                for item in career.skills
            ],
        ),
        evidence=[_proposal_evidence(item) for item in facts.evidence if item.verified],
        job=job_context,
    )


def validate_proposal(
    project_path: Path, request: ProposalRequest, response: ProposalResponse
) -> list[ProposalDiagnostic]:
    diagnostics: list[ProposalDiagnostic] = []
    if response.request_id != request.id:
        diagnostics.append(
            ProposalDiagnostic(
                "request_id",
                f"declares '{response.request_id}', expected '{request.id}'",
            )
        )
    facts = load_career(project_path / "career.yml")
    verified_ids = {item.id for item in facts.evidence if item.verified}
    known_ids = {item.id for item in facts.evidence}
    for item in response.items:
        unknown = set(item.evidence_ids) - known_ids
        if unknown:
            diagnostics.append(
                ProposalDiagnostic(
                    f"items.{item.id}.evidence_ids",
                    f"references unknown evidence_ids: {', '.join(sorted(unknown))}",
                )
            )
        unverified = (set(item.evidence_ids) & known_ids) - verified_ids
        if unverified:
            diagnostics.append(
                ProposalDiagnostic(
                    f"items.{item.id}.evidence_ids",
                    f"references unverified evidence_ids: {', '.join(sorted(unverified))}",
                )
            )

    selection_item = _item_of_kind(response, "variant_selection")
    selection = (
        selection_item.selection
        if isinstance(selection_item, VariantSelectionProposal)
        else VariantSelection()
    )
    for section in ("experience", "education", "skills"):
        selected = getattr(selection, section)
        if selected is not None:
            unknown = set(selected) - {item.id for item in getattr(facts, section)}
            if unknown:
                diagnostics.append(
                    ProposalDiagnostic(
                        f"selection.{section}",
                        f"references unknown {section} ids: {', '.join(sorted(unknown))}",
                    )
                )

    locale_item = _item_of_kind(response, "variant_locale")
    if isinstance(locale_item, VariantLocaleProposal):
        try:
            override = ResumeVariantLocale.model_validate(
                {
                    "schema_version": 1,
                    "locale": request.locale,
                    "evidence_ids": locale_item.evidence_ids,
                    **locale_item.locale_override.model_dump(mode="python"),
                }
            )
        except ValidationError as error:
            diagnostics.extend(
                ProposalDiagnostic("variant_locale", item["msg"])
                for item in error.errors()
            )
        else:
            diagnostics.extend(_validate_locale_targets(override, selection, facts))
    return diagnostics


def diff_proposal(response: ProposalResponse) -> list[ProposalDiff]:
    return [
        ProposalDiff(
            id=item.id,
            kind=item.kind,
            before=None,
            after=_proposal_item_content(item),
            confidence=item.confidence,
            pending_information=item.pending_information,
        )
        for item in response.items
    ]


def apply_proposal(
    project_path: Path,
    request: ProposalRequest,
    response: ProposalResponse,
    accepted_ids: list[str],
) -> AppliedProposal:
    diagnostics = validate_proposal(project_path, request, response)
    if diagnostics:
        raise ValueError(
            "; ".join(f"{item.path}: {item.message}" for item in diagnostics)
        )
    accepted = set(accepted_ids)
    known = {item.id for item in response.items}
    unknown = accepted - known
    if unknown:
        raise ValueError(
            f"accepts unknown proposal item ids: {', '.join(sorted(unknown))}"
        )
    if not accepted:
        raise ValueError("at least one proposal item must be accepted")

    selected = [item for item in response.items if item.id in accepted]
    selection_item = next(
        (item for item in selected if isinstance(item, VariantSelectionProposal)), None
    )
    locale_item = next(
        (item for item in selected if isinstance(item, VariantLocaleProposal)), None
    )
    cover_item = next(
        (item for item in selected if isinstance(item, CoverLetterProposal)), None
    )
    variant_path: Path | None = None
    if selection_item is not None or locale_item is not None:
        directory = variant_directory(project_path, request.variant_id)
        if directory.exists():
            raise FileExistsError(f"variant '{request.variant_id}' already exists")
        selection = (
            selection_item.selection
            if selection_item is not None
            else VariantSelection()
        )
        style = selection_item.style if selection_item is not None else None
        _write_yaml(
            directory / "variant.yml",
            ResumeVariant(
                schema_version=1,
                id=request.variant_id,
                job_id=request.job.id if request.job else None,
                style=style,
                selection=selection,
            ),
        )
        if locale_item is not None:
            override = ResumeVariantLocale.model_validate(
                {
                    "schema_version": 1,
                    "locale": request.locale,
                    "evidence_ids": locale_item.evidence_ids,
                    **locale_item.locale_override.model_dump(mode="python"),
                }
            )
            _write_yaml(directory / "locales" / f"{request.locale}.yml", override)
        variant_path = directory / "variant.yml"
    cover_letter_path: Path | None = None
    if cover_item is not None:
        cover_letter_path = (
            project_path
            / "exports"
            / "cover-letters"
            / f"{request.id}.{request.locale}.md"
        )
        _atomic_write(cover_letter_path, cover_item.body.rstrip() + "\n")
    return AppliedProposal(variant_path, cover_letter_path)


def load_proposal_request(path: Path) -> ProposalRequest:
    return ProposalRequest.model_validate(_load_yaml(path))


def load_proposal_response(path: Path) -> ProposalResponse:
    return ProposalResponse.model_validate(_load_yaml(path))


def write_proposal_request(path: Path, request: ProposalRequest) -> None:
    _atomic_write(path, dump_proposal_request(request))


def dump_proposal_request(request: ProposalRequest) -> str:
    """Serialize the exact local context that may be shared with an external agent."""
    return _dump_yaml(request.model_dump(mode="python"))


def dump_proposal_diff(diffs: list[ProposalDiff]) -> str:
    return _dump_yaml([item.__dict__ for item in diffs])


def _proposal_evidence(evidence: CareerEvidence) -> ProposalEvidence:
    return ProposalEvidence(**evidence.model_dump(exclude={"verified"}))


def _item_of_kind(response: ProposalResponse, kind: str) -> ProposalItem | None:
    return next((item for item in response.items if item.kind == kind), None)


def _proposal_item_content(item: ProposalItem) -> dict[str, Any]:
    return item.model_dump(
        exclude={"id", "kind", "confidence", "pending_information"}, mode="python"
    )


def _validate_locale_targets(
    override: ResumeVariantLocale, selection: VariantSelection, facts: Any
) -> list[ProposalDiagnostic]:
    diagnostics: list[ProposalDiagnostic] = []
    for section in ("experience", "education", "skills"):
        known = {item.id for item in getattr(facts, section)}
        selected = getattr(selection, section)
        if selected is not None:
            known &= set(selected)
        unknown = set(getattr(override, section)) - known
        if unknown:
            diagnostics.append(
                ProposalDiagnostic(
                    f"variant_locale.{section}",
                    f"references unavailable {section} ids: {', '.join(sorted(unknown))}",
                )
            )
    return diagnostics


def _load_yaml(path: Path) -> CommentedMap:
    yaml = YAML(typ="rt")
    document = yaml.load(path.read_text(encoding="utf-8"))
    if not isinstance(document, CommentedMap):
        raise ValueError(f"{path.name} must contain a mapping")
    return document


def _write_yaml(path: Path, value: BaseModel) -> None:
    _atomic_write(path, _dump_yaml(value.model_dump(mode="python")))


def _dump_yaml(value: Any) -> str:
    yaml = YAML()
    yaml.default_flow_style = False
    stream = StringIO()
    yaml.dump(value, stream)
    return stream.getvalue()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
