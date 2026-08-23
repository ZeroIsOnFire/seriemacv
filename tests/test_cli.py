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
                result = main([
                    "init", str(project_path), "--name", "My Career",
                    "--language", "en", "--style", "classic",
                ])

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

    def test_template_show_prints_only_the_career_example(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "my-career"
            with redirect_stdout(StringIO()):
                main(["init", str(project_path), "--name", "My Career"])

            with redirect_stdout(StringIO()) as output:
                result = main(["template", "show", str(project_path), "career"])
            self.assertEqual(result, 0)
            self.assertIn("Avery Example", output.getvalue())

            with redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit):
                    main(["template", "show", str(project_path), "job"])

    def test_jobs_are_hidden_and_resume_styles_are_discoverable(self) -> None:
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                main(["jobs", "list", "."])

        with redirect_stdout(StringIO()) as output:
            result = main(["resume", "styles"])

        self.assertEqual(result, 0)
        self.assertIn("clean\tClean\tsingle-column\tATS-safe", output.getvalue())
        self.assertIn("sidebar\tSidebar\ttwo-column\texperimental", output.getvalue())
