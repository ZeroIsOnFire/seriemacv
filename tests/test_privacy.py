from __future__ import annotations

import json
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

from seriemacv.cli import main
from seriemacv.mcp import _handle
from seriemacv.privacy import REDACTED, TELEMETRY_ENABLED, redact_sensitive_text
from seriemacv.project import create_project
from seriemacv.studio import create_studio_server


class PrivacyTests(unittest.TestCase):
    def test_telemetry_is_disabled_by_default(self) -> None:
        self.assertFalse(TELEMETRY_ENABLED)

    def test_redacts_credentials_personal_data_and_sensitive_field_values(self) -> None:
        value = (
            "Authorization: Bearer secret-token; api_key=abc123; password: hunter2; "
            "cookie=session-value; email: person@example.invalid; phone: +55 11 95555-0100; "
            "salary=5000"
        )

        redacted = redact_sensitive_text(value)

        for secret in (
            "secret-token",
            "abc123",
            "hunter2",
            "session-value",
            "person@example.invalid",
            "+55 11 95555-0100",
            "5000",
        ):
            self.assertNotIn(secret, redacted)
        self.assertIn("Authorization: <redacted>", redacted)
        self.assertIn("email: <redacted>", redacted)
        self.assertIn("salary=<redacted>", redacted)

    def test_cli_error_redacts_reflected_personal_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            with patch(
                "seriemacv.cli.set_profile",
                side_effect=ValueError("email: person@example.invalid token=abc123"),
            ):
                from contextlib import redirect_stderr
                from io import StringIO

                with redirect_stderr(StringIO()) as output:
                    result = main(
                        [
                            "career",
                            "set-profile",
                            str(project_path),
                            "--name",
                            "Example",
                        ]
                    )

        self.assertEqual(result, 1)
        self.assertNotIn("person@example.invalid", output.getvalue())
        self.assertNotIn("abc123", output.getvalue())
        self.assertIn(REDACTED, output.getvalue())

    def test_studio_error_redacts_response_body(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            with patch(
                "seriemacv.studio.load_jobs",
                side_effect=ValueError("phone: +55 11 95555-0100"),
            ):
                server = create_studio_server(project_path)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    with self.assertRaises(HTTPError) as caught:
                        urlopen(f"http://127.0.0.1:{server.server_port}/api/jobs")
                    body = json.loads(caught.exception.read())
                finally:
                    server.shutdown()
                    server.server_close()

        self.assertNotIn("+55 11 95555-0100", body["error"])
        self.assertEqual(body["error"], "phone: <redacted>")

    def test_mcp_error_redacts_message(self) -> None:
        with patch(
            "seriemacv.mcp._call",
            side_effect=ValueError("email: person@example.invalid"),
        ):
            response = _handle(
                {
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "tools/call",
                    "params": {
                        "name": "list_jobs",
                        "arguments": {"project_path": "ignored"},
                    },
                }
            )

        self.assertEqual(response["id"], 7)
        self.assertNotIn("person@example.invalid", response["error"]["message"])
        self.assertIn(REDACTED, response["error"]["message"])

    def test_cli_read_output_keeps_data_explicitly_requested_by_user(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            (project_path / "career.yml").write_text(
                "schema_version: 2\nprofile: {name: Example, email: person@example.invalid}\n"
                "experience: []\neducation: []\nskills: []\nevidence: []\nanswers: []\nstories: []\n",
                encoding="utf-8",
            )
            from contextlib import redirect_stdout
            from io import StringIO

            with redirect_stdout(StringIO()) as output:
                result = main(["career", "list", str(project_path), "profile"])

        self.assertEqual(result, 0)
        self.assertIn("person@example.invalid", output.getvalue())

    def test_diagnostic_bundle_excludes_personal_project_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            output_path = Path(temporary_directory) / "diagnostics.zip"
            create_project(project_path, project_name="Private career")
            (project_path / "career.yml").write_text(
                "schema_version: 2\nprofile: {name: Private Person, email: person@example.invalid}\n",
                encoding="utf-8",
            )
            result = main(
                [
                    "diagnostics",
                    "bundle",
                    str(project_path),
                    "--output",
                    str(output_path),
                ]
            )
            with zipfile.ZipFile(output_path) as archive:
                self.assertEqual(archive.namelist(), ["diagnostics.json"])
                bundle = archive.read("diagnostics.json").decode("utf-8")

        self.assertEqual(result, 0)
        self.assertNotIn("Private Person", bundle)
        self.assertNotIn("person@example.invalid", bundle)
