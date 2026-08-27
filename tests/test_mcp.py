from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from seriemacv.mcp import TOOLS, _handle
from seriemacv.project import create_project


class McpTests(unittest.TestCase):
    def test_initialization_and_tool_listing_are_read_only(self) -> None:
        initialized = _handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        listed = _handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

        self.assertEqual(initialized["result"]["capabilities"], {"tools": {}})
        self.assertEqual(listed["result"]["tools"], TOOLS)
        self.assertEqual(
            [item["name"] for item in TOOLS],
            ["search_career_evidence", "list_jobs", "get_match_report", "propose_resume_tailoring"],
        )

    def test_unknown_method_returns_json_rpc_error(self) -> None:
        response = _handle({"jsonrpc": "2.0", "id": 3, "method": "unknown"})

        self.assertEqual(response["error"]["code"], -32601)

    def test_list_jobs_calls_the_shared_local_use_case(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")

            response = _handle({
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "list_jobs", "arguments": {"project_path": str(project_path)}},
            })

            self.assertEqual(response["result"]["content"][0]["text"], "[]\n")
