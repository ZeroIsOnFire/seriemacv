from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from seriemacv.jobs import (
    JobDocument,
    JobImportPayload,
    JobSource,
    create_job,
    import_jobs,
    job_path,
    load_job,
    load_jobs,
    load_json_payload,
    load_yaml_payload,
    source_format_for_path,
    validate_job,
    validate_jobs,
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
            path = project_path / "jobs" / "broken.yml"
            path.write_text(
                "schema_version: 1\nid: broken\ntitle: Engineer\nsource:\n"
                "  format: manual\n  content: Description\nrequirements:\n"
                "  - id: python\n    statement: Python\n    priority: invalid\n",
                encoding="utf-8",
            )

            diagnostics = validate_job(path)

            self.assertEqual(diagnostics[0].path, "requirements.0.priority")
            self.assertIsNotNone(diagnostics[0].line)


class DormantJobDomainTests(unittest.TestCase):
    def test_domain_still_creates_lists_loads_and_validates_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            payload = JobImportPayload(
                schema_version=1,
                id="example-role",
                title="Platform Engineer",
                description="Build reliable systems.",
                requirements=[
                    {
                        "id": "python",
                        "statement": "Professional Python experience",
                        "priority": "required",
                    }
                ],
            )
            source = JobSource(format="manual", content="Build reliable systems.")

            saved = create_job(project_path, payload, source)

            self.assertEqual(saved, job_path(project_path, "example-role"))
            self.assertEqual(load_job(saved).title, "Platform Engineer")
            self.assertEqual(load_jobs(project_path)[0].id, "example-role")
            self.assertEqual(validate_job(saved), [])
            self.assertEqual(validate_jobs(project_path), [])
            with self.assertRaises(FileExistsError):
                create_job(project_path, payload, source)

    def test_structured_parsers_remain_available_while_cli_is_hidden(self) -> None:
        yaml_text = (
            "schema_version: 1\nid: Platform-Engineer\ntitle: Platform Engineer\n"
            "requirements:\n  - id: python\n    statement: Python\n"
            "    priority: required\n"
        )
        json_text = (
            '{"schema_version": 1, "id": "data-engineer", '
            '"title": "Data Engineer"}'
        )

        yaml_payload = load_yaml_payload(yaml_text)
        json_payload = load_json_payload(json_text)

        self.assertEqual(yaml_payload.id, "platform-engineer")
        self.assertEqual(json_payload.id, "data-engineer")
        self.assertEqual(source_format_for_path(Path("role.yaml")), "yaml")
        self.assertEqual(source_format_for_path(Path("role.json")), "json")
        with self.assertRaisesRegex(ValueError, "Unsupported job source format"):
            source_format_for_path(Path("role.md"))

    def test_imports_all_yaml_jobs_from_a_zip_without_extracting_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            archive_path = Path(temporary_directory) / "jobs.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("first.yaml", _job_yaml("first-role", "First Role"))
                archive.writestr("nested/second.yml", _job_yaml("second-role", "Second Role"))
                archive.writestr("README.md", "Ignored")

            paths = import_jobs(project_path, archive_path)

            self.assertEqual([path.name for path in paths], ["first-role.yml", "second-role.yml"])
            self.assertEqual(validate_job(paths[0]), [])
            self.assertEqual(load_job(paths[0]).source.filename, "jobs.zip!first.yaml")
            with self.assertRaisesRegex(FileExistsError, "already exist"):
                import_jobs(project_path, archive_path)


def _create_project(temporary_directory: str) -> Path:
    project_path = Path(temporary_directory) / "my-career"
    create_project(project_path, project_name="My Career")
    return project_path


def _job_yaml(job_id: str, title: str) -> str:
    return f"schema_version: 1\nid: {job_id}\ntitle: {title}\n"
