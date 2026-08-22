from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from seriemacv.project import (
    PROJECT_ARTIFACTS,
    PROJECT_DIRECTORIES,
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
            for relative_directory in PROJECT_DIRECTORIES:
                self.assertTrue((project_path / relative_directory).is_dir())
            for relative_path in PROJECT_ARTIFACTS:
                self.assertTrue((project_path / relative_path).is_file())
            self.assertEqual(validate_project(project_path), [])

    def test_refuses_to_overwrite_an_existing_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            create_project(project_path, project_name="My Career")

            with self.assertRaises(ProjectAlreadyExistsError):
                create_project(project_path, project_name="Other Career")


class ValidateProjectTests(unittest.TestCase):
    def test_reports_missing_required_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            create_project(project_path, project_name="My Career")
            (project_path / "resume" / "variants").rmdir()
            (project_path / "resume" / "master.md").unlink()
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
