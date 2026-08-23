from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from seriemacv.importer import ImportError, ImportProposal, NuExtractSettings, SourceExcerpt, apply_proposal, save_proposal
from seriemacv.project import create_project


class ImportProposalTests(unittest.TestCase):
    def test_apply_is_explicit_and_rejects_existing_career(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory) / "career"
            create_project(project, project_name="Career")
            proposal = ImportProposal.model_validate({
                "schema_version": 1, "id": "import-test", "created_at": "2026-01-01T00:00:00+00:00", "source_path": "resume.md", "source_sha256": "0" * 64, "language": "en", "runtime": {"endpoint": "http://127.0.0.1:8080", "model": "nuextract"}, "confidence": 1.0,
                "excerpts": [{"text": "Example Engineer"}],
                "career": {"schema_version": 2, "profile": {"name": "Example", "email": "example@example.invalid"}, "experience": [], "education": [], "skills": [], "evidence": [], "answers": [], "stories": []},
                "locale": {"schema_version": 1, "locale": "en", "catalog": {"labels": {"summary": "Summary", "experience": "Experience", "education": "Education", "skills": "Skills", "languages": "Languages", "current": "Present", "other": "Other", "level.beginner": "Beginner", "level.intermediate": "Intermediate", "level.advanced": "Advanced", "level.expert": "Expert"}, "months": ["Jan"] * 12, "date_format": "{month} {year}"}, "profile": {"title": "Engineer"}, "experience": {}, "education": {}, "skills": {}},
            })
            save_proposal(project, proposal)
            self.assertIn('name: ""', (project / "career.yml").read_text(encoding="utf-8"))
            apply_proposal(project, "import-test")
            self.assertIn("name: Example", (project / "career.yml").read_text(encoding="utf-8"))
            with self.assertRaises(ImportError):
                apply_proposal(project, "import-test")
