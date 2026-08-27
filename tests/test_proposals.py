import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from seriemacv.cli import main
from seriemacv.jobs import JobImportPayload, JobSource, create_job
from seriemacv.project import create_project
from seriemacv.proposals import (
    ProposalResponse,
    apply_proposal,
    create_proposal_request,
    diff_proposal,
    validate_proposal,
    write_proposal_request,
)
from seriemacv.variants import load_variant_career


class ProposalTests(unittest.TestCase):
    def test_request_exposes_minimal_context_and_verified_evidence_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)

            request = create_proposal_request(project_path, "backend-tailor", "backend-role", "en")

            self.assertEqual(request.career.profile.title, "Software Engineer")
            self.assertEqual([item.id for item in request.evidence], ["backend-delivery"])
            self.assertNotIn("email", request.model_dump_json())
            self.assertNotIn("pending-proof", request.model_dump_json())

    def test_valid_response_has_granular_diff_and_applies_only_accepted_items(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)
            request = create_proposal_request(project_path, "backend-tailor", "backend-role", "en")
            response = _response(request.id)
            original_career = (project_path / "career.yml").read_text(encoding="utf-8")

            self.assertEqual(validate_proposal(project_path, request, response), [])
            self.assertEqual([item.id for item in diff_proposal(response)], ["selection", "wording", "letter"])

            applied = apply_proposal(
                project_path, request, response, ["selection", "wording", "letter"]
            )

            self.assertTrue(applied.variant_path and applied.variant_path.is_file())
            self.assertTrue(applied.cover_letter_path and applied.cover_letter_path.is_file())
            self.assertEqual((project_path / "career.yml").read_text(encoding="utf-8"), original_career)
            _, career = load_variant_career(project_path, "backend-role", "en")
            self.assertEqual([item.id for item in career.skills], ["python"])
            self.assertEqual(career.summary, "Builds reliable backend platforms.")
            self.assertIn("reliable backend", applied.cover_letter_path.read_text(encoding="utf-8"))

    def test_rejects_unknown_or_unverified_proposal_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)
            request = create_proposal_request(project_path, "backend-tailor", "backend-role", "en")
            response = ProposalResponse.model_validate({
                "schema_version": 1,
                "request_id": request.id,
                "items": [{
                    "id": "letter",
                    "kind": "cover_letter",
                    "body": "A supported letter.",
                    "evidence_ids": ["missing-proof", "pending-proof"],
                    "confidence": "medium",
                    "pending_information": [],
                }],
            })

            messages = "\n".join(item.message for item in validate_proposal(project_path, request, response))
            self.assertIn("unknown evidence_ids: missing-proof", messages)
            self.assertIn("unverified evidence_ids: pending-proof", messages)

    def test_cover_letter_without_evidence_is_rejected_before_persistence(self) -> None:
        with self.assertRaisesRegex(ValueError, "evidence_ids is required for a cover letter"):
            ProposalResponse.model_validate({
                "schema_version": 1,
                "request_id": "backend-tailor",
                "items": [{
                    "id": "letter",
                    "kind": "cover_letter",
                    "body": "Unsupported letter.",
                    "evidence_ids": [],
                    "confidence": "low",
                    "pending_information": ["Add verified evidence."],
                }],
            })

    def test_accepting_one_item_does_not_persist_rejected_variant_items(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)
            request = create_proposal_request(project_path, "backend-tailor", "backend-role", "en")

            applied = apply_proposal(project_path, request, _response(request.id), ["letter"])

            self.assertIsNone(applied.variant_path)
            self.assertTrue(applied.cover_letter_path and applied.cover_letter_path.is_file())
            self.assertFalse((project_path / "resume/variants/backend-role").exists())

    def test_cli_writes_reviews_and_requires_explicit_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)
            request_path = project_path / "request.yml"
            response_path = project_path / "response.yml"
            request = create_proposal_request(project_path, "backend-tailor", "backend-role", "en")
            write_proposal_request(request_path, request)
            _write_yaml(response_path, _response(request.id).model_dump(mode="python"))

            with redirect_stdout(StringIO()) as output:
                result = main(["proposal", "review", str(project_path), str(request_path), str(response_path)])
            self.assertEqual(result, 0)
            self.assertIn("kind: cover_letter", output.getvalue())

            with redirect_stderr(StringIO()) as error:
                result = main(["proposal", "apply", str(project_path), str(request_path), str(response_path), "--accept", "missing"])
            self.assertEqual(result, 1)
            self.assertIn("accepts unknown proposal item ids: missing", error.getvalue())

    def test_job_tailoring_request_includes_match_and_links_the_created_variant(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)
            create_job(
                project_path,
                JobImportPayload.model_validate({
                    "schema_version": 1,
                    "id": "backend-job",
                    "title": "Backend Engineer",
                    "requirements": [{"id": "backend", "statement": "Reliable backend services"}],
                }),
                JobSource(format="manual", content="Backend role"),
            )

            request = create_proposal_request(
                project_path, "job-tailor", "backend-job-variant", "en", job_id="backend-job"
            )
            applied = apply_proposal(project_path, request, _response(request.id), ["selection"])

            self.assertEqual(request.job.id, "backend-job")
            self.assertEqual(request.job.match.job_id, "backend-job")
            self.assertTrue(applied.variant_path)
            self.assertEqual(
                load_variant_career(project_path, "backend-job-variant", "en")[0].job_id,
                "backend-job",
            )


def _response(request_id: str) -> ProposalResponse:
    return ProposalResponse.model_validate({
        "schema_version": 1,
        "request_id": request_id,
        "items": [
            {
                "id": "selection",
                "kind": "variant_selection",
                "selection": {"experience": ["current"], "education": [], "skills": ["python"]},
                "style": "compact",
                "evidence_ids": [],
                "confidence": "high",
                "pending_information": [],
            },
            {
                "id": "wording",
                "kind": "variant_locale",
                "locale_override": {
                    "summary": "Builds reliable backend platforms.",
                    "experience": {"current": {"highlights": ["Built reliable backend services."]}},
                },
                "evidence_ids": ["backend-delivery"],
                "confidence": "high",
                "pending_information": [],
            },
            {
                "id": "letter",
                "kind": "cover_letter",
                "body": "I am interested in reliable backend platform work.",
                "evidence_ids": ["backend-delivery"],
                "confidence": "medium",
                "pending_information": ["Confirm the hiring manager name."],
            },
        ],
    })


def _complete_project(temporary_directory: str) -> Path:
    project_path = Path(temporary_directory) / "career-project"
    create_project(project_path, project_name="Career Project", resume_language="en")
    (project_path / "career.yml").write_text(
        """schema_version: 2
profile: {name: Seriema Example, email: seriema@example.invalid}
experience:
  - {id: current, company: Example Systems, start_date: 2022-01}
education: []
skills:
  - {id: python, core: true}
evidence:
  - {id: backend-delivery, statement: Delivered reliable backend services., verified: true}
  - {id: pending-proof, statement: Pending claim, verified: false}
answers: []
stories: []
""",
        encoding="utf-8",
    )
    (project_path / "career.locales/en.yml").write_text(
        """schema_version: 1
locale: en
profile: {title: Software Engineer, location: Example City}
summary: General software engineering summary.
experience:
  current: {title: Backend Engineer, highlights: [Built software.]}
education: {}
skills:
  python: {name: Python, category: Languages}
""",
        encoding="utf-8",
    )
    return project_path


def _write_yaml(path: Path, value: object) -> None:
    from ruamel.yaml import YAML

    yaml = YAML()
    with path.open("w", encoding="utf-8", newline="\n") as file:
        yaml.dump(value, file)
