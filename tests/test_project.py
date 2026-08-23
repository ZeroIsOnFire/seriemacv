from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from seriemacv.jobs import load_yaml_payload
from seriemacv.project import (
    PROJECT_ARTIFACTS,
    PROJECT_DIRECTORIES,
    PROJECT_EXAMPLES,
    InvalidProjectError,
    ProjectAlreadyExistsError,
    create_project,
    open_project,
    validate_project,
)


class CreateProjectTests(unittest.TestCase):
    def test_creates_portable_career_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"

            created = create_project(project_path, project_name="My Career")

            self.assertEqual(created, project_path)
            self.assertTrue((project_path / "seriemacv.yml").is_file())
            self.assertTrue((project_path / "seriemacv.yml.example").is_file())
            self.assertTrue((project_path / "career.yml.example").is_file())
            self.assertTrue((project_path / "job.yml.example").is_file())
            self.assertIn(
                "resume_style: clean",
                (project_path / "seriemacv.yml.example").read_text(encoding="utf-8"),
            )
            job_template = (project_path / "job.yml.example").read_text(encoding="utf-8")
            job = load_yaml_payload(job_template)
            self.assertEqual(job.id, "example-platform-engineer")
            self.assertTrue(job.description)
            self.assertIn("120,000", job.salary_range)
            for relative_directory in PROJECT_DIRECTORIES:
                self.assertTrue((project_path / relative_directory).is_dir())
            for relative_path in PROJECT_ARTIFACTS:
                self.assertTrue((project_path / relative_path).is_file())
            self.assertEqual(validate_project(project_path), [])

    def test_repository_examples_match_init_templates(self) -> None:
        repository_path = Path(__file__).resolve().parents[1]

        self.assertEqual(
            (repository_path / "examples" / "career.yml").read_text(encoding="utf-8"),
            PROJECT_EXAMPLES["career.yml.example"],
        )
        self.assertEqual(
            (repository_path / "examples" / "job.yml").read_text(encoding="utf-8"),
            PROJECT_EXAMPLES["job.yml.example"],
        )

    def test_refuses_to_overwrite_an_existing_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            create_project(project_path, project_name="My Career")

            with self.assertRaises(ProjectAlreadyExistsError):
                create_project(project_path, project_name="Other Career")

    def test_stores_resume_language_and_style_in_project_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"

            create_project(
                project_path,
                project_name="My Career",
                resume_language="en",
                resume_style="modern",
            )

            config = (project_path / "seriemacv.yml").read_text(encoding="utf-8")
            self.assertIn("resume_language: en", config)
            self.assertIn("resume_style: modern", config)

    def test_legacy_configuration_defaults_to_clean_style(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            create_project(project_path, project_name="My Career")
            config_path = project_path / "seriemacv.yml"
            config_path.write_text(
                "schema_version: 1\nproject_name: My Career\nresume_language: en\n",
                encoding="utf-8",
            )

            project = open_project(project_path)

            self.assertEqual(project.resume_style, "clean")


class ValidateProjectTests(unittest.TestCase):
    def test_reports_missing_required_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            create_project(project_path, project_name="My Career")
            (project_path / "resume" / "variants").rmdir()
            (project_path / "resume").rmdir()

            errors = validate_project(project_path)

            self.assertIn("Required directory is missing: resume", errors)

    def test_reports_unsupported_configuration_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            create_project(project_path, project_name="My Career")
            (project_path / "seriemacv.yml").write_text(
                "schema_version: 2\nproject_name: My Career\n",
                encoding="utf-8",
            )

            errors = validate_project(project_path)

            self.assertTrue(
                any("schema_version" in error and "1" in error for error in errors)
            )

    def test_rejects_unknown_configuration_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            create_project(project_path, project_name="My Career")
            (project_path / "seriemacv.yml").write_text(
                "schema_version: 1\nproject_name: My Career\nunexpected: true\n",
                encoding="utf-8",
            )

            errors = validate_project(project_path)

            self.assertTrue(any("unexpected" in error for error in errors))


class OpenProjectTests(unittest.TestCase):
    def test_opens_a_valid_project_and_its_local_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            create_project(project_path, project_name="My Career")

            project = open_project(project_path)

            self.assertEqual(project.path, project_path)
            self.assertEqual(project.name, "My Career")
            self.assertTrue(project.database_path.is_file())
            self.assertEqual(project.database_schema_version, 1)

    def test_refuses_to_open_an_invalid_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaises(InvalidProjectError):
                open_project(Path(temporary_directory))

    def test_opens_a_project_created_with_the_legacy_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "legacy-career"
            _create_legacy_project(project_path)

            project = open_project(project_path)

            self.assertEqual(project.path, project_path)
            self.assertEqual(validate_project(project_path), [])


def _create_legacy_project(project_path: Path) -> None:
    directories = (
        "resume/variants",
        "jobs/sources",
        "applications",
        "knowledge",
        "styles",
        "exports",
        ".seriemacv/cache",
        ".seriemacv/browser",
        ".seriemacv/index",
    )
    for relative_directory in directories:
        (project_path / relative_directory).mkdir(parents=True, exist_ok=True)
    artifacts = {
        "profile.yml": "name: Legacy\nlocation: ''\nemail: ''\n",
        "resume/master.md": "# Legacy\n",
        "knowledge/achievements.yml": "[]\n",
        "knowledge/skills.yml": "[]\n",
        "knowledge/answers.md": "# Answers\n",
        "knowledge/stories.md": "# Stories\n",
    }
    for relative_path, content in artifacts.items():
        (project_path / relative_path).write_text(content, encoding="utf-8")
    (project_path / "seriemacv.yml").write_text(
        "schema_version: 1\nproject_name: Legacy Career\n", encoding="utf-8"
    )
    database_path = project_path / ".seriemacv/index/seriemacv.db"
    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY)")
            connection.execute("INSERT INTO schema_migrations (version) VALUES (1)")
