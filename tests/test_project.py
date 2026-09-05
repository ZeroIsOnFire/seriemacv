from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ruamel.yaml import YAML

from seriemacv.career import CareerLocaleDocument, I18nDocument
from seriemacv.jobs import load_yaml_payload
from seriemacv.project import (
    PROJECT_ARTIFACTS,
    PROJECT_DIRECTORIES,
    PROJECT_EXAMPLES,
    InvalidProjectError,
    ProjectAlreadyExistsError,
    create_project,
    load_project_configuration,
    open_project,
    validate_project,
)
from seriemacv.variants import ResumeVariant, ResumeVariantLocale


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
            self.assertTrue((project_path / "variant.yml.example").is_file())
            self.assertTrue((project_path / "variant-locale.yml.example").is_file())
            self.assertTrue((project_path / "i18n" / "pt-BR.yml").is_file())
            self.assertTrue((project_path / "i18n" / "en.yml").is_file())
            self.assertNotIn(
                "catalog:",
                (project_path / "career.locales" / "pt-BR.yml").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertIn(
                "resume_style: clean",
                (project_path / "seriemacv.yml.example").read_text(encoding="utf-8"),
            )
            job_template = (project_path / "job.yml.example").read_text(
                encoding="utf-8"
            )
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
        yaml = YAML(typ="safe")

        self.assertEqual(
            (repository_path / "examples" / "career.yml").read_text(encoding="utf-8"),
            PROJECT_EXAMPLES["career.yml.example"],
        )
        self.assertEqual(
            (repository_path / "examples" / "job.yml").read_text(encoding="utf-8"),
            PROJECT_EXAMPLES["job.yml.example"],
        )
        self.assertEqual(
            (repository_path / "examples" / "variant.yml").read_text(encoding="utf-8"),
            PROJECT_EXAMPLES["variant.yml.example"],
        )
        self.assertEqual(
            (repository_path / "examples" / "variant-locale.yml").read_text(
                encoding="utf-8"
            ),
            PROJECT_EXAMPLES["variant-locale.yml.example"],
        )
        for locale in ("pt-BR", "en"):
            career_locale = (
                repository_path / "examples" / f"career.locales.{locale}.yml"
            ).read_text(encoding="utf-8")
            i18n = (repository_path / "examples" / f"i18n.{locale}.yml").read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                career_locale,
                PROJECT_EXAMPLES[f"career.locales/{locale}.yml.example"],
            )
            self.assertEqual(i18n, PROJECT_EXAMPLES[f"i18n/{locale}.yml.example"])
            CareerLocaleDocument.model_validate(yaml.load(career_locale))
            I18nDocument.model_validate(yaml.load(i18n))
        ResumeVariant.model_validate(yaml.load(PROJECT_EXAMPLES["variant.yml.example"]))
        ResumeVariantLocale.model_validate(
            yaml.load(PROJECT_EXAMPLES["variant-locale.yml.example"])
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
            self.assertIn('resume_color: "#647D74"', config)

    def test_normalizes_resume_color_and_rejects_invalid_hexadecimal_value(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            create_project(project_path, project_name="My Career")
            config_path = project_path / "seriemacv.yml"
            config_path.write_text(
                "schema_version: 2\nproject_name: My Career\nresume_color: '#ab12cd'\n",
                encoding="utf-8",
            )

            self.assertEqual(
                load_project_configuration(project_path).resume_color, "AB12CD"
            )

            config_path.write_text(
                "schema_version: 2\nproject_name: My Career\nresume_color: blue\n",
                encoding="utf-8",
            )
            self.assertTrue(
                any("hexadecimal" in error for error in validate_project(project_path))
            )

    def test_legacy_configuration_defaults_to_clean_style(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            create_project(project_path, project_name="My Career")
            config_path = project_path / "seriemacv.yml"
            config_path.write_text(
                "schema_version: 2\nproject_name: My Career\nresume_language: en\n",
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
                "schema_version: 3\nproject_name: My Career\n",
                encoding="utf-8",
            )

            errors = validate_project(project_path)

            self.assertTrue(
                any("schema_version" in error and "2" in error for error in errors)
            )

    def test_rejects_unknown_configuration_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            create_project(project_path, project_name="My Career")
            (project_path / "seriemacv.yml").write_text(
                "schema_version: 2\nproject_name: My Career\nunexpected: true\n",
                encoding="utf-8",
            )

            errors = validate_project(project_path)

            self.assertTrue(any("unexpected" in error for error in errors))


class OpenProjectTests(unittest.TestCase):
    def test_opens_a_valid_yaml_project_without_a_local_database(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            create_project(project_path, project_name="My Career")

            project = open_project(project_path)

            self.assertEqual(project.path, project_path)
            self.assertEqual(project.name, "My Career")
            self.assertFalse((project_path / ".seriemacv/index").exists())

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
        "schema_version: 2\nproject_name: Legacy Career\n", encoding="utf-8"
    )
    (project_path / ".seriemacv/index/seriemacv.db").write_text(
        "legacy index retained by the user\n", encoding="utf-8"
    )
