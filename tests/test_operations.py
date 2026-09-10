from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from seriemacv.cli import main
from seriemacv.mcp import main as mcp_main
from seriemacv.operations import (
    METRICS_PATH,
    OperationRecorder,
    operation_summary,
    read_operation_records,
    record_browser_call,
    record_cache,
)
from seriemacv.project import create_project, load_project_configuration


class OperationMetricsTests(unittest.TestCase):
    def test_records_only_bounded_metadata_and_recovers_from_corrupt_lines(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Private Person")
            metrics_path = project_path / METRICS_PATH
            metrics_path.parent.mkdir(parents=True, exist_ok=True)
            metrics_path.write_text(
                'not-json\n{"schema_version":1,"operation":"Private Person"}\n',
                encoding="utf-8",
            )

            for index in range(3):
                with OperationRecorder(
                    project_path,
                    "cli",
                    "jobs.list",
                    input_bytes=index,
                    max_records=2,
                ) as recorder:
                    recorder.add_output(index + 1)
                    record_cache(index == 2)
                    for kind in ("navigation", "inspection", "fill", "upload"):
                        record_browser_call(kind)

            records = read_operation_records(project_path)
            raw = metrics_path.read_text(encoding="utf-8")

        self.assertEqual(len(records), 2)
        self.assertEqual(records[-1]["cache"], {"hits": 1, "misses": 0})
        self.assertEqual(records[-1]["input_bytes"], 2)
        self.assertEqual(records[-1]["output_bytes"], 3)
        self.assertEqual(
            records[-1]["browser"],
            {"navigation": 1, "inspection": 1, "fill": 1, "upload": 1},
        )
        self.assertGreaterEqual(records[-1]["duration_ms"], 0)
        self.assertEqual(records[-1]["status"], "success")
        self.assertNotIn("Private Person", raw)
        self.assertNotIn("not-json", raw)

    def test_cli_warns_without_changing_output_and_summary_does_not_record_itself(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            config_path = project_path / "seriemacv.yml"
            config_path.write_text(
                config_path.read_text(encoding="utf-8").replace(
                    "output_warning_bytes: 65536", "output_warning_bytes: 1"
                ),
                encoding="utf-8",
            )
            output, errors = StringIO(), StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                result = main(["validate", str(project_path)])
            records_before = read_operation_records(project_path)
            summary_output = StringIO()
            with redirect_stdout(summary_output):
                summary_result = main(
                    ["diagnostics", "operations", str(project_path), "--limit", "1"]
                )
            records_after = read_operation_records(project_path)

        self.assertEqual(result, 0)
        self.assertIn("Valid seriemaCV project", output.getvalue())
        self.assertIn("exceeded 1 bytes", errors.getvalue())
        self.assertEqual(records_before, records_after)
        self.assertEqual(records_before[0]["operation"], "validate")
        self.assertIn("largest_results:", summary_output.getvalue())
        self.assertEqual(summary_result, 0)

    def test_mcp_records_serialized_call_and_preserves_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            config_path = project_path / "seriemacv.yml"
            config_path.write_text(
                config_path.read_text(encoding="utf-8").replace(
                    "output_warning_bytes: 65536", "output_warning_bytes: 1"
                ),
                encoding="utf-8",
            )
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "list_jobs",
                    "arguments": {"project_path": str(project_path)},
                },
            }
            output, errors = StringIO(), StringIO()
            with (
                patch.object(sys, "stdin", StringIO(json.dumps(request) + "\n")),
                redirect_stdout(output),
                redirect_stderr(errors),
            ):
                result = mcp_main()
            response = json.loads(output.getvalue())
            records = read_operation_records(project_path)

        self.assertEqual(result, 0)
        self.assertEqual(response["result"]["content"][0]["text"], "[]\n")
        self.assertIn("exceeded 1 bytes", errors.getvalue())
        self.assertEqual(records[0]["interface"], "mcp")
        self.assertEqual(records[0]["operation"], "list_jobs")

    def test_metrics_write_failure_does_not_fail_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            errors = StringIO()
            with (
                patch("seriemacv.operations._write_records", side_effect=OSError),
                redirect_stderr(errors),
            ):
                with OperationRecorder(project_path, "cli", "validate"):
                    pass

        self.assertIn("metrics could not be written", errors.getvalue())

    def test_exception_is_recorded_as_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")

            with self.assertRaisesRegex(ValueError, "failed"):
                with OperationRecorder(project_path, "cli", "jobs.import"):
                    raise ValueError("failed")

            records = read_operation_records(project_path)

        self.assertEqual(records[0]["status"], "error")

    def test_configuration_defaults_are_backward_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            config_path = project_path / "seriemacv.yml"
            config_path.write_text(
                "schema_version: 2\nproject_name: Career\n", encoding="utf-8"
            )

            configuration = load_project_configuration(project_path)

        self.assertEqual(configuration.operation_metrics.output_warning_bytes, 65_536)
        self.assertEqual(configuration.operation_metrics.max_records, 1_000)

    def test_summary_contains_only_safe_aggregates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "career"
            create_project(project_path, project_name="Career")
            with OperationRecorder(
                project_path, "cli", "applications.context"
            ) as recorder:
                recorder.add_output(12)
                recorder._started -= 2
                record_browser_call("inspection")
                record_browser_call("fill")
            with OperationRecorder(project_path, "cli", "applications.prepare"):
                pass
            summary = operation_summary(project_path, limit=1)

        self.assertEqual(summary["operations"], 2)
        self.assertEqual(summary["output_bytes"], 12)
        self.assertEqual(summary["status"], {"success": 2, "error": 0})
        self.assertGreaterEqual(summary["duration_ms"], 2_000)
        self.assertEqual(
            summary["largest_results"][0]["operation"], "applications.context"
        )
        self.assertEqual(
            summary["slowest_operations"][0]["operation"], "applications.context"
        )
        self.assertEqual(summary["most_browser_calls"][0]["browser_calls"], 2)


if __name__ == "__main__":
    unittest.main()
