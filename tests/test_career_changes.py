from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import anyio
from mcp import Client
from pydantic import ValidationError
from ruamel.yaml import YAML

from seriemacv.career import load_career, load_localized_career
from seriemacv.career_changes import (
    CareerChange,
    apply_career_change,
    plan_career_change,
)
from seriemacv.mcp import create_mcp_server
from seriemacv.project import create_project


class CareerChangeTests(unittest.TestCase):
    def test_noop_update_does_not_create_a_write_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _example_project(temporary_directory)
            change = CareerChange.model_validate(
                {
                    "operations": [
                        {
                            "kind": "profile_update",
                            "values": {"phone": "+55 11 5555-0100"},
                        },
                        {
                            "kind": "locale_update",
                            "locale": "en",
                            "section": "summary",
                            "values": {
                                "value": "Build reliable software with collaborative teams."
                            },
                        },
                    ]
                }
            )

            plan = plan_career_change(project_path, change)

            self.assertEqual(plan.changes, {})
            self.assertEqual(plan.diff, [])

    def test_typed_crud_preserves_comments_and_waits_for_apply(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _example_project(temporary_directory)
            career_path = project_path / "career.yml"
            original = "# keep this note\n" + career_path.read_text(encoding="utf-8")
            career_path.write_text(original, encoding="utf-8")
            change = CareerChange.model_validate(
                {
                    "operations": [
                        {
                            "kind": "profile_update",
                            "values": {"portfolio": "https://example.invalid"},
                        },
                        {
                            "kind": "record_create",
                            "section": "skills",
                            "record": {
                                "id": "distributed-systems",
                                "tags": ["architecture"],
                            },
                            "locales": {
                                "pt-BR": {"name": "Sistemas distribuídos"},
                                "en": {"name": "Distributed systems"},
                            },
                        },
                        {
                            "kind": "record_update",
                            "section": "skills",
                            "id": "distributed-systems",
                            "values": {"core": True},
                            "locales": {
                                "en": {"category": "Architecture"},
                            },
                        },
                        {
                            "kind": "locale_update",
                            "locale": "en",
                            "section": "summary",
                            "values": {"value": "Builds dependable systems."},
                        },
                    ]
                }
            )

            plan = plan_career_change(project_path, change)

            self.assertEqual(career_path.read_text(encoding="utf-8"), original)
            self.assertEqual(len(plan.changes), 3)
            apply_career_change(plan)
            self.assertIn("# keep this note", career_path.read_text(encoding="utf-8"))
            facts = load_career(career_path)
            skill = next(
                item for item in facts.skills if item.id == "distributed-systems"
            )
            self.assertTrue(skill.core)
            localized = load_localized_career(project_path, "en")
            self.assertEqual(localized.summary, "Builds dependable systems.")
            self.assertEqual(
                next(
                    item.name
                    for item in localized.skills
                    if item.id == "distributed-systems"
                ),
                "Distributed systems",
            )

    def test_deletion_cascade_is_explicit_and_keeps_documents_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _example_project(temporary_directory)
            variant = project_path / "resume" / "variants" / "example"
            (variant / "locales").mkdir(parents=True)
            shutil.copyfile(
                project_path / "variant.yml.example", variant / "variant.yml"
            )
            shutil.copyfile(
                project_path / "variant-locale.yml.example",
                variant / "locales" / "en.yml",
            )
            (project_path / "applications" / "example.yml").write_text(
                "schema_version: 1\n"
                "id: example\n"
                "job_id: example-role\n"
                "answers:\n"
                "  - field_id: authorization\n"
                "    answer: Yes\n"
                "    saved_answer_id: work-authorization\n",
                encoding="utf-8",
            )
            change = CareerChange.model_validate(
                {
                    "operations": [
                        {
                            "kind": "record_delete",
                            "section": "experience",
                            "id": "example-platform",
                        },
                        {
                            "kind": "record_delete",
                            "section": "answers",
                            "id": "work-authorization",
                        },
                    ]
                }
            )

            plan = plan_career_change(project_path, change)
            diff_paths = {item.path for item in plan.diff}

            self.assertIn("career.yml::evidence.example-service", diff_paths)
            self.assertIn(
                "career.yml::stories.example-delivery.evidence_ids", diff_paths
            )
            self.assertTrue(any("selection.experience" in item for item in diff_paths))
            self.assertTrue(any("saved_answer_id" in item for item in diff_paths))
            apply_career_change(plan)
            facts = load_career(project_path / "career.yml")
            self.assertEqual(facts.experience, [])
            self.assertEqual(facts.evidence, [])
            self.assertEqual(facts.answers, [])
            self.assertEqual(facts.stories[0].evidence_ids, [])
            locale = YAML(typ="safe").load(
                (variant / "locales" / "en.yml").read_text(encoding="utf-8")
            )
            self.assertEqual(locale["evidence_ids"], [])
            self.assertNotIn("summary", locale)
            self.assertNotIn("example-platform", locale.get("experience", {}))
            application = YAML(typ="safe").load(
                (project_path / "applications" / "example.yml").read_text(
                    encoding="utf-8"
                )
            )
            self.assertIsNone(application["answers"][0]["saved_answer_id"])

    def test_rejects_missing_locale_and_id_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _example_project(temporary_directory)
            incomplete = CareerChange.model_validate(
                {
                    "operations": [
                        {
                            "kind": "record_create",
                            "section": "skills",
                            "record": {"id": "architecture"},
                            "locales": {"en": {"name": "Architecture"}},
                        }
                    ]
                }
            )
            with self.assertRaisesRegex(ValueError, "every locale"):
                plan_career_change(project_path, incomplete)
            with self.assertRaisesRegex(ValidationError, "immutable"):
                CareerChange.model_validate(
                    {
                        "operations": [
                            {
                                "kind": "record_update",
                                "section": "skills",
                                "id": "python",
                                "values": {"id": "python-3"},
                            }
                        ]
                    }
                )

    def test_mcp_prepares_without_writing_then_confirms_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = _example_project(temporary_directory)
            career_path = project_path / "career.yml"
            original = career_path.read_text(encoding="utf-8")

            async def exercise() -> None:
                async with Client(create_mcp_server(project_path)) as client:
                    prepared = await client.call_tool(
                        "prepare_career_change",
                        {
                            "change": {
                                "operations": [
                                    {
                                        "kind": "profile_update",
                                        "values": {"phone": "+55 11 5555-0199"},
                                    }
                                ]
                            }
                        },
                    )
                    self.assertFalse(prepared.is_error)
                    self.assertEqual(career_path.read_text(encoding="utf-8"), original)
                    token = prepared.structured_content["data"]["token"]  # type: ignore[index]
                    confirmed = await client.call_tool(
                        "confirm_change", {"token": token}
                    )
                    self.assertFalse(confirmed.is_error)
                    replay = await client.call_tool("confirm_change", {"token": token})
                    self.assertTrue(replay.is_error)

            anyio.run(exercise)
            self.assertEqual(load_career(career_path).profile.phone, "+55 11 5555-0199")


def _example_project(temporary_directory: str) -> Path:
    project_path = Path(temporary_directory) / "career"
    create_project(project_path, project_name="Career")
    shutil.copyfile(project_path / "career.yml.example", project_path / "career.yml")
    for locale in ("pt-BR", "en"):
        shutil.copyfile(
            project_path / "career.locales" / f"{locale}.yml.example",
            project_path / "career.locales" / f"{locale}.yml",
        )
    return project_path
