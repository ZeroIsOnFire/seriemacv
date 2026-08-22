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
                result = main(["init", str(project_path), "--name", "My Career"])

            self.assertEqual(result, 0)
            self.assertIn("Created seriemaCV project", stdout.getvalue())

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
