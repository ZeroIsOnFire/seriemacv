from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path


class QualityPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]

    def test_ci_runs_the_shared_quality_gate_with_restricted_permissions(self) -> None:
        workflow = (self.root / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("timeout-minutes: 20", workflow)
        self.assertIn("python -m pip check", workflow)
        self.assertIn("python scripts/check_quality.py", workflow)
        self.assertGreaterEqual(self._action_major(workflow, "actions/checkout"), 5)
        self.assertGreaterEqual(self._action_major(workflow, "actions/setup-python"), 6)

    def _action_major(self, workflow: str, action: str) -> int:
        match = re.search(rf"uses:\s*{re.escape(action)}@v(\d+)\b", workflow)
        self.assertIsNotNone(match, f"{action} must use a versioned major tag")
        return int(match.group(1))

    def test_mypy_baseline_expands_beyond_the_original_privacy_modules(self) -> None:
        configuration = tomllib.loads(
            (self.root / "pyproject.toml").read_text(encoding="utf-8")
        )
        typed_files = configuration["tool"]["mypy"]["files"]

        self.assertGreaterEqual(len(typed_files), 10)
        self.assertIn("src/seriemacv/browser.py", typed_files)
        self.assertIn("src/seriemacv/matching.py", typed_files)
        self.assertIn("src/seriemacv/project.py", typed_files)

        debt_modules = {
            module
            for override in configuration["tool"]["mypy"]["overrides"]
            if override.get("ignore_errors") is True
            for module in override["module"]
        }
        self.assertEqual(
            debt_modules,
            {
                "seriemacv.applications",
                "seriemacv.career",
                "seriemacv.jobs",
                "seriemacv.proposals",
                "seriemacv.renderer",
                "seriemacv.variants",
            },
        )

    def test_agent_policies_cover_untrusted_content_and_browser_boundaries(
        self,
    ) -> None:
        shared = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        development = (self.root / "agents/development.md").read_text(encoding="utf-8")
        jobs = (self.root / "agents/jobs.md").read_text(encoding="utf-8")

        self.assertIn("untrusted data", shared)
        self.assertIn("Do not weaken checks", development)
        self.assertIn(
            "After the same command or browser action fails twice", development
        )
        self.assertIn("Do not infer checkbox, radio, or select semantics", jobs)
        self.assertIn("Do not bypass CAPTCHA", jobs)
        self.assertIn("do not create or submit a duplicate application", jobs)


if __name__ == "__main__":
    unittest.main()
