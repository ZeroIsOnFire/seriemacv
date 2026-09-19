from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from seriemacv.mcp_changes import ChangeDiff, ChangeManager


class McpChangeTests(unittest.TestCase):
    def test_change_is_previewed_then_confirmed_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "jobs" / "role.yml"
            manager = ChangeManager(root)
            prepared = manager.prepare(
                operation="job.save",
                summary="Save role",
                diff=[ChangeDiff(path="jobs/role.yml", after={"id": "role"})],
                affected_paths=[target],
                action=lambda: _write(target, b"id: role\n"),
            )

            self.assertFalse(target.exists())
            confirmed = manager.confirm(prepared.token)

            self.assertEqual(target.read_text(encoding="utf-8"), "id: role\n")
            self.assertEqual(confirmed.status, "confirmed")
            with self.assertRaisesRegex(ValueError, "already used"):
                manager.confirm(prepared.token)

    def test_expired_tampered_and_stale_tokens_do_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "record.yml"
            target.write_text("before\n", encoding="utf-8")
            current = datetime(2026, 1, 1, tzinfo=UTC)
            manager = ChangeManager(root, ttl_seconds=10, now=lambda: current)
            expired = manager.prepare(
                operation="test",
                summary="Expired",
                diff=[],
                affected_paths=[target],
                action=lambda: target.write_text("after\n", encoding="utf-8"),
            )
            current += timedelta(seconds=10)

            with self.assertRaisesRegex(ValueError, "expired"):
                manager.confirm(expired.token)
            with self.assertRaisesRegex(ValueError, "unknown"):
                manager.confirm("tampered")

            current += timedelta(seconds=1)
            stale = manager.prepare(
                operation="test",
                summary="Stale",
                diff=[],
                affected_paths=[target],
                action=lambda: target.write_text("after\n", encoding="utf-8"),
            )
            target.write_text("external\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed"):
                manager.confirm(stale.token)
            self.assertEqual(target.read_text(encoding="utf-8"), "external\n")

    def test_failed_multifile_change_rolls_back_every_file_and_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            original = root / "original.yml"
            created = root / "nested" / "created.yml"
            original.write_text("before\n", encoding="utf-8")
            manager = ChangeManager(root)

            def fail_after_writes() -> None:
                original.write_text("changed\n", encoding="utf-8")
                created.parent.mkdir()
                created.write_text("created\n", encoding="utf-8")
                raise RuntimeError("failed")

            prepared = manager.prepare(
                operation="test",
                summary="Rollback",
                diff=[],
                affected_paths=[original, created],
                action=fail_after_writes,
            )

            with self.assertRaisesRegex(RuntimeError, "failed"):
                manager.confirm(prepared.token)

            self.assertEqual(original.read_text(encoding="utf-8"), "before\n")
            self.assertFalse(created.exists())
            self.assertFalse(created.parent.exists())


def _write(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path
