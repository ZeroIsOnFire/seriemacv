"""Local lexical search over verified canonical career evidence."""

from __future__ import annotations

from pathlib import Path

from seriemacv.career import CAREER_FILE, CareerEvidence, load_career, validate_career


def search_verified_evidence(
    project_path: Path,
    *,
    query: str | None = None,
    tags: list[str] | None = None,
    experience_id: str | None = None,
) -> list[CareerEvidence]:
    """Return verified canonical evidence matching lexical and metadata criteria.

    Search reads the canonical YAML directly; no separate index is maintained.
    """
    normalized_query = (query or "").strip()
    normalized_tags = [tag.strip() for tag in tags or [] if tag.strip()]
    normalized_experience_id = (experience_id or "").strip()
    if not (normalized_query or normalized_tags or normalized_experience_id):
        raise ValueError("Provide a text query, --tag, or --experience-id")

    resolved_project_path = project_path.expanduser().resolve()
    career_path = resolved_project_path / CAREER_FILE
    diagnostics = validate_career(career_path)
    if diagnostics:
        raise ValueError("; ".join(item.format(career_path) for item in diagnostics))
    career = load_career(career_path)
    verified_evidence = [item for item in career.evidence if item.verified]
    required_tags = {tag.casefold() for tag in normalized_tags}
    return [
        item
        for item in sorted(verified_evidence, key=lambda evidence: evidence.id)
        if _matches_query(item, normalized_query)
        and _matches_metadata(item, required_tags, normalized_experience_id)
    ]


def _matches_query(evidence: CareerEvidence, query: str) -> bool:
    if not query:
        return True
    searchable = "\n".join(
        (
            evidence.id,
            evidence.statement,
            " ".join(evidence.tags),
            "\n".join(evidence.details),
        )
    ).casefold()
    return query.casefold() in searchable


def _matches_metadata(
    evidence: CareerEvidence,
    required_tags: set[str],
    experience_id: str,
) -> bool:
    evidence_tags = {tag.casefold() for tag in evidence.tags}
    return required_tags.issubset(evidence_tags) and (
        not experience_id or evidence.experience_id == experience_id
    )
