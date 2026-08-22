from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from seriemacv.career import CareerDocument
from seriemacv.cli import main
from seriemacv.project import create_project
from seriemacv.renderer import (
    render_html,
    render_markdown,
    write_markdown_resume,
    write_resume,
)


class MarkdownRendererTests(unittest.TestCase):
    def test_html_is_semantic_and_escapes_canonical_content(self) -> None:
        career = self._career().model_copy(
            update={"summary": "<script>alert(1)</script>"}
        )

        rendered = render_html(career, "en")

        self.assertIn("<main>", rendered)
        self.assertIn("<section><h2>Summary</h2>", rendered)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertNotIn("<script>alert", rendered)

    def test_pdf_uses_fake_renderer_and_writes_only_pdf(self) -> None:
        class FakePdf:
            def render(self, html: str) -> bytes:
                self.html = html
                return b"%PDF-fake"

        with tempfile.TemporaryDirectory() as temporary_directory:
            fake = FakePdf()
            project_path = Path(temporary_directory)
            output_path = write_resume(project_path, self._career(), "en", "pdf", fake)

            self.assertEqual(output_path.name, "resume.pdf")
            self.assertEqual(output_path.read_bytes(), b"%PDF-fake")
            self.assertIn("Professional Experience", fake.html)
            self.assertFalse((project_path / "exports/resume.html").exists())

    def test_renders_localized_headings_and_preserves_user_content(self) -> None:
        career = self._career()

        portuguese = render_markdown(career, "pt-BR")
        english = render_markdown(career, "en")

        self.assertIn("## Resumo", portuguese)
        self.assertIn("## Experiência profissional", portuguese)
        self.assertIn("## Formação acadêmica", portuguese)
        self.assertIn("## Summary", english)
        self.assertIn("## Professional Experience", english)
        self.assertIn("Texto canônico sem tradução.", english)
        self.assertIn("Software Engineer", english)

    def test_omits_empty_sections_and_hides_non_resume_sections(self) -> None:
        career = CareerDocument.model_validate(
            {
                "schema_version": 1,
                "profile": {
                    "name": "Avery Example",
                    "title": "Engineer",
                    "email": "avery@example.invalid",
                },
                "evidence": [{"id": "private-proof", "statement": "Do not render"}],
            }
        )

        rendered = render_markdown(career, "en")

        self.assertNotIn("## Summary", rendered)
        self.assertNotIn("## Professional Experience", rendered)
        self.assertNotIn("## Education", rendered)
        self.assertNotIn("## Skills", rendered)
        self.assertNotIn("## Languages", rendered)
        self.assertNotIn("Do not render", rendered)

    def test_orders_dated_sections_in_reverse_chronology_and_keeps_skill_order(
        self,
    ) -> None:
        rendered = render_markdown(self._career(), "en")

        self.assertLess(rendered.index("Current Corp"), rendered.index("Earlier Corp"))
        self.assertLess(
            rendered.index("New University"), rendered.index("Old University")
        )
        self.assertLess(rendered.index("Python"), rendered.index("YAML"))
        self.assertIn("Jan 2024 — Present", rendered)
        self.assertIn("Remote | Contract", rendered)

    def test_writes_the_single_resume_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory)
            exports_path = project_path / "exports"
            exports_path.mkdir()
            output_path = write_markdown_resume(project_path, self._career(), "pt-BR")

            self.assertEqual(output_path, exports_path / "resume.md")
            self.assertTrue(output_path.exists())

    def test_atomic_write_keeps_existing_artifact_when_replacement_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory)
            exports_path = project_path / "exports"
            exports_path.mkdir()
            output_path = exports_path / "resume.md"
            output_path.write_text("previous artifact", encoding="utf-8")

            with patch(
                "seriemacv.renderer.os.replace", side_effect=OSError("disk error")
            ):
                with self.assertRaises(OSError):
                    write_markdown_resume(project_path, self._career(), "en")

            self.assertEqual(
                output_path.read_text(encoding="utf-8"), "previous artifact"
            )
            self.assertEqual(list(exports_path.glob(".resume.md.*.tmp")), [])

    @staticmethod
    def _career() -> CareerDocument:
        return CareerDocument.model_validate(
            {
                "schema_version": 1,
                "profile": {
                    "name": "Avery Example",
                    "title": "Software Engineer",
                    "location": "Remote",
                    "email": "avery@example.invalid",
                    "phone": "+1 555 0100",
                    "links": {"Portfolio": "https://example.invalid/avery"},
                    "languages": ["Portuguese", "English"],
                },
                "summary": "Texto canônico sem tradução.",
                "experience": [
                    {
                        "id": "earlier-corp",
                        "company": "Earlier Corp",
                        "title": "Developer",
                        "start_date": "2020-01",
                        "end_date": "2023-12",
                    },
                    {
                        "id": "current-corp",
                        "company": "Current Corp",
                        "title": "Software Engineer",
                        "start_date": "2024-01",
                        "location": "Remote",
                        "employment_type": "Contract",
                        "highlights": ["Built reliable tools."],
                    },
                ],
                "education": [
                    {
                        "id": "old-university",
                        "institution": "Old University",
                        "degree": "BSc",
                        "start_date": "2014-01",
                        "end_date": "2018-12",
                    },
                    {
                        "id": "new-university",
                        "institution": "New University",
                        "degree": "MSc",
                        "start_date": "2021-01",
                        "end_date": "2023-12",
                    },
                ],
                "skills": [
                    {"id": "python", "name": "Python"},
                    {"id": "yaml", "name": "YAML"},
                ],
            }
        )


