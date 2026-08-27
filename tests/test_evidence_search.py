import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from seriemacv.cli import main
from seriemacv.evidence_search import search_verified_evidence
from seriemacv.project import create_project


class EvidenceSearchTests(unittest.TestCase):
    def test_searches_verified_evidence_by_text_tags_and_experience(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)

            results = search_verified_evidence(project_path, query="reliability")
            self.assertEqual([item.id for item in results], ["reliable-service"])

            results = search_verified_evidence(project_path, tags=["PYTHON"])
            self.assertEqual(
                [item.id for item in results], ["alpha-python", "beta-python", "reliable-service"]
            )

            results = search_verified_evidence(
                project_path, tags=["python"], experience_id="platform"
            )
            self.assertEqual([item.id for item in results], ["reliable-service"])

    def test_reads_manual_yaml_edits_directly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            career_path = project_path / "career.yml"

            self.assertEqual(
                [item.id for item in search_verified_evidence(project_path, query="reliability")],
                ["reliable-service"],
            )
            career_path.write_text(
                career_path.read_text(encoding="utf-8").replace(
                    "reliability", "incident"
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                [item.id for item in search_verified_evidence(project_path, query="incident")],
                ["reliable-service"],
            )
            self.assertEqual(search_verified_evidence(project_path, query="reliability"), [])

    def test_excludes_unverified_evidence_and_orders_ties_by_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)

            results = search_verified_evidence(project_path, tags=["python"])

            self.assertEqual(
                [item.id for item in results], ["alpha-python", "beta-python", "reliable-service"]
            )
            self.assertNotIn("pending-python", [item.id for item in results])

            results = search_verified_evidence(project_path, query="shared")
            self.assertEqual([item.id for item in results], ["alpha-python", "beta-python"])

    def test_rejects_missing_criteria_and_invalid_career(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            with self.assertRaisesRegex(ValueError, "Provide a text query"):
                search_verified_evidence(project_path)
            self.assertEqual(search_verified_evidence(project_path, query='"'), [])

            (project_path / "career.yml").write_text("profile: [\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid YAML"):
                search_verified_evidence(project_path, query="python")

    def test_cli_prints_yaml_and_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _create_project(temporary_directory)
            with redirect_stdout(StringIO()) as output:
                result = main([
                    "career", "search-evidence", str(project_path), "python", "--tag", "reliability",
                ])
            self.assertEqual(result, 0)
            self.assertIn("id: reliable-service", output.getvalue())

            with redirect_stderr(StringIO()) as error:
                result = main(["career", "search-evidence", str(project_path)])
            self.assertEqual(result, 1)
            self.assertIn("Provide a text query", error.getvalue())


def _create_project(temporary_directory: str) -> Path:
    project_path = Path(temporary_directory) / "my-career"
    create_project(project_path, project_name="My Career")
    (project_path / "career.yml").write_text(
        """schema_version: 2
profile:
  name: Seriema Example
  email: seriema@example.invalid
experience:
  - id: platform
    company: Example Systems
    start_date: 2024-01
skills: []
education: []
evidence:
  - id: reliable-service
    statement: Improved deployment reliability with Python checks.
    details: [Documented the reliability process.]
    tags: [python, reliability]
    experience_id: platform
    verified: true
  - id: alpha-python
    statement: Shared proof.
    tags: [python]
    verified: true
  - id: beta-python
    statement: Shared proof.
    tags: [python]
    verified: true
  - id: pending-python
    statement: Used Python for a pending claim.
    tags: [python]
    verified: false
answers: []
stories: []
""",
        encoding="utf-8",
    )
    return project_path
