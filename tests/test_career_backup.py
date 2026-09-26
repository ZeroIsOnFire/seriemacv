from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from ruamel.yaml import YAML

from seriemacv.career_backup import create_career_backup
from seriemacv.project import create_project


class CareerBackupTests(unittest.TestCase):
    def test_copies_canonical_sources_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            expected = {
                path.relative_to(project_path).as_posix(): path.read_bytes()
                for path in [
                    project_path / "career.yml",
                    *sorted((project_path / "career.locales").glob("*.yml")),
                ]
            }

            backup = create_career_backup(
                project_path,
                "analyze",
                now=lambda: datetime(2026, 9, 25, 12, 30, tzinfo=UTC),
            )

            self.assertEqual(backup.name, "20260925T123000Z-analyze")
            for relative, content in expected.items():
                self.assertEqual((backup / relative).read_bytes(), content)
            manifest = YAML(typ="safe").load(
                (backup / "manifest.yml").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["reason"], "analyze")
            self.assertEqual(
                [item["path"] for item in manifest["files"]], list(expected)
            )
            self.assertTrue(
                all(len(item["sha256"]) == 64 for item in manifest["files"])
            )

    def test_preserves_invalid_yaml_and_uses_a_unique_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            career_path = project_path / "career.yml"
            career_path.write_text("profile: [\n", encoding="utf-8")

            def frozen_time() -> datetime:
                return datetime(2026, 9, 25, tzinfo=UTC)

            first = create_career_backup(project_path, "update", now=frozen_time)
            second = create_career_backup(project_path, "update", now=frozen_time)

            self.assertEqual(
                (first / "career.yml").read_text(encoding="utf-8"), "profile: [\n"
            )
            self.assertEqual(second.name, "20260925T000000Z-update-2")

    def test_rejects_an_invalid_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")

            with self.assertRaisesRegex(ValueError, "reason"):
                create_career_backup(project_path, "../outside")  # type: ignore[arg-type]
