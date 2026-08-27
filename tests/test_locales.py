from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from seriemacv.career import load_localized_career, validate_locale
from seriemacv.cli import main
from seriemacv.project import create_project

FACTS = '''schema_version: 2
profile: {name: Example, email: example@example.invalid}
experience:
  - {id: example, company: Example Co, start_date: 2024-01}
education: []
skills: []
evidence: []
answers: []
stories: []
'''

LOCALE = '''schema_version: 1
locale: en
profile: {title: Engineer, location: Remote}
summary: Localized summary.
experience: {example: {title: Developer}}
education: {}
skills: {}
'''

I18N = '''schema_version: 1
locale: en
labels: {summary: Summary, experience: Experience, education: Education, skills: Skills, languages: Languages, current: Present, other: Other, level.beginner: Beginner, level.intermediate: Intermediate, level.advanced: Advanced, level.expert: Expert}
months: [Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec]
date_format: '{month} {year}'
'''


class LocalizedCareerTests(unittest.TestCase):
    def test_composes_facts_and_renders_multiple_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career", resume_language="en")
            (project_path / "career.yml").write_text(FACTS, encoding="utf-8")
            (project_path / "career.locales" / "en.yml").write_text(LOCALE, encoding="utf-8")
            (project_path / "i18n" / "en.yml").write_text(I18N, encoding="utf-8")

            career = load_localized_career(project_path, "en")

            self.assertEqual(career.profile.title, "Engineer")
            self.assertEqual(career.experience[0].title, "Developer")
            self.assertEqual(main(["resume", "render", str(project_path), "--format", "markdown", "--format", "html"]), 0)
            self.assertTrue((project_path / "exports" / "resume.en.md").is_file())
            self.assertTrue((project_path / "exports" / "resume.en.html").is_file())

    def test_custom_language_keeps_resume_wording_separate_from_i18n(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            (project_path / "career.yml").write_text(FACTS, encoding="utf-8")
            (project_path / "career.locales" / "es.yml").write_text(
                LOCALE.replace("locale: en", "locale: es")
                .replace("Engineer", "Ingeniero")
                .replace("Developer", "Desarrollador"),
                encoding="utf-8",
            )
            (project_path / "i18n" / "es.yml").write_text(
                I18N.replace("locale: en", "locale: es")
                .replace("Summary", "Resumen")
                .replace("Experience", "Experiencia")
                .replace("Present", "Actual")
                .replace(
                    "[Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec]",
                    "[Ene, Feb, Mar, Abr, May, Jun, Jul, Ago, Sep, Oct, Nov, Dic]",
                )
                .replace("'{month} {year}'", "'{month} de {year}'"),
                encoding="utf-8",
            )

            career = load_localized_career(project_path, "es")

            self.assertEqual(career.profile.title, "Ingeniero")
            self.assertEqual(career.catalog.labels["summary"], "Resumen")
            self.assertEqual(career.catalog.months[0], "Ene")
            self.assertEqual(career.catalog.date_format, "{month} de {year}")

    def test_rejects_missing_record_translation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            (project_path / "career.yml").write_text(FACTS, encoding="utf-8")
            (project_path / "career.locales" / "en.yml").write_text(LOCALE.replace("experience: {example: {title: Developer}}", "experience: {}"), encoding="utf-8")
            (project_path / "i18n" / "en.yml").write_text(I18N, encoding="utf-8")

            self.assertTrue(validate_locale(project_path, "en"))

    def test_requires_a_separate_i18n_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            (project_path / "career.yml").write_text(FACTS, encoding="utf-8")
            (project_path / "career.locales" / "es.yml").write_text(
                LOCALE.replace("locale: en", "locale: es"),
                encoding="utf-8",
            )

            diagnostics = validate_locale(project_path, "es")

            self.assertEqual(len(diagnostics), 1)
            self.assertIn("i18n document is missing", diagnostics[0].message)
            self.assertIn("es.yml", diagnostics[0].message)

    def test_rejects_catalog_inside_career_locale(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            (project_path / "career.yml").write_text(FACTS, encoding="utf-8")
            (project_path / "career.locales" / "en.yml").write_text(
                LOCALE.replace(
                    "profile:",
                    "catalog: {}\nprofile:",
                ),
                encoding="utf-8",
            )

            diagnostics = validate_locale(project_path, "en")

            self.assertEqual(len(diagnostics), 1)
            self.assertIn("catalog", diagnostics[0].message)
