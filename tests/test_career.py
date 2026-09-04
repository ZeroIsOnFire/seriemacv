from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from seriemacv.career import (
    CareerDocument,
    add_record,
    load_career,
    set_profile,
    validate_career,
)
from seriemacv.cli import main
from seriemacv.project import create_project


class CareerSchemaTests(unittest.TestCase):
    def test_experience_allows_only_one_highlight(self) -> None:
        with self.assertRaisesRegex(ValueError, "at most 1 item"):
            CareerDocument.model_validate({
                "schema_version": 2,
                "experience": [{
                    "id": "example",
                    "company": "Example",
                    "title": "Engineer",
                    "start_date": "2024-01",
                    "highlights": ["Primary achievement.", "Secondary achievement."],
                }],
            })

        career = CareerDocument.model_validate({
            "schema_version": 2,
            "experience": [{
                "id": "example",
                "company": "Example",
                "title": "Engineer",
                "start_date": "2024-01",
                "bullets": ["Secondary achievement."],
                "highlights": ["Primary achievement."],
            }],
        })
        self.assertEqual(career.experience[0].highlights, ["Primary achievement."])

    def test_example_is_a_complete_valid_career_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)

            diagnostics = validate_career(project_path / "career.yml.example")
            career = load_career(project_path / "career.yml.example")

            self.assertEqual(diagnostics, [])
            self.assertEqual(career.evidence[0].experience_id, "example-platform")

    def test_new_scaffold_reports_missing_profile_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)

            diagnostics = validate_career(project_path / "career.yml")

            self.assertEqual({item.path for item in diagnostics}, {
                "profile.name", "profile.email"
            })
            self.assertTrue(all(item.line is not None for item in diagnostics))

    def test_rejects_unknown_fields_and_invalid_dates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            career_path = project_path / "career.yml"
            career_path.write_text(
                "schema_version: 2\nprofile: {}\nexperience:\n"
                "  - id: broken\n    company: Example\n"
                "    start_date: 2024-13\n    unexpected: true\n",
                encoding="utf-8",
            )

            diagnostics = validate_career(career_path)

            self.assertTrue(any(item.path.endswith("start_date") for item in diagnostics))
            self.assertTrue(any(item.path.endswith("unexpected") for item in diagnostics))

    def test_rejects_duplicate_ids_and_unknown_evidence_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            career_path = project_path / "career.yml"
            career_path.write_text(
                "schema_version: 2\nprofile: {}\nexperience:\n"
                "  - id: repeated\n    company: Example\n    start_date: 2024-01\n"
                "  - id: repeated\n    company: Example\n    start_date: 2024-02\n"
                "evidence:\n  - id: proof\n    statement: A fact\n"
                "    experience_id: missing\n",
                encoding="utf-8",
            )

            diagnostics = validate_career(career_path)

            self.assertTrue(any("duplicate" in item.message for item in diagnostics))

    def test_rejects_unknown_evidence_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            career_path = project_path / "career.yml"
            career_path.write_text(
                "schema_version: 2\nprofile: {}\nevidence:\n"
                "  - id: proof\n    statement: A fact\n"
                "    experience_id: missing\n",
                encoding="utf-8",
            )

            diagnostics = validate_career(career_path)

            self.assertTrue(any("unknown experience_id" in item.message for item in diagnostics))

    def test_add_record_is_atomic_when_validation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            career_path = project_path / "career.yml"
            original = career_path.read_text(encoding="utf-8")

            with self.assertRaises(ValueError):
                add_record(career_path, "experience", {
                    "id": "bad date", "company": "Example", "title": "Engineer",
                    "start_date": "2024-01",
                })

            self.assertEqual(career_path.read_text(encoding="utf-8"), original)

    def test_answers_and_stories_require_unique_verified_evidence_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            career_path = project_path / "career.yml"
            career_path.write_text(
                """schema_version: 2
profile: {}
evidence:
  - id: verified-proof
    statement: Verified fact
    verified: true
  - id: pending-proof
    statement: Pending fact
answers:
  - id: supported-answer
    prompt: Question?
    answer: Answer.
    evidence_ids: [verified-proof]
stories:
  - id: supported-story
    title: Story
    evidence_ids: [verified-proof]
""",
                encoding="utf-8",
            )
            self.assertEqual(
                [item.message for item in validate_career(career_path) if "evidence_ids" in item.message],
                [],
            )

            original = career_path.read_text(encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unverified evidence_ids: pending-proof"):
                add_record(career_path, "answers", {
                    "id": "invalid-answer", "prompt": "Question?", "answer": "Answer.",
                    "evidence_ids": ["pending-proof"],
                })
            self.assertEqual(career_path.read_text(encoding="utf-8"), original)

            with self.assertRaisesRegex(ValueError, "unknown evidence_ids: missing-proof"):
                add_record(career_path, "answers", {
                    "id": "missing-answer", "prompt": "Question?", "answer": "Answer.",
                    "evidence_ids": ["missing-proof"],
                })
            self.assertEqual(career_path.read_text(encoding="utf-8"), original)

            with self.assertRaisesRegex(ValueError, "contains duplicate ids"):
                add_record(career_path, "stories", {
                    "id": "invalid-story", "title": "Story", "evidence_ids": ["verified-proof", "verified-proof"],
                })

            with self.assertRaisesRegex(ValueError, "unverified evidence_ids: pending-proof"):
                CareerDocument.model_validate({
                    "schema_version": 2,
                    "evidence": [{"id": "pending-proof", "statement": "Pending fact"}],
                    "stories": [{"id": "story", "title": "Story", "evidence_ids": ["pending-proof"]}],
                })

    def test_legacy_saved_answer_without_evidence_ids_is_valid(self) -> None:
        career = CareerDocument.model_validate({
            "schema_version": 2,
            "answers": [{"id": "legacy-answer", "prompt": "Question?", "answer": "Answer."}],
        })

        self.assertEqual(career.answers[0].evidence_ids, [])

    def test_profile_and_record_edits_preserve_comments(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            career_path = project_path / "career.yml"
            career_path.write_text(
                "# Keep this comment\nschema_version: 2\nprofile: {}\n",
                encoding="utf-8",
            )

            set_profile(career_path, {"name": "Seriema"})
            add_record(career_path, "skills", {
                "id": "python", "tags": []
            })

            updated = career_path.read_text(encoding="utf-8")
            self.assertIn("# Keep this comment", updated)
            self.assertIn("id: python", updated)


class CareerCliTests(unittest.TestCase):
    def test_cli_edits_validates_and_lists_career_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            with redirect_stdout(StringIO()):
                result = main([
                    "career", "set-profile", str(project_path), "--name", "Seriema",
                    "--email", "seriema@example.invalid",
                    "--link", "github=https://github.com/seriema",
                ])
            self.assertEqual(result, 0)

            with redirect_stdout(StringIO()):
                result = main([
                    "career", "add-experience", str(project_path), "--id", "example-job",
                    "--company", "Example", "--start-date", "2024-01",
                ])
            self.assertEqual(result, 0)

            with redirect_stdout(StringIO()) as output:
                result = main(["career", "list", str(project_path), "experience"])
            self.assertEqual(result, 0)
            self.assertIn("example-job", output.getvalue())

            with redirect_stdout(StringIO()):
                result = main(["career", "validate", str(project_path)])
            self.assertEqual(result, 0)

    def test_cli_validate_prints_diagnostics_for_empty_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            stderr = StringIO()

            with redirect_stderr(stderr):
                result = main(["career", "validate", str(project_path)])

            self.assertEqual(result, 1)
            self.assertIn("profile.name", stderr.getvalue())

    def test_cli_merges_profile_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            with redirect_stdout(StringIO()):
                main([
                    "career", "set-profile", str(project_path), "--link",
                    "github=https://github.com/seriema", "--link",
                    "linkedin=https://linkedin.com/in/seriema",
                ])
                result = main([
                    "career", "set-profile", str(project_path), "--link",
                    "portfolio=https://example.com",
                ])

            self.assertEqual(result, 0)
            profile = load_career(project_path / "career.yml").profile
            self.assertEqual(set(profile.links), {"github", "linkedin", "portfolio"})

    def test_cli_adds_and_lists_reusable_answers_and_stories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            with redirect_stdout(StringIO()):
                main([
                    "career", "add-evidence", str(project_path), "--id", "proof",
                    "--statement", "Verified fact", "--verified",
                ])
                answer_result = main([
                    "career", "add-answer", str(project_path), "--id", "availability",
                    "--prompt", "When can you start?", "--answer", "Immediately.",
                    "--tag", "availability", "--evidence-id", "proof",
                ])
                story_result = main([
                    "career", "add-story", str(project_path), "--id", "delivery",
                    "--title", "Delivery", "--situation", "A need existed.",
                    "--action", "Delivered it.", "--result", "Released.",
                    "--evidence-id", "proof",
                ])
            self.assertEqual(answer_result, 0)
            self.assertEqual(story_result, 0)

            with redirect_stdout(StringIO()) as output:
                result = main(["career", "list", str(project_path), "answers"])
            self.assertEqual(result, 0)
            self.assertIn("evidence_ids:\n  - proof", output.getvalue())

            career = load_career(project_path / "career.yml")
            self.assertEqual(career.stories[0].evidence_ids, ["proof"])

    def test_cli_reports_invalid_yaml_instead_of_raising(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            (project_path / "career.yml").write_text("profile: [\n", encoding="utf-8")
            stderr = StringIO()

            with redirect_stderr(stderr):
                result = main([
                    "career", "set-profile", str(project_path), "--name", "Seriema",
                ])

            self.assertEqual(result, 1)
            self.assertIn("expected", stderr.getvalue().lower())


def _create_project(temporary_directory: str) -> Path:
    project_path = Path(temporary_directory) / "my-career"
    create_project(project_path, project_name="My Career")
    return project_path
