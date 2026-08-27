"""Local lexical search over verified canonical career evidence."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from seriemacv.career import CAREER_FILE, CareerEvidence, load_career, validate_career
from seriemacv.project import open_project


def search_verified_evidence(
    project_path: Path,
    *,
    query: str | None = None,
    tags: list[str] | None = None,
    experience_id: str | None = None,
) -> list[CareerEvidence]:
    """Return verified canonical evidence matching lexical and metadata criteria.

    The SQLite FTS index is rebuilt from ``career.yml`` for every query, so it is
    always a disposable projection of the user's canonical data.
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
    project = open_project(resolved_project_path)
    verified_evidence = [item for item in career.evidence if item.verified]

    with closing(sqlite3.connect(project.database_path)) as connection:
        with connection:
            connection.execute("DELETE FROM evidence_fts")
            connection.executemany(
                """
                INSERT INTO evidence_fts (evidence_id, statement, tags, details, experience_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.id,
                        item.statement,
                        " ".join(item.tags),
                        "\n".join(item.details),
                        item.experience_id or "",
                    )
                    for item in verified_evidence
                ],
            )
            try:
                if normalized_query:
                    rows = connection.execute(
                        """
                        SELECT evidence_id FROM evidence_fts
                        WHERE evidence_fts MATCH ?
                        ORDER BY bm25(evidence_fts), evidence_id
                        """,
                        (normalized_query,),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        "SELECT evidence_id FROM evidence_fts ORDER BY evidence_id"
                    ).fetchall()
            except sqlite3.OperationalError as error:
                raise ValueError(f"Invalid FTS query: {error}") from error

    evidence_by_id = {item.id: item for item in verified_evidence}
    required_tags = {tag.casefold() for tag in normalized_tags}
    return [
        evidence_by_id[row[0]]
        for row in rows
        if _matches_metadata(
            evidence_by_id[row[0]], required_tags, normalized_experience_id
        )
    ]


def _matches_metadata(
    evidence: CareerEvidence,
    required_tags: set[str],
    experience_id: str,
) -> bool:
    evidence_tags = {tag.casefold() for tag in evidence.tags}
    return (
        required_tags.issubset(evidence_tags)
        and (not experience_id or evidence.experience_id == experience_id)
    )