class ResumeRenderCliTests(unittest.TestCase):
    def test_cli_uses_project_resume_language_and_writes_single_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career-project"
            create_project(
                project_path, project_name="Career Project", resume_language="en"
            )
            career_path = project_path / "career.yml"
            career_path.write_text(
                """schema_version: 1
profile:
  name: Avery Example
  title: Engineer
  email: avery@example.invalid
summary: Canonical content.
experience: []
education: []
skills: []
evidence: []
answers: []
stories: []
""",
                encoding="utf-8",
            )

            result = main(
                [
                    "resume",
                    "render",
                    str(project_path),
                    "--format",
                    "markdown",
                ]
            )

            self.assertEqual(result, 0)
            output_path = project_path / "exports/resume.md"
            self.assertTrue(output_path.exists())
            self.assertIn("## Summary", output_path.read_text(encoding="utf-8"))

            result = main([
                "resume", "render", str(project_path), "--format", "html",
            ])

            self.assertEqual(result, 0)
            self.assertTrue((project_path / "exports/resume.html").exists())

    def test_cli_does_not_overwrite_artifact_when_career_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career-project"
            create_project(project_path, project_name="Career Project")
            output_path = project_path / "exports/resume.md"
            output_path.write_text("previous artifact", encoding="utf-8")
            stderr = StringIO()

            with redirect_stderr(stderr):
                result = main(
                    [
                        "resume",
                        "render",
                        str(project_path),
                        "--format",
                        "markdown",
                    ]
                )

            self.assertEqual(result, 1)
            self.assertIn("profile.name", stderr.getvalue())
            self.assertEqual(
                output_path.read_text(encoding="utf-8"), "previous artifact"
            )

    def test_cli_reports_invalid_project_configuration_at_its_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career-project"
            create_project(project_path, project_name="Career Project")
            (project_path / "career.yml").write_text(
                """schema_version: 1
profile:
  name: Avery Example
  title: Engineer
  email: avery@example.invalid
experience: []
education: []
skills: []
evidence: []
answers: []
stories: []
""",
                encoding="utf-8",
            )
            configuration_path = project_path / "seriemacv.yml"
            configuration_path.write_text(
                "schema_version: 1\nproject_name: Career Project\nresume_language: fr\n",
                encoding="utf-8",
            )
            stderr = StringIO()

            with redirect_stderr(stderr):
                result = main(
                    [
                        "resume",
                        "render",
                        str(project_path),
                        "--format",
                        "markdown",
                    ]
                )

            self.assertEqual(result, 1)
            self.assertIn(str(configuration_path), stderr.getvalue())
            self.assertFalse((project_path / "exports/resume.md").exists())
