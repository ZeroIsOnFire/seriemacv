from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from seriemacv.cli import main
from seriemacv.jobs import (
    JobDocument,
    JobImportPayload,
    JobSource,
    create_job,
    load_job,
    validate_job,
)
from seriemacv.project import create_project


class JobSchemaTests(unittest.TestCase):
    def test_job_document_requires_title_and_rejects_unknown_fields(self) -> None:
        with self.assertRaises(ValueError):
            JobDocument.model_validate({"schema_version": 1, "id": "missing-title"})

        with self.assertRaises(ValueError):
            JobImportPayload.model_validate({
                "schema_version": 1,
                "id": "example-role",
                "title": "Engineer",
                "unexpected": True,
            })

        with self.assertRaises(ValueError):
            JobImportPayload.model_validate({
                "schema_version": 1,
                "id": "blank-title",
                "title": "   ",
            })

    def test_job_document_rejects_duplicate_ids_and_invalid_priority(self) -> None:
        base = {
            "schema_version": 1,
            "id": "example-role",
            "title": "Engineer",
            "source": {"format": "manual", "content": "Job description"},
            "requirements": [
                {"id": "python", "statement": "Python", "priority": "required"},
                {"id": "python", "statement": "More Python", "priority": "preferred"},
            ],
        }
        with self.assertRaises(ValueError):
            JobDocument.model_validate(base)

        base["requirements"][1]["id"] = "sql"
        base["requirements"][1]["priority"] = "important"
        with self.assertRaises(ValueError):
            JobDocument.model_validate(base)

    def test_validation_reports_field_location(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            job_path = project_path / "jobs" / "broken.yml"
            job_path.write_text(
                "schema_version: 1\nid: broken\ntitle: Engineer\nsource:\n"
                "  format: manual\n  content: Description\nrequirements:\n"
                "  - id: python\n    statement: Python\n    priority: invalid\n",
                encoding="utf-8",
            )

            diagnostics = validate_job(job_path)

            self.assertEqual(diagnostics[0].path, "requirements.0.priority")
            self.assertIsNotNone(diagnostics[0].line)

    def test_create_job_is_atomic_and_does_not_overwrite_existing_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            source = JobSource(format="manual", content="Build resilient systems.")
            payload = JobImportPayload(
                schema_version=1, id="example-role", title="Engineer"
            )
            job_path = create_job(project_path, payload, source)
            original = job_path.read_text(encoding="utf-8")

            with self.assertRaises(FileExistsError):
                create_job(project_path, payload, source)

            self.assertEqual(job_path.read_text(encoding="utf-8"), original)


class JobCliTests(unittest.TestCase):
    def test_cli_add_validate_list_and_show_job(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            with redirect_stdout(StringIO()):
                result = main([
                    "jobs", "add", str(project_path), "--id", "example-role",
                    "--title", "Platform Engineer", "--company", "Example Co",
                    "--description", "Build reliable systems.",
                    "--requirement", "python=Professional Python experience",
                    "--preferred-requirement", "aws=AWS experience",
                ])
            self.assertEqual(result, 0)

            job = load_job(project_path / "jobs" / "example-role.yml")
            self.assertEqual(job.source.format, "manual")
            self.assertEqual(job.source.content, "Build reliable systems.")
            self.assertEqual(job.description, "Build reliable systems.")
            self.assertEqual(
                [requirement.priority for requirement in job.requirements],
                ["required", "preferred"],
            )

            with redirect_stdout(StringIO()) as output:
                result = main(["jobs", "list", str(project_path)])
            self.assertEqual(result, 0)
            self.assertIn("example-role", output.getvalue())

            with redirect_stdout(StringIO()) as output:
                result = main(["jobs", "show", str(project_path), "example-role"])
            self.assertEqual(result, 0)
            self.assertIn("Platform Engineer", output.getvalue())

            with redirect_stdout(StringIO()):
                result = main(["jobs", "validate", str(project_path)])
            self.assertEqual(result, 0)

    def test_cli_imports_structured_yaml_and_preserves_raw_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            source_path = Path(temporary_directory) / "role.yml"
            source_text = (
                "schema_version: 1\nid: platform-engineer\ntitle: Platform Engineer\n"
                "requirements:\n  - id: python\n    statement: Professional Python experience\n"
                "    priority: required\n"
            )
            source_path.write_text(source_text, encoding="utf-8")

            with redirect_stdout(StringIO()):
                result = main(["jobs", "import", str(project_path), str(source_path)])

            self.assertEqual(result, 0)
            job = load_job(project_path / "jobs" / "platform-engineer.yml")
            self.assertEqual(job.source.format, "yaml")
            self.assertEqual(job.source.filename, "role.yml")
            self.assertEqual(job.source.content, source_text)
            self.assertEqual(job.requirements[0].id, "python")

    def test_cli_normalizes_uppercase_import_ids_without_changing_raw_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            source_path = Path(temporary_directory) / "role.yaml"
            source_text = "schema_version: 1\nid: Insi-OX4UST\ntitle: Ruby Developer\n"
            source_path.write_text(source_text, encoding="utf-8")

            with redirect_stdout(StringIO()):
                result = main(["jobs", "import", str(project_path), str(source_path)])

            self.assertEqual(result, 0)
            job = load_job(project_path / "jobs" / "insi-ox4ust.yml")
            self.assertEqual(job.id, "insi-ox4ust")
            self.assertEqual(job.source.content, source_text)

    def test_cli_imports_structured_json_and_preserves_raw_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            source_path = Path(temporary_directory) / "role.json"
            source_text = (
                '{"schema_version": 1, "id": "data-engineer", '
                '"title": "Data Engineer", "requirements": '
                '[{"id": "sql", "statement": "Advanced SQL", '
                '"priority": "required"}]}'
            )
            source_path.write_text(source_text, encoding="utf-8")

            with redirect_stdout(StringIO()):
                result = main(["jobs", "import", str(project_path), str(source_path)])

            self.assertEqual(result, 0)
            job = load_job(project_path / "jobs" / "data-engineer.yml")
            self.assertEqual(job.requirements[0].id, "sql")
            self.assertEqual(job.source.format, "json")
            self.assertEqual(job.source.content, source_text)

    def test_cli_rejects_malformed_json_without_creating_job(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            source_path = Path(temporary_directory) / "broken.json"
            source_path.write_text('{"schema_version": 1,', encoding="utf-8")
            stderr = StringIO()

            with redirect_stderr(stderr):
                result = main(["jobs", "import", str(project_path), str(source_path)])

            self.assertEqual(result, 1)
            self.assertIn("invalid JSON", stderr.getvalue())
            self.assertEqual(list((project_path / "jobs").glob("*.yml")), [])

    def test_cli_validates_all_job_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            (project_path / "jobs" / "broken.yml").write_text(
                "schema_version: 1\nid: broken\ntitle: Engineer\n",
                encoding="utf-8",
            )
            stderr = StringIO()

            with redirect_stderr(stderr):
                result = main(["jobs", "validate", str(project_path)])

            self.assertEqual(result, 1)
            self.assertIn("source", stderr.getvalue())

    def test_cli_rejects_an_invalid_job_id_before_resolving_a_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            stderr = StringIO()

            with redirect_stderr(stderr):
                result = main(["jobs", "show", str(project_path), "../career"])

            self.assertEqual(result, 1)
            self.assertIn("kebab-case", stderr.getvalue())

    def test_cli_rejects_invalid_input_without_creating_job(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            unsupported_path = Path(temporary_directory) / "role.md"
            unsupported_path.write_text("# A job description", encoding="utf-8")
            stderr = StringIO()

            with redirect_stderr(stderr):
                result = main(["jobs", "import", str(project_path), str(unsupported_path)])

            self.assertEqual(result, 1)
            self.assertIn("Unsupported job source format", stderr.getvalue())
            self.assertFalse((project_path / "jobs" / "role.yml").exists())


def _create_project(temporary_directory: str) -> Path:
    project_path = Path(temporary_directory) / "my-career"
    create_project(project_path, project_name="My Career")
    return project_path
