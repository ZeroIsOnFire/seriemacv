from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from seriemacv.jobs import JobDocument, JobSource
from seriemacv.matching import (
    MatchClassification,
    MatchWeights,
    extract_requirements,
    match_job,
)
from seriemacv.project import create_project


class MatchingTests(unittest.TestCase):
    def test_report_is_explainable_uses_verified_evidence_and_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _project_with_evidence(temporary_directory)
            job = _job(
                requirements=[
                    {"id": "python", "statement": "Professional Python experience", "priority": "required"},
                    {"id": "go", "statement": "Professional Go experience", "priority": "required"},
                    {"id": "kubernetes", "statement": "Kubernetes operations", "priority": "preferred"},
                ]
            )

            report = match_job(project_path, job)

            self.assertEqual(report.job_id, "platform-role")
            self.assertEqual(report.score.total, 50.0)
            self.assertEqual(
                [item.classification for item in report.requirements],
                [MatchClassification.STRONG_MATCH, MatchClassification.CONFLICT, MatchClassification.PARTIAL_MATCH],
            )
            self.assertEqual(report.requirements[0].evidence_ids, ["python-delivery"])
            self.assertEqual(report.requirements[1].evidence_ids, ["go-conflict"])
            self.assertNotIn("pending-python", [
                evidence_id for item in report.requirements for evidence_id in item.evidence_ids
            ])
            self.assertEqual(report.gaps, [])
            self.assertEqual(report.conflicts, ["go"])

    def test_no_evidence_is_a_gap_and_does_not_score(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _project_with_evidence(temporary_directory)

            report = match_job(project_path, _job(requirements=[{
                "id": "rust", "statement": "Rust programming", "priority": "required"
            }]))

            self.assertEqual(report.requirements[0].classification, MatchClassification.NO_EVIDENCE)
            self.assertEqual(report.requirements[0].evidence_ids, [])
            self.assertEqual(report.gaps, ["rust"])
            self.assertEqual(report.score.total, 0.0)

    def test_score_uses_configurable_dimension_weights(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _project_with_evidence(temporary_directory)
            job = _job(requirements=[{
                "id": "english", "statement": "English communication", "priority": "required", "dimension": "language"
            }])
            weights = MatchWeights(core_technical_fit=0, experience_seniority=0, responsibilities=0, domain=0, location_schedule=0, language=100, other_constraints=0)

            report = match_job(project_path, job, weights=weights)

            self.assertEqual(report.score.total, 75.0)
            self.assertEqual(report.score.dimensions["language"], 75.0)

    def test_extracts_reviewable_requirements_when_job_has_no_structured_ones(self) -> None:
        job = _job(
            requirements=[],
            description="Requirements:\n- Must have Python experience.\n- English communication is required.\nBenefits include remote work.",
        )

        requirements = extract_requirements(job)

        self.assertEqual([item.id for item in requirements], ["must-have-python-experience", "english-communication-is-required"])
        self.assertTrue(all(item.priority == "required" for item in requirements))


def _project_with_evidence(temporary_directory: str) -> Path:
    project_path = Path(temporary_directory) / "career-project"
    create_project(project_path, project_name="Career Project", resume_language="en")
    (project_path / "career.yml").write_text(
        """schema_version: 2
profile: {name: Example Person, email: example@example.invalid}
experience: []
education: []
skills: []
evidence:
  - id: python-delivery
    statement: Delivered Python services in production.
    tags: [python, backend]
    details: [Owned reliable service operations.]
    verified: true
  - id: go-conflict
    statement: No professional Go experience.
    tags: [go]
    verified: true
  - id: kubernetes-familiarity
    statement: Used Kubernetes during a migration.
    tags: [kubernetes]
    verified: true
  - id: english-communication
    statement: English communication with global teams.
    tags: [english]
    verified: true
  - id: pending-python
    statement: Pending Python claim.
    tags: [python]
    verified: false
answers: []
stories: []
""",
        encoding="utf-8",
    )
    return project_path


def _job(
    *, requirements: list[dict[str, str]], description: str = ""
) -> JobDocument:
    return JobDocument.model_validate({
        "schema_version": 1,
        "id": "platform-role",
        "title": "Platform Engineer",
        "description": description,
        "requirements": requirements,
        "source": JobSource(format="manual", content=description or "Structured role").model_dump(),
    })
