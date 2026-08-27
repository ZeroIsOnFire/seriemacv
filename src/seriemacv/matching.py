"""Deterministic, evidence-backed job matching.

The matcher deliberately performs no inference beyond transparent lexical rules.
Every positive or conflicting conclusion links to verified canonical evidence.
"""

from __future__ import annotations

import re
from collections import defaultdict
from enum import StrEnum
from io import StringIO
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from ruamel.yaml import YAML

from seriemacv.career import CareerEvidence, load_career, validate_career
from seriemacv.jobs import JobDocument, JobRequirement

MatchDimension = Literal[
    "core_technical_fit",
    "experience_seniority",
    "responsibilities",
    "domain",
    "location_schedule",
    "language",
    "other_constraints",
]

_DIMENSIONS: tuple[MatchDimension, ...] = (
    "core_technical_fit",
    "experience_seniority",
    "responsibilities",
    "domain",
    "location_schedule",
    "language",
    "other_constraints",
)
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "com", "de", "do", "e",
    "em", "for", "have", "in", "is", "of", "or", "para", "required", "the",
    "to", "with", "experience", "professional", "must", "ter", "uma", "um",
}
_TOKEN_PATTERN = re.compile(r"[\w+#.]+", re.UNICODE)
_CONFLICT_PATTERN = re.compile(r"\b(no|not|without|sem|n[aã]o)\b", re.IGNORECASE)
_STRONG_MARKERS = re.compile(
    r"\b(delivered|owned|led|production|architected|mentored|years?|operat(?:ed|ions)|"
    r"entreg(?:uei|ou)|liderei|produ[cç][aã]o|respons[aá]vel)\b",
    re.IGNORECASE,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class MatchClassification(StrEnum):
    STRONG_MATCH = "STRONG_MATCH"
    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    TRANSFERABLE = "TRANSFERABLE"
    NO_EVIDENCE = "NO_EVIDENCE"
    CONFLICT = "CONFLICT"


class MatchWeights(StrictModel):
    """Percentage weights for the explainable score dimensions."""

    core_technical_fit: float = 35
    experience_seniority: float = 20
    responsibilities: float = 15
    domain: float = 10
    location_schedule: float = 10
    language: float = 5
    other_constraints: float = 5

    @model_validator(mode="after")
    def totals_one_hundred(self) -> "MatchWeights":
        if any(value < 0 for value in self.model_dump().values()):
            raise ValueError("weights must not be negative")
        if round(sum(self.model_dump().values()), 6) != 100:
            raise ValueError("weights must total 100")
        return self


class MatchedRequirement(StrictModel):
    id: str
    statement: str
    priority: Literal["required", "preferred"]
    dimension: MatchDimension
    classification: MatchClassification
    evidence_ids: list[str] = Field(default_factory=list)
    explanation: str


class MatchScore(StrictModel):
    total: float = Field(ge=0, le=100)
    dimensions: dict[MatchDimension, float] = Field(default_factory=dict)
    weights: MatchWeights


class MatchReport(StrictModel):
    schema_version: Literal[1] = 1
    job_id: str
    requirements: list[MatchedRequirement]
    score: MatchScore
    gaps: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    interview_notes: list[str] = Field(default_factory=list)


def extract_requirements(job: JobDocument) -> list[JobRequirement]:
    """Return structured requirements, or deterministic candidates from a description.

    Existing structured requirements are authoritative. Extraction is intentionally
    conservative: only lines that explicitly signal a requirement are returned.
    The result is a proposal-like in-memory value; it never changes the job source.
    """
    if job.requirements:
        return job.requirements
    candidates: list[str] = []
    for line in job.description.splitlines():
        normalized = line.strip().lstrip("-*• ").strip()
        if not normalized:
            continue
        if normalized.rstrip(":").casefold() in {"requirements", "requisitos"}:
            continue
        lowered = normalized.casefold()
        if any(marker in lowered for marker in ("must", "required", "requirement", "necessário", "necessaria", "obrigatório", "obrigatoria")):
            candidates.append(normalized)
    if not candidates:
        for sentence in re.split(r"(?<=[.!?])\s+", job.description):
            normalized = sentence.strip()
            if normalized and any(marker in normalized.casefold() for marker in ("must", "required", "necessário", "obrigatório")):
                candidates.append(normalized)
    used_ids: set[str] = set()
    return [
        JobRequirement(id=_requirement_id(item, used_ids), statement=item, priority="required")
        for item in candidates
    ]


def match_job(
    project_path: Path, job: JobDocument, *, weights: MatchWeights | None = None
) -> MatchReport:
    """Classify every job requirement using only verified career evidence."""
    career_path = project_path.expanduser().resolve() / "career.yml"
    diagnostics = validate_career(career_path)
    if diagnostics:
        raise ValueError("; ".join(item.format(career_path) for item in diagnostics))
    evidence = [item for item in load_career(career_path).evidence if item.verified]
    effective_weights = weights or MatchWeights()
    matched = [_match_requirement(item, evidence) for item in extract_requirements(job)]
    dimension_scores: dict[MatchDimension, list[float]] = defaultdict(list)
    for item in matched:
        dimension_scores[item.dimension].append(_classification_value(item.classification))
    dimensions = {
        dimension: round(sum(values) / len(values), 2)
        for dimension, values in sorted(dimension_scores.items())
    }
    present_weight = sum(getattr(effective_weights, dimension) for dimension in dimensions)
    total = (
        round(
            sum(dimensions[dimension] * getattr(effective_weights, dimension) for dimension in dimensions)
            / present_weight,
            2,
        )
        if present_weight else 0.0
    )
    gaps = [item.id for item in matched if item.classification == MatchClassification.NO_EVIDENCE]
    conflicts = [item.id for item in matched if item.classification == MatchClassification.CONFLICT]
    notes = [
        f"Discuss evidence for {item.id}: {item.explanation}"
        for item in matched
        if item.classification in {MatchClassification.PARTIAL_MATCH, MatchClassification.TRANSFERABLE}
    ]
    return MatchReport(
        job_id=job.id,
        requirements=matched,
        score=MatchScore(total=total, dimensions=dimensions, weights=effective_weights),
        gaps=gaps,
        conflicts=conflicts,
        interview_notes=notes,
    )


def dump_match_report(report: MatchReport) -> str:
    yaml = YAML()
    yaml.default_flow_style = False
    stream = StringIO()
    yaml.dump(report.model_dump(mode="json"), stream)
    return stream.getvalue()


def _match_requirement(requirement: JobRequirement, evidence: list[CareerEvidence]) -> MatchedRequirement:
    terms = _terms(requirement.id.replace("-", " ") + " " + requirement.statement)
    dimension = requirement.dimension or _infer_dimension(requirement)
    candidates: list[tuple[CareerEvidence, set[str], bool]] = []
    for item in evidence:
        item_terms = _terms(" ".join([item.statement, *item.tags, *item.details]))
        overlap = terms & item_terms
        tag_match = bool(terms & _terms(" ".join(item.tags)))
        if overlap or tag_match:
            candidates.append((item, overlap, tag_match))
    candidates.sort(key=lambda candidate: candidate[0].id)
    if not candidates:
        return _matched(requirement, dimension, MatchClassification.NO_EVIDENCE, [], "No verified evidence contains the requirement terms.")
    conflicting = [item for item, overlap, _ in candidates if overlap and _CONFLICT_PATTERN.search(" ".join([item.statement, *item.details]))]
    if conflicting:
        return _matched(requirement, dimension, MatchClassification.CONFLICT, conflicting, "Verified evidence explicitly contradicts this requirement.")
    supporting = [item for item, _, _ in candidates]
    combined_overlap = set().union(*(overlap for _, overlap, _ in candidates))
    text = " ".join(" ".join([item.statement, *item.details]) for item in supporting)
    if _STRONG_MARKERS.search(text):
        classification = MatchClassification.STRONG_MATCH
        reason = "Verified evidence directly names the requirement and shows sustained delivery or ownership."
    elif len(combined_overlap) >= 2:
        classification = MatchClassification.MATCH
        reason = "Verified evidence directly covers multiple requirement terms."
    elif combined_overlap:
        classification = MatchClassification.PARTIAL_MATCH
        reason = "Verified evidence covers part of the requirement, without enough detail for a full match."
    else:
        classification = MatchClassification.TRANSFERABLE
        reason = "Verified evidence has a related tag but no direct statement match."
    return _matched(requirement, dimension, classification, supporting, reason)


def _matched(
    requirement: JobRequirement,
    dimension: MatchDimension,
    classification: MatchClassification,
    evidence: list[CareerEvidence],
    explanation: str,
) -> MatchedRequirement:
    return MatchedRequirement(
        id=requirement.id,
        statement=requirement.statement,
        priority=requirement.priority,
        dimension=dimension,
        classification=classification,
        evidence_ids=[item.id for item in evidence],
        explanation=explanation,
    )


def _terms(value: str) -> set[str]:
    terms = {token.casefold() for token in _TOKEN_PATTERN.findall(value)}
    return {term for term in terms if len(term) > 1 and term not in _STOP_WORDS}


def _infer_dimension(requirement: JobRequirement) -> MatchDimension:
    text = (requirement.id + " " + requirement.statement).casefold()
    if any(term in text for term in ("english", "portuguese", "language", "idioma", "inglês")):
        return "language"
    if any(term in text for term in ("remote", "location", "timezone", "time zone", "localização", "horário")):
        return "location_schedule"
    if any(term in text for term in ("senior", "years", "anos", "leadership", "liderança")):
        return "experience_seniority"
    if any(term in text for term in ("responsib", "build", "operate", "deliver", "desenvolv", "operar")):
        return "responsibilities"
    return "core_technical_fit"


def _classification_value(classification: MatchClassification) -> float:
    return {
        MatchClassification.STRONG_MATCH: 100,
        MatchClassification.MATCH: 75,
        MatchClassification.PARTIAL_MATCH: 50,
        MatchClassification.TRANSFERABLE: 25,
        MatchClassification.NO_EVIDENCE: 0,
        MatchClassification.CONFLICT: 0,
    }[classification]


def _requirement_id(statement: str, used_ids: set[str]) -> str:
    identifier = re.sub(r"[^a-z0-9]+", "-", statement.casefold()).strip("-")
    identifier = identifier[:60].strip("-") or "requirement"
    base = identifier
    number = 2
    while identifier in used_ids:
        identifier = f"{base}-{number}"
        number += 1
    used_ids.add(identifier)
    return identifier
