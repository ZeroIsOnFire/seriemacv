from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from seriemacv.cli import main


class CliTests(unittest.TestCase):
    def test_init_then_validate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            stdout = StringIO()

            with redirect_stdout(stdout):
                result = main(
                    [
                        "init",
                        str(project_path),
                        "--name",
                        "My Career",
                        "--language",
                        "en",
                        "--style",
                        "classic",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertIn("Created seriemaCV project", stdout.getvalue())
            self.assertIn(
                "resume_language: en",
                (project_path / "seriemacv.yml").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "resume_style: classic",
                (project_path / "seriemacv.yml").read_text(encoding="utf-8"),
            )

            with redirect_stdout(StringIO()):
                result = main(["validate", str(project_path)])

            self.assertEqual(result, 0)

    def test_validate_returns_nonzero_for_invalid_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            stderr = StringIO()

            with redirect_stderr(stderr):
                result = main(["validate", temporary_directory])

            self.assertEqual(result, 1)
            self.assertIn("seriemacv.yml", stderr.getvalue())

    def test_template_show_prints_career_job_and_variant_examples(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            with redirect_stdout(StringIO()):
                main(["init", str(project_path), "--name", "My Career"])

            with redirect_stdout(StringIO()) as output:
                result = main(["template", "show", str(project_path), "career"])
            self.assertEqual(result, 0)
            self.assertIn("Seriema Example", output.getvalue())

            with redirect_stdout(StringIO()) as output:
                result = main(["template", "show", str(project_path), "variant"])
            self.assertEqual(result, 0)
            self.assertIn("id: example-platform-variant", output.getvalue())

            with redirect_stdout(StringIO()) as output:
                result = main(["template", "show", str(project_path), "variant-locale"])
            self.assertEqual(result, 0)
            self.assertIn("evidence_ids: [example-service]", output.getvalue())

            with redirect_stdout(StringIO()) as output:
                result = main(["template", "show", str(project_path), "job"])
            self.assertEqual(result, 0)
            self.assertIn("id: example-platform-engineer", output.getvalue())

    def test_jobs_list_is_available_and_resume_styles_are_discoverable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            with redirect_stdout(StringIO()):
                main(["init", str(project_path), "--name", "My Career"])
            with redirect_stdout(StringIO()) as output:
                result = main(["jobs", "list", str(project_path)])
            self.assertEqual(result, 0)
            self.assertEqual(output.getvalue(), "[]\n")

        with redirect_stdout(StringIO()) as output:
            result = main(["resume", "styles"])

        self.assertEqual(result, 0)
        self.assertIn("clean\tClean\tsingle-column\tATS-safe", output.getvalue())
        self.assertIn(
            "classic-alt\tClassic Alt\tsingle-column\tATS-safe",
            output.getvalue(),
        )
        self.assertIn(
            "clean-executive-alt\tClean Executive Alt\tsingle-column\tATS-safe",
            output.getvalue(),
        )
        self.assertIn(
            "timeline\tTimeline\ttimeline\texperimental",
            output.getvalue(),
        )
        self.assertIn("sidebar\tSidebar\ttwo-column\texperimental", output.getvalue())
        self.assertIn(
            "sidebar-alt\tSidebar Alt\ttwo-column\texperimental",
            output.getvalue(),
        )

    def test_jobs_import_is_available_for_structured_local_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            source_path = Path(temporary_directory) / "role.yml"
            source_path.write_text(
                "schema_version: 1\nid: platform-role\ntitle: Platform Engineer\n",
                encoding="utf-8",
            )
            with redirect_stdout(StringIO()):
                main(["init", str(project_path), "--name", "My Career"])

            with redirect_stdout(StringIO()) as output:
                result = main(["jobs", "import", str(project_path), str(source_path)])

            self.assertEqual(result, 0)
            self.assertIn("Saved job document", output.getvalue())
            self.assertTrue((project_path / "jobs" / "platform-role.yml").is_file())

    def test_match_prints_yaml_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            with redirect_stdout(StringIO()):
                main(
                    [
                        "init",
                        str(project_path),
                        "--name",
                        "My Career",
                        "--language",
                        "en",
                    ]
                )
            (project_path / "career.yml").write_text(
                "schema_version: 2\nprofile: {name: Example, email: example@example.invalid}\n"
                "experience: []\neducation: []\nskills: []\n"
                "evidence: [{id: python-work, statement: Delivered Python services., tags: [python], verified: true}]\n"
                "answers: []\nstories: []\n",
                encoding="utf-8",
            )
            (project_path / "jobs" / "platform-role.yml").write_text(
                "schema_version: 1\nid: platform-role\ntitle: Platform Engineer\n"
                "requirements: [{id: python, statement: Python experience, priority: required}]\n"
                "source: {format: manual, content: Python experience}\n",
                encoding="utf-8",
            )

            with redirect_stdout(StringIO()) as output:
                result = main(["match", str(project_path), "platform-role"])

            self.assertEqual(result, 0)
            self.assertIn("job_id: platform-role", output.getvalue())
            self.assertIn("classification: STRONG_MATCH", output.getvalue())
