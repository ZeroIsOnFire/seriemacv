from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from seriemacv.career import add_record, load_career, set_profile, validate_career
from seriemacv.cli import main
from seriemacv.project import create_project


class CareerSchemaTests(unittest.TestCase):
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
