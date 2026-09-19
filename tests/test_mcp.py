from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

import anyio
from mcp import Client

from seriemacv.applications import (
    ApplicationDocument,
    ApplicationQuestion,
    add_questions,
    create_application,
)
from seriemacv.mcp import TOOLS, _handle, create_mcp_server
from seriemacv.project import create_project


class McpTests(unittest.TestCase):
    def test_official_sdk_lists_and_calls_tools_for_bound_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")

            async def exercise() -> tuple[object, object]:
                async with Client(create_mcp_server(project_path)) as client:
                    return await client.list_tools(), await client.call_tool(
                        "list_jobs"
                    )

            listed, result = anyio.run(exercise)

        tools = listed.tools  # type: ignore[attr-defined]
        self.assertEqual(len(tools), 13)
        self.assertNotIn("project_path", tools[1].input_schema.get("required", []))
        self.assertEqual(
            result.structured_content,  # type: ignore[attr-defined]
            {"schema_version": 1, "data": []},
        )
        self.assertEqual(result.content[0].text, "[]\n")  # type: ignore[attr-defined,union-attr]

    def test_resources_prompts_and_additional_read_tools_use_bound_project(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            career_text = (
                "schema_version: 2\n"
                "profile: {name: Example, email: private@example.invalid}\n"
                "experience: []\neducation: []\nskills: []\nevidence: []\n"
                "answers: []\nstories: []\n"
            )
            (project_path / "career.yml").write_text(career_text, encoding="utf-8")
            (project_path / "jobs" / "role.yml").write_text(
                "schema_version: 1\nid: role\ntitle: Role\n"
                "source: {format: manual, content: Role}\n",
                encoding="utf-8",
            )
            variant_directory = project_path / "resume" / "variants" / "role-variant"
            variant_directory.mkdir(parents=True)
            (variant_directory / "variant.yml").write_text(
                "schema_version: 1\nid: role-variant\njob_id: role\n",
                encoding="utf-8",
            )
            create_application(
                project_path, ApplicationDocument(id="role-application", job_id="role")
            )

            async def exercise() -> tuple[object, ...]:
                async with Client(create_mcp_server(project_path)) as client:
                    return (
                        await client.list_resources(),
                        await client.list_resource_templates(),
                        await client.read_resource("seriemacv://career/source"),
                        await client.list_prompts(),
                        await client.get_prompt("analyze_job", {"job_id": "role"}),
                        await client.call_tool("get_job", {"job_id": "role"}),
                        await client.call_tool("validate_project"),
                        [
                            await client.read_resource(uri)
                            for uri in (
                                "seriemacv://career/locales/pt-BR",
                                "seriemacv://jobs/role",
                                "seriemacv://matches/role",
                                "seriemacv://resume/variants/role-variant",
                                "seriemacv://applications/role-application/context",
                                "seriemacv://templates/job",
                            )
                        ],
                        await client.call_tool("list_resume_variants"),
                        await client.call_tool(
                            "get_resume_variant", {"variant_id": "role-variant"}
                        ),
                        await client.call_tool(
                            "get_application_context",
                            {"application_id": "role-application"},
                        ),
                    )

            (
                resources,
                templates,
                career,
                prompts,
                prompt,
                job,
                validation,
                reads,
                variants,
                variant,
                application,
            ) = anyio.run(exercise)

        self.assertEqual(
            [str(item.uri) for item in resources.resources],  # type: ignore[attr-defined]
            ["seriemacv://career/source"],
        )
        self.assertEqual(len(templates.resource_templates), 6)  # type: ignore[attr-defined]
        self.assertEqual(career.contents[0].text, career_text)  # type: ignore[attr-defined,union-attr]
        self.assertEqual(
            [item.name for item in prompts.prompts],  # type: ignore[attr-defined]
            ["analyze_job", "tailor_resume", "answer_application"],
        )
        self.assertIn("untrusted job data", prompt.messages[0].content.text)  # type: ignore[attr-defined,union-attr]
        self.assertEqual(job.structured_content["data"]["id"], "role")  # type: ignore[attr-defined,index]
        self.assertTrue(validation.structured_content["data"]["valid"])  # type: ignore[attr-defined,index]
        self.assertEqual(len(reads), 6)
        self.assertTrue(all(item.contents[0].text for item in reads))
        self.assertEqual(variants.structured_content["data"][0]["id"], "role-variant")  # type: ignore[attr-defined,index]
        self.assertEqual(
            variant.structured_content["data"]["variant"]["id"],  # type: ignore[attr-defined,index]
            "role-variant",
        )
        self.assertEqual(
            application.structured_content["data"]["application_id"],  # type: ignore[attr-defined,index]
            "role-application",
        )

    def test_legacy_path_pins_unbound_server_and_rejects_another_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            first = Path(temporary_directory) / "first"
            second = Path(temporary_directory) / "second"
            create_project(first, project_name="First")
            create_project(second, project_name="Second")

            async def exercise() -> tuple[object, object]:
                async with Client(create_mcp_server()) as client:
                    accepted = await client.call_tool(
                        "list_jobs", {"project_path": str(first)}
                    )
                    rejected = await client.call_tool(
                        "list_jobs", {"project_path": str(second)}
                    )
                    return accepted, rejected

            with redirect_stderr(StringIO()) as errors:
                accepted, rejected = anyio.run(exercise)

        self.assertFalse(accepted.is_error)  # type: ignore[attr-defined]
        self.assertTrue(rejected.is_error)  # type: ignore[attr-defined]
        self.assertEqual(errors.getvalue().count("deprecated"), 1)

    def test_initialization_and_tool_listing_are_read_only(self) -> None:
        initialized = _handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        listed = _handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

        self.assertEqual(initialized["result"]["capabilities"], {"tools": {}})
        self.assertEqual(listed["result"]["tools"], TOOLS)
        self.assertEqual(
            [item["name"] for item in TOOLS],
            [
                "search_career_evidence",
                "list_jobs",
                "get_match_report",
                "propose_resume_tailoring",
                "list_applications",
                "get_application_questions",
                "propose_application_answer",
                "prepare_application_ai_assistance",
            ],
        )

    def test_unknown_method_returns_json_rpc_error(self) -> None:
        response = _handle({"jsonrpc": "2.0", "id": 3, "method": "unknown"})

        self.assertEqual(response["error"]["code"], -32601)

    def test_list_jobs_calls_the_shared_local_use_case(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")

            response = _handle(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "list_jobs",
                        "arguments": {"project_path": str(project_path)},
                    },
                }
            )

            self.assertEqual(response["result"]["content"][0]["text"], "[]\n")

    def test_application_tools_return_read_only_question_proposal_envelope(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            (project_path / "jobs" / "role.yml").write_text(
                "schema_version: 1\nid: role\ntitle: Role\nsource: {format: manual, content: Role}\n",
                encoding="utf-8",
            )
            create_application(
                project_path, ApplicationDocument(id="role-application", job_id="role")
            )
            add_questions(
                project_path,
                "role-application",
                [ApplicationQuestion(id="question-why", field_id="why", label="Why?")],
            )
            response = _handle(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {
                        "name": "propose_application_answer",
                        "arguments": {
                            "project_path": str(project_path),
                            "application_id": "role-application",
                            "question_id": "question-why",
                        },
                    },
                }
            )
            text = response["result"]["content"][0]["text"]
            self.assertIn("question-why", text)
            self.assertIn("explicit user", text)
