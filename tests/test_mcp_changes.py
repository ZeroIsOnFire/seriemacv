from __future__ import annotations

import tempfile
import threading
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from seriemacv.mcp_changes import ChangeDiff, ChangeManager


class McpChangeTests(unittest.TestCase):
    def test_failed_change_does_not_restore_through_swapped_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            project = root / "project"
            nested = project / "nested"
            nested.mkdir(parents=True)
            target = nested / "record.yml"
            target.write_text("before\n", encoding="utf-8")
            outside = root / "outside"
            outside.mkdir()
            (outside / "record.yml").write_text("outside\n", encoding="utf-8")
            manager = ChangeManager(project)

            def swap_then_fail() -> None:
                target.unlink()
                nested.rmdir()
                nested.symlink_to(outside, target_is_directory=True)
                raise RuntimeError("failed")

            prepared = manager.prepare(
                operation="test",
                summary="Rollback safely",
                diff=[],
                affected_paths=[target],
                action=swap_then_fail,
            )
            with self.assertRaisesRegex(RuntimeError, "failed"):
                manager.confirm(prepared.token)

            self.assertEqual(target.read_text(encoding="utf-8"), "before\n")
            self.assertEqual(
                (outside / "record.yml").read_text(encoding="utf-8"), "outside\n"
            )

    def test_rejects_symlink_swap_even_when_target_hash_is_identical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            project = root / "project"
            project.mkdir()
            target = project / "record.yml"
            outside = root / "outside.yml"
            target.write_text("same\n", encoding="utf-8")
            outside.write_text("same\n", encoding="utf-8")
            manager = ChangeManager(project)
            prepared = manager.prepare(
                operation="test",
                summary="Replace local record",
                diff=[],
                affected_paths=[target],
                action=lambda: target.write_text("changed\n", encoding="utf-8"),
            )
            target.unlink()
            try:
                target.symlink_to(outside)
            except OSError as error:
                self.skipTest(f"symlinks unavailable: {error}")

            with self.assertRaisesRegex(ValueError, "symlink|outside"):
                manager.confirm(prepared.token)

            self.assertEqual(outside.read_text(encoding="utf-8"), "same\n")

    def test_rejects_empty_directory_and_outside_affected_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "project"
            root.mkdir()
            manager = ChangeManager(root)

            for paths in ([], [root], [root.parent / "outside.yml"]):
                with self.subTest(paths=paths):
                    with self.assertRaisesRegex(ValueError, "affected file"):
                        manager.prepare(
                            operation="test",
                            summary="Unsafe",
                            diff=[],
                            affected_paths=paths,
                            action=lambda: None,
                        )

    def test_pending_change_count_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manager = ChangeManager(root, max_pending=2)
            prepared = [
                manager.prepare(
                    operation="test",
                    summary=f"Change {index}",
                    diff=[],
                    affected_paths=[root / f"{index}.yml"],
                    action=lambda: None,
                )
                for index in range(2)
            ]

            with self.assertRaisesRegex(ValueError, "too many pending"):
                manager.prepare(
                    operation="test",
                    summary="Overflow",
                    diff=[],
                    affected_paths=[root / "overflow.yml"],
                    action=lambda: None,
                )
            manager.confirm(prepared[0].token)
            manager.prepare(
                operation="test",
                summary="After confirmation",
                diff=[],
                affected_paths=[root / "allowed.yml"],
                action=lambda: None,
            )

    def test_concurrent_confirmations_cannot_bypass_stale_hash_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "record.yml"
            target.write_text("before\n", encoding="utf-8")
            manager = ChangeManager(root)
            first_started = threading.Event()
            release_first = threading.Event()
            second_started = threading.Event()
            results: list[str] = []
            errors: list[Exception] = []

            def first_action() -> None:
                first_started.set()
                if not release_first.wait(timeout=2):
                    raise TimeoutError("test did not release first action")
                target.write_text("first\n", encoding="utf-8")

            def second_action() -> None:
                second_started.set()
                target.write_text("second\n", encoding="utf-8")

            first = manager.prepare(
                operation="test",
                summary="First",
                diff=[],
                affected_paths=[target],
                action=first_action,
            )
            second = manager.prepare(
                operation="test",
                summary="Second",
                diff=[],
                affected_paths=[target],
                action=second_action,
            )

            def confirm(token: str) -> None:
                try:
                    manager.confirm(token)
                    results.append(token)
                except Exception as error:
                    errors.append(error)

            first_thread = threading.Thread(target=confirm, args=(first.token,))
            second_thread = threading.Thread(target=confirm, args=(second.token,))
            first_thread.start()
            self.assertTrue(first_started.wait(timeout=1))
            second_thread.start()
            second_ran_before_release = second_started.wait(timeout=0.2)
            release_first.set()
            first_thread.join(timeout=2)
            second_thread.join(timeout=2)

            self.assertFalse(second_ran_before_release)
            self.assertEqual(results, [first.token])
            self.assertEqual(len(errors), 1)
            self.assertIn("changed", str(errors[0]))
            self.assertEqual(target.read_text(encoding="utf-8"), "first\n")

    def test_token_cannot_be_used_by_another_project_manager(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first = root / "first"
            second = root / "second"
            first.mkdir()
            second.mkdir()
            target = first / "record.yml"
            manager = ChangeManager(first)
            other_project = ChangeManager(second)
            prepared = manager.prepare(
                operation="test",
                summary="Project-bound",
                diff=[],
                affected_paths=[target],
                action=lambda: target.write_text("confirmed\n", encoding="utf-8"),
            )

            with self.assertRaisesRegex(ValueError, "unknown"):
                other_project.confirm(prepared.token)
            self.assertFalse(target.exists())
            manager.confirm(prepared.token)
            self.assertEqual(target.read_text(encoding="utf-8"), "confirmed\n")

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
