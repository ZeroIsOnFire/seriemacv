from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from seriemacv.cli import main
from seriemacv.jobs import JobImportPayload, JobSource, create_job
from seriemacv.project import create_project
from seriemacv.variants import (
    ResumeVariantLocale,
    list_variants,
    load_variant_career,
    validate_variant,
    validate_variants,
)


class ResumeVariantTests(unittest.TestCase):
    def test_variant_experience_allows_only_one_highlight(self) -> None:
        with self.assertRaisesRegex(ValueError, "at most 1 item"):
            ResumeVariantLocale.model_validate({
                "schema_version": 1,
                "locale": "en",
                "experience": {
                    "example": {
                        "highlights": ["Primary achievement.", "Secondary achievement."]
                    }
                },
            })

    def test_variant_selects_reorders_and_overrides_localized_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)
            _write_variant(project_path)

            variant, career = load_variant_career(project_path, "backend-role", "en")

            self.assertEqual(variant.job_id, "platform-role")
            self.assertEqual(variant.style, "compact")
            self.assertEqual([item.id for item in career.experience], ["older", "current"])
            self.assertEqual([item.id for item in career.education], [])
            self.assertEqual([item.id for item in career.skills], ["python"])
            self.assertEqual(career.summary, "Backend engineer for reliable platforms.")
            self.assertEqual(career.profile.title, "Senior Backend Engineer")
            self.assertEqual(career.profile.location, "Sao Paulo, Brazil")
            self.assertEqual(career.experience[0].title, "Earlier Engineer")
            self.assertEqual(
                career.experience[1].highlights,
                ["Built reliable backend services."],
            )

    def test_variant_locale_is_optional_and_career_locale_is_inherited(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)
            _write_variant(project_path, with_locale=False)

            _, career = load_variant_career(project_path, "backend-role", "en")

            self.assertEqual(career.summary, "General software engineering summary.")
            self.assertEqual(career.profile.title, "Software Engineer")
            self.assertEqual([item.id for item in career.skills], ["python"])

    def test_validation_rejects_unknown_career_job_and_evidence_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)
            _write_variant(project_path)
            variant_path = project_path / "resume/variants/backend-role/variant.yml"
            variant_path.write_text(
                variant_path.read_text(encoding="utf-8")
                .replace("platform-role", "missing-job")
                .replace("skills: [python]", "skills: [missing-skill]"),
                encoding="utf-8",
            )
            locale_path = project_path / "resume/variants/backend-role/locales/en.yml"
            locale_path.write_text(
                locale_path.read_text(encoding="utf-8").replace(
                    "evidence_ids: [backend-delivery]",
                    "evidence_ids: [missing-evidence]",
                ),
                encoding="utf-8",
            )

            diagnostics = validate_variant(project_path, "backend-role")

            messages = "\n".join(item.message for item in diagnostics)
            self.assertIn("unknown job_id 'missing-job'", messages)
            self.assertIn("unknown skills ids: missing-skill", messages)
            self.assertIn("unknown evidence_ids: missing-evidence", messages)

    def test_validation_rejects_unknown_fields_and_directory_id_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)
            _write_variant(project_path)
            path = project_path / "resume/variants/backend-role/variant.yml"
            path.write_text(
                path.read_text(encoding="utf-8")
                .replace("id: backend-role", "id: another-role")
                .replace("job_id:", "unexpected: true\njob_id:"),
                encoding="utf-8",
            )

            diagnostics = validate_variant(project_path, "backend-role")

            messages = "\n".join(item.message for item in diagnostics)
            self.assertIn("Extra inputs are not permitted", messages)

    def test_validation_rejects_invalid_locale_filename_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)
            _write_variant(project_path, with_locale=False)
            locales_path = project_path / "resume/variants/backend-role/locales"
            (locales_path / "invalid locale.yml").write_text(
                "schema_version: 1\nlocale: en\n",
                encoding="utf-8",
            )
            (locales_path / "en.yml").write_text(
                "schema_version: 1\nlocale: en\nunexpected: true\n",
                encoding="utf-8",
            )

            diagnostics = validate_variant(project_path, "backend-role")

            messages = "\n".join(item.message for item in diagnostics)
            self.assertIn("filename must be a BCP 47 locale identifier", messages)
            self.assertIn("Extra inputs are not permitted", messages)

    def test_validation_requires_verified_evidence_for_tailored_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)
            _write_variant(project_path)
            locale_path = project_path / "resume/variants/backend-role/locales/en.yml"
            locale_path.write_text(
                locale_path.read_text(encoding="utf-8").replace(
                    "evidence_ids: [backend-delivery]\n", ""
                ),
                encoding="utf-8",
            )

            diagnostics = validate_variant(project_path, "backend-role")

            self.assertIn(
                "evidence_ids is required for a tailored summary or highlights",
                "\n".join(item.message for item in diagnostics),
            )

            _write_variant(project_path)
            career_path = project_path / "career.yml"
            career_path.write_text(
                career_path.read_text(encoding="utf-8").replace(
                    "verified: true", "verified: false"
                ),
                encoding="utf-8",
            )

            diagnostics = validate_variant(project_path, "backend-role")

            self.assertIn(
                "references unverified evidence_ids: backend-delivery",
                "\n".join(item.message for item in diagnostics),
            )

    def test_lists_only_valid_variant_directories_and_validates_all(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)
            _write_variant(project_path)
            (project_path / "resume/variants/notes").mkdir()

            self.assertEqual([item.id for item in list_variants(project_path)], ["backend-role"])
            self.assertEqual(validate_variants(project_path), [])


