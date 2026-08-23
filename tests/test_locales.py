from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from seriemacv.career import list_locales, load_localized_career, validate_locale
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
catalog:
  labels: {summary: Summary, experience: Experience, education: Education, skills: Skills, languages: Languages, current: Present, other: Other, level.beginner: Beginner, level.intermediate: Intermediate, level.advanced: Advanced, level.expert: Expert}
  months: [Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec]
  date_format: '{month} {year}'
profile: {title: Engineer, location: Remote}
summary: Localized summary.
experience: {example: {title: Developer}}
education: {}
skills: {}
'''


class LocalizedCareerTests(unittest.TestCase):
    def test_composes_facts_and_renders_multiple_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career", resume_language="en")
            (project_path / "career.yml").write_text(FACTS, encoding="utf-8")
            (project_path / "career.locales" / "en.yml").write_text(LOCALE, encoding="utf-8")

            career = load_localized_career(project_path, "en")

            self.assertEqual(career.profile.title, "Engineer")
            self.assertEqual(career.experience[0].title, "Developer")
            self.assertEqual(main(["resume", "render", str(project_path), "--format", "markdown", "--format", "html"]), 0)
            self.assertTrue((project_path / "exports" / "resume.en.md").is_file())
            self.assertTrue((project_path / "exports" / "resume.en.html").is_file())

    def test_rejects_missing_record_translation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            (project_path / "career.yml").write_text(FACTS, encoding="utf-8")
            (project_path / "career.locales" / "en.yml").write_text(LOCALE.replace("experience: {example: {title: Developer}}", "experience: {}"), encoding="utf-8")

            self.assertTrue(validate_locale(project_path, "en"))
