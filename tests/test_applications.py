from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from seriemacv.application_ai import (
    ApplicationAiAnswer,
    ApplicationAiCoverLetter,
    ApplicationAiResponse,
    apply_ai_response,
    create_ai_request,
    dump_ai,
    validate_ai_response,
)
from seriemacv.applications import (
    ApplicationDocument,
    ApplicationQuestion,
    add_questions,
    apply_answer,
    create_application,
    load_application,
    update_status,
)
from seriemacv.browser import (
    BrowserField,
    _questions_for,
    _saved_answers_for_seniority,
    _wait_for_form_controls,
    browser_profile_path,
)
from seriemacv.career import SavedAnswer
from seriemacv.cli import main
from seriemacv.project import create_project


class ApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name) / "career"
        create_project(self.project, project_name="Career")
        (self.project / "career.yml").write_text(
            "schema_version: 2\nprofile: {name: Example, email: example@example.invalid}\n"
            "experience: []\neducation: []\nskills: []\n"
            "evidence: [{id: verified-work, statement: Delivered services., verified: true}]\n"
            "answers: []\nstories: []\n",
            encoding="utf-8",
        )
        (self.project / "jobs" / "role.yml").write_text(
            "schema_version: 1\nid: role\ntitle: Role\nsource: {format: manual, content: Role}\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_application_state_question_and_explicit_saved_answer_flow(self) -> None:
        create_application(self.project, ApplicationDocument(id="role-application", job_id="role"))
        preparing = update_status(self.project, "role-application", "preparing")
        self.assertEqual(preparing.status, "preparing")
        add_questions(self.project, "role-application", [ApplicationQuestion(
            id="question-why", field_id="why", label="Why this role?",
        )])
        with self.assertRaisesRegex(ValueError, "explicit answer or a proposal"):
            apply_answer(self.project, "role-application", "question-why")
        completed = apply_answer(
            self.project, "role-application", "question-why", "Because the work fits.",
            save_answer_id="why-role",
        )
        self.assertEqual(completed.status, "ready_for_review")
        self.assertEqual(completed.answers[0].answer, "Because the work fits.")
        self.assertEqual(load_application(self.project, "role-application").answers[0].saved_answer_id, "why-role")
        with self.assertRaisesRegex(ValueError, "invalid status transition"):
            update_status(self.project, "role-application", "interview")
        self.assertEqual(update_status(self.project, "role-application", "applied").status, "applied")

    def test_rejects_invalid_links_and_sensitive_fields_stay_pending(self) -> None:
        with self.assertRaises(OSError):
            create_application(self.project, ApplicationDocument(id="missing-job", job_id="missing"))
        create_application(self.project, ApplicationDocument(id="role-application", job_id="role"))
        questions = _questions_for([
            BrowserField("email", 0, "Email", True, "text", False),
            BrowserField("salary", 1, "Salary expectation", True, "text", True),
        ], load_application(self.project, "role-application"), {"email"})
        self.assertEqual([item.id for item in questions], ["question-salary"])
        self.assertTrue(questions[0].sensitive)

    def test_saved_answer_requires_review_before_it_can_fill_a_new_application(self) -> None:
        create_application(self.project, ApplicationDocument(id="role-application", job_id="role"))
        questions = _questions_for(
            [BrowserField("portfolio", 0, "Portfolio", True, "text", False)],
            load_application(self.project, "role-application"),
            set(),
            saved_answers={"portfolio": ("https://example.invalid/work", ["verified-work"], False)},
        )

        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].proposed_answer, "https://example.invalid/work")
        self.assertEqual(questions[0].proposed_evidence_ids, ["verified-work"])

    def test_saved_salary_is_proposed_only_for_its_staff_scope(self) -> None:
        answer = SavedAnswer(
            id="staff-salary",
            prompt="Expected salary?",
            answer="USD 8,000-10,000 monthly gross",
            sensitive=True,
            role_scope=["staff"],
        )

        staff_answers = _saved_answers_for_seniority([answer], "Staff")
        senior_answers = _saved_answers_for_seniority([answer], "Senior")

        self.assertIn("expected salary?", staff_answers)
        self.assertNotIn("expected salary?", senior_answers)
        create_application(self.project, ApplicationDocument(id="role-application", job_id="role"))
        questions = _questions_for(
            [BrowserField("salary", 0, "Expected salary?", True, "text", True)],
            load_application(self.project, "role-application"),
            set(),
            saved_answers=staff_answers,
        )
        self.assertEqual(questions[0].proposed_answer, "USD 8,000-10,000 monthly gross")

    def test_sensitive_optional_field_is_queued_for_review(self) -> None:
        create_application(self.project, ApplicationDocument(id="role-application", job_id="role"))
        questions = _questions_for(
            [BrowserField("invoice", 0, "Can you issue invoices?", False, "checkbox", True)],
            load_application(self.project, "role-application"),
            set(),
        )

        self.assertEqual([item.id for item in questions], ["question-invoice"])
        self.assertFalse(questions[0].required)
        self.assertTrue(questions[0].sensitive)

    def test_browser_profile_is_scoped_to_its_project(self) -> None:
        other_project = Path(self.temporary.name) / "other-career"
        create_project(other_project, project_name="Other career")

        self.assertEqual(browser_profile_path(self.project), self.project / ".seriemacv" / "browser")
        self.assertEqual(browser_profile_path(other_project), other_project / ".seriemacv" / "browser")
        self.assertNotEqual(browser_profile_path(self.project), browser_profile_path(other_project))

    def test_browser_preparation_waits_for_client_rendered_form_controls(self) -> None:
        class Page:
            def __init__(self) -> None:
                self.calls: list[tuple[object, ...]] = []

            def wait_for_selector(self, selector: str, *, state: str) -> None:
                self.calls.append(("selector", selector, state))

            def wait_for_timeout(self, timeout: int) -> None:
                self.calls.append(("timeout", timeout))

        page = Page()
        _wait_for_form_controls(page)

        self.assertEqual(page.calls, [
            ("selector", "input, select, textarea", "attached"),
            ("timeout", 500),
        ])

    def test_cli_creates_lists_and_updates_application(self) -> None:
        with redirect_stdout(StringIO()):
            result = main([
                "applications", "create", str(self.project), "--id", "cli-application",
                "--job-id", "role",
            ])
        self.assertEqual(result, 0)
        with redirect_stdout(StringIO()) as output:
            result = main(["applications", "list", str(self.project)])
        self.assertEqual(result, 0)
        self.assertIn("cli-application", output.getvalue())
        with redirect_stdout(StringIO()) as output:
            result = main(["applications", "set-status", str(self.project), "cli-application", "preparing"])
        self.assertEqual(result, 0)
        self.assertIn("preparing", output.getvalue())

    def test_cli_applies_an_explicit_application_answer(self) -> None:
        create_application(self.project, ApplicationDocument(id="role-application", job_id="role"))
        add_questions(self.project, "role-application", [
            ApplicationQuestion(id="question-why", field_id="why", label="Why this role?"),
        ])

        with redirect_stdout(StringIO()) as output:
            result = main([
                "applications", "apply-answer", str(self.project), "role-application",
                "question-why", "--answer", "Because the work fits.",
            ])

        self.assertEqual(result, 0)
        self.assertIn("Because the work fits.", output.getvalue())

    def test_ai_response_is_reviewable_and_requires_explicit_item_acceptance(self) -> None:
        create_application(self.project, ApplicationDocument(id="role-application", job_id="role"))
        add_questions(self.project, "role-application", [
            ApplicationQuestion(id="question-why", field_id="why", label="Why this role?"),
            ApplicationQuestion(id="question-salary", field_id="salary", label="Salary", sensitive=True),
        ])
        request = create_ai_request(self.project, "role-ai", "role-application")
        self.assertNotIn("example@example.invalid", request.model_dump_json())
        response = ApplicationAiResponse(
            request_id="role-ai",
            answers=[ApplicationAiAnswer(id="why-answer", question_id="question-why", answer="Relevant delivery experience.", evidence_ids=["verified-work"], confidence="high")],
            cover_letter=ApplicationAiCoverLetter(id="letter", body="Dear team,\n\nI delivered services.", evidence_ids=["verified-work"], confidence="medium"),
        )
        self.assertEqual({item.id for item in validate_ai_response(self.project, request, response)}, {"why-answer", "letter"})
        applied = apply_ai_response(self.project, request, response, ["why-answer", "letter"])
        self.assertEqual(applied.questions[0].proposed_answer, "Relevant delivery experience.")
        self.assertTrue(applied.cover_letter_path)
        self.assertTrue((self.project / applied.cover_letter_path).is_file())
        sensitive = ApplicationAiResponse(request_id="role-ai", answers=[ApplicationAiAnswer(id="bad", question_id="question-salary", answer="100", confidence="low")])
        with self.assertRaisesRegex(ValueError, "sensitive"):
            validate_ai_response(self.project, request, sensitive)

    def test_cli_ai_preview_matches_request_without_writing(self) -> None:
        create_application(self.project, ApplicationDocument(id="role-application", job_id="role"))
        add_questions(self.project, "role-application", [
            ApplicationQuestion(id="question-why", field_id="why", label="Why this role?"),
        ])
        before = {path.relative_to(self.project) for path in self.project.rglob("*")}

        with redirect_stdout(StringIO()) as output:
            result = main([
                "applications", "ai-preview", str(self.project), "role-application",
                "--request-id", "role-ai",
            ])

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), dump_ai(create_ai_request(self.project, "role-ai", "role-application")))
        self.assertEqual(before, {path.relative_to(self.project) for path in self.project.rglob("*")})