class ResumeVariantCliTests(unittest.TestCase):
    def test_cli_lists_validates_and_renders_named_variant_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)
            _write_variant(project_path)

            with redirect_stdout(StringIO()) as output:
                result = main(["resume", "variants", "list", str(project_path)])
            self.assertEqual(result, 0)
            self.assertIn("backend-role\tplatform-role\ten", output.getvalue())

            with redirect_stdout(StringIO()):
                result = main(
                    ["resume", "variants", "validate", str(project_path), "--id", "backend-role"]
                )
            self.assertEqual(result, 0)

            with redirect_stdout(StringIO()):
                result = main(
                    [
                        "resume",
                        "render",
                        str(project_path),
                        "--format",
                        "markdown",
                        "--language",
                        "en",
                        "--variant",
                        "backend-role",
                    ]
                )
            self.assertEqual(result, 0)
            output_path = project_path / "exports/resume.backend-role.en.md"
            rendered = output_path.read_text(encoding="utf-8")
            self.assertIn("Backend engineer for reliable platforms.", rendered)
            self.assertNotIn("Bachelor", rendered)
            self.assertLess(
                rendered.index("Earlier Engineer"),
                rendered.index("Senior Software Engineer"),
            )

            with redirect_stdout(StringIO()):
                result = main(
                    [
                        "resume",
                        "render",
                        str(project_path),
                        "--format",
                        "html",
                        "--language",
                        "en",
                        "--variant",
                        "backend-role",
                    ]
                )
            self.assertEqual(result, 0)
            html_path = project_path / "exports/resume.backend-role.en.html"
            self.assertIn('data-style="compact"', html_path.read_text(encoding="utf-8"))

            with redirect_stdout(StringIO()):
                result = main(
                    [
                        "resume",
                        "render",
                        str(project_path),
                        "--format",
                        "html",
                        "--language",
                        "en",
                        "--variant",
                        "backend-role",
                        "--style",
                        "clean",
                    ]
                )
            self.assertEqual(result, 0)
            self.assertIn('data-style="clean"', html_path.read_text(encoding="utf-8"))

    def test_cli_does_not_overwrite_variant_artifact_when_variant_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _complete_project(temporary_directory)
            _write_variant(project_path)
            output_path = project_path / "exports/resume.backend-role.en.md"
            output_path.write_text("previous artifact", encoding="utf-8")
            variant_path = project_path / "resume/variants/backend-role/variant.yml"
            variant_path.write_text(
                variant_path.read_text(encoding="utf-8").replace("python", "unknown"),
                encoding="utf-8",
            )

            with redirect_stderr(StringIO()):
                result = main(
                    [
                        "resume",
                        "render",
                        str(project_path),
                        "--format",
                        "markdown",
                        "--language",
                        "en",
                        "--variant",
                        "backend-role",
                    ]
                )

            self.assertEqual(result, 1)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "previous artifact")


def _complete_project(temporary_directory: str) -> Path:
    project_path = Path(temporary_directory) / "career-project"
    create_project(
        project_path,
        project_name="Career Project",
        resume_language="en",
        resume_style="modern",
    )
    (project_path / "career.yml").write_text(
        """schema_version: 2
profile:
  name: Seriema Example
  email: seriema@example.invalid
experience:
  - id: current
    company: Example Systems
    start_date: 2022-01
  - id: older
    company: Earlier Systems
    start_date: 2019-01
    end_date: 2021-12
education:
  - id: degree
    institution: Example University
    start_date: 2015-01
    end_date: 2018-12
skills:
  - id: python
    core: true
  - id: sql
evidence:
  - id: backend-delivery
    experience_id: current
    statement: Delivered reliable backend services.
    verified: true
answers: []
stories: []
""",
        encoding="utf-8",
    )
    (project_path / "career.locales/en.yml").write_text(
        """schema_version: 1
locale: en
profile: {title: Software Engineer, location: 'Sao Paulo, Brazil'}
summary: General software engineering summary.
experience:
  current: {title: Senior Software Engineer, highlights: [Built software.]}
  older: {title: Earlier Engineer, highlights: [Maintained software.]}
education:
  degree: {degree: Bachelor of Technology}
skills:
  python: {name: Python, category: Languages}
  sql: {name: SQL, category: Databases}
""",
        encoding="utf-8",
    )
    create_job(
        project_path,
        JobImportPayload(schema_version=1, id="platform-role", title="Platform Engineer"),
        JobSource(format="manual", content="Build reliable platforms."),
    )
    return project_path


def _write_variant(project_path: Path, *, with_locale: bool = True) -> None:
    variant_path = project_path / "resume/variants/backend-role"
    (variant_path / "locales").mkdir(parents=True, exist_ok=True)
    (variant_path / "variant.yml").write_text(
        """schema_version: 1
id: backend-role
job_id: platform-role
style: compact
selection:
  experience: [older, current]
  education: []
  skills: [python]
""",
        encoding="utf-8",
    )
    if with_locale:
        (variant_path / "locales/en.yml").write_text(
            """schema_version: 1
locale: en
evidence_ids: [backend-delivery]
profile:
  title: Senior Backend Engineer
summary: Backend engineer for reliable platforms.
experience:
  current:
    highlights: [Built reliable backend services.]
""",
            encoding="utf-8",
        )
