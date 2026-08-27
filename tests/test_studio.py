from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from urllib.request import urlopen

from seriemacv.applications import ApplicationDocument, create_application
from seriemacv.project import create_project
from seriemacv.studio import create_studio_server


class StudioTests(unittest.TestCase):
    def test_local_studio_serves_read_only_job_and_match_views(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
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
            create_application(project_path, ApplicationDocument(id="platform-application", job_id="platform-role"))
            server = create_studio_server(project_path)
            try:
                import threading

                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                base_url = f"http://127.0.0.1:{server.server_port}"
                with urlopen(f"{base_url}/api/jobs") as response:
                    jobs = json.loads(response.read())
                with urlopen(f"{base_url}/api/match/platform-role") as response:
                    report = json.loads(response.read())
                with urlopen(f"{base_url}/") as response:
                    page = response.read().decode("utf-8")
                with urlopen(f"{base_url}/api/applications") as response:
                    applications = json.loads(response.read())
                with urlopen(f"{base_url}/api/application/platform-application") as response:
                    application = json.loads(response.read())
            finally:
                server.shutdown()
                server.server_close()

            self.assertEqual(jobs, [{"id": "platform-role", "title": "Platform Engineer", "company": ""}])
            self.assertEqual(report["requirements"][0]["classification"], "STRONG_MATCH")
            self.assertEqual(applications[0]["id"], "platform-application")
            self.assertEqual(application["status"], "saved")
            self.assertIn("seriemaCV Studio", page)
