from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
    ApplicationAnswer,
    ApplicationDocument,
    ApplicationQuestion,
    add_questions,
    application_context,
    apply_answer,
    create_application,
    load_application,
    replace_questions,
    update_status,
)
from seriemacv.browser import (
    BrowserField,
    _attach_documents,
    _fill_and_persist_application_page,
    _fill_greenhouse_combobox,
    _greenhouse_confirmed_answers,
    _greenhouse_profile_values,
    _interactive_browser_session,
    _is_greenhouse_application,
    _prepare_resume_attachment,
    _profile_value_for_field,
    _questions_for,
    _saved_answers_for_job,
    _wait_for_form_controls,
    browser_profile_path,
    discover_fields,
    prepare_job_application,
)
from seriemacv.career import SavedAnswer, load_career
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
        create_application(
            self.project, ApplicationDocument(id="role-application", job_id="role")
        )
        preparing = update_status(self.project, "role-application", "preparing")
        self.assertEqual(preparing.status, "preparing")
        add_questions(
            self.project,
            "role-application",
            [
                ApplicationQuestion(
                    id="question-why",
                    field_id="why",
                    label="Why this role?",
                )
            ],
        )
        with self.assertRaisesRegex(ValueError, "explicit answer or a proposal"):
            apply_answer(self.project, "role-application", "question-why")
        completed = apply_answer(
            self.project,
            "role-application",
            "question-why",
            "Because the work fits.",
            save_answer_id="why-role",
            save_role_scope=["staff"],
            save_language_scope=["en"],
        )
        self.assertEqual(completed.status, "ready_for_review")
        career = load_career(self.project / "career.yml")
        self.assertEqual(career.answers[0].role_scope, ["staff"])
        self.assertEqual(career.answers[0].language_scope, ["en"])
        self.assertEqual(completed.answers[0].answer, "Because the work fits.")
        self.assertEqual(
            load_application(self.project, "role-application")
            .answers[0]
            .saved_answer_id,
            "why-role",
        )
        with self.assertRaisesRegex(ValueError, "invalid status transition"):
            update_status(self.project, "role-application", "interview")
        self.assertEqual(
            update_status(self.project, "role-application", "applied").status, "applied"
        )

    def test_rejects_invalid_links_and_sensitive_fields_stay_pending(self) -> None:
        with self.assertRaises(OSError):
            create_application(
                self.project, ApplicationDocument(id="missing-job", job_id="missing")
            )
        create_application(
            self.project, ApplicationDocument(id="role-application", job_id="role")
        )
        questions = _questions_for(
            [
                BrowserField("email", 0, "Email", True, "text", False),
                BrowserField("salary", 1, "Salary expectation", True, "text", True),
            ],
            load_application(self.project, "role-application"),
            {"email"},
        )
        self.assertEqual([item.id for item in questions], ["question-salary"])
        self.assertTrue(questions[0].sensitive)

    def test_saved_answer_requires_review_before_it_can_fill_a_new_application(
        self,
    ) -> None:
        create_application(
            self.project, ApplicationDocument(id="role-application", job_id="role")
        )
        questions = _questions_for(
            [BrowserField("portfolio", 0, "Portfolio", True, "text", False)],
            load_application(self.project, "role-application"),
            set(),
            saved_answers={
                "portfolio": ("https://example.invalid/work", ["verified-work"], False)
            },
        )

        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].proposed_answer, "https://example.invalid/work")
        self.assertEqual(questions[0].proposed_evidence_ids, ["verified-work"])

    def test_saved_salary_is_proposed_only_for_its_staff_english_scope(self) -> None:
        answer = SavedAnswer(
            id="staff-salary",
            prompt="Expected salary?",
            answer="USD 8,000-10,000 monthly gross",
            sensitive=True,
            role_scope=["staff"],
            language_scope=["en"],
        )

        staff_english_answers = _saved_answers_for_job([answer], "Staff", "English")
        senior_english_answers = _saved_answers_for_job([answer], "Senior", "English")
        staff_portuguese_answers = _saved_answers_for_job(
            [answer], "Staff", "Portuguese"
        )

        self.assertIn("expected salary?", staff_english_answers)
        self.assertNotIn("expected salary?", senior_english_answers)
        self.assertNotIn("expected salary?", staff_portuguese_answers)
        create_application(
            self.project, ApplicationDocument(id="role-application", job_id="role")
        )
        questions = _questions_for(
            [BrowserField("salary", 0, "Expected salary?", True, "text", True)],
            load_application(self.project, "role-application"),
            set(),
            saved_answers=staff_english_answers,
        )
        self.assertEqual(questions[0].proposed_answer, "USD 8,000-10,000 monthly gross")

    def test_sensitive_optional_field_is_queued_for_review(self) -> None:
        create_application(
            self.project, ApplicationDocument(id="role-application", job_id="role")
        )
        questions = _questions_for(
            [
                BrowserField(
                    "invoice", 0, "Can you issue invoices?", False, "checkbox", True
                )
            ],
            load_application(self.project, "role-application"),
            set(),
        )

        self.assertEqual([item.id for item in questions], ["question-invoice"])
        self.assertFalse(questions[0].required)
        self.assertTrue(questions[0].sensitive)

    def test_refreshing_greenhouse_questions_removes_optional_stale_fields(
        self,
    ) -> None:
        create_application(
            self.project, ApplicationDocument(id="role-application", job_id="role")
        )
        update_status(self.project, "role-application", "preparing")
        add_questions(
            self.project,
            "role-application",
            [
                ApplicationQuestion(
                    id="question-demographic",
                    field_id="demographic",
                    label="Demographic",
                    required=False,
                    sensitive=True,
                ),
            ],
        )

        refreshed = replace_questions(
            self.project,
            "role-application",
            [
                ApplicationQuestion(
                    id="question-why", field_id="why", label="Why this role?"
                ),
            ],
        )

        self.assertEqual(refreshed.status, "needs_user_input")
        self.assertEqual(
            [question.id for question in refreshed.questions], ["question-why"]
        )

    def test_refreshing_questions_keeps_current_unanswered_field_detected(self) -> None:
        create_application(
            self.project, ApplicationDocument(id="role-application", job_id="role")
        )
        add_questions(
            self.project,
            "role-application",
            [
                ApplicationQuestion(
                    id="question-why", field_id="why", label="Why this role?"
                ),
            ],
        )

        detected = _questions_for(
            [BrowserField("why", 0, "Why this role?", True, "text", False)],
            load_application(self.project, "role-application"),
            set(),
        )

        self.assertEqual([question.id for question in detected], ["question-why"])

    def test_browser_profile_is_scoped_to_its_project(self) -> None:
        other_project = Path(self.temporary.name) / "other-career"
        create_project(other_project, project_name="Other career")

        self.assertEqual(
            browser_profile_path(self.project), self.project / ".seriemacv" / "browser"
        )
        self.assertEqual(
            browser_profile_path(other_project),
            other_project / ".seriemacv" / "browser",
        )
        self.assertNotEqual(
            browser_profile_path(self.project), browser_profile_path(other_project)
        )

    def test_greenhouse_name_fields_use_first_and_last_name_parts(self) -> None:
        career = load_career(self.project / "career.yml")
        career.profile.name = "Example Person"

        self.assertEqual(_profile_value_for_field("First Name", career), "Example")
        self.assertEqual(_profile_value_for_field("Last Name", career), "Person")
        self.assertEqual(
            _profile_value_for_field("Full Name", career), "Example Person"
        )
        self.assertEqual(
            _profile_value_for_field("Email", career), "example@example.invalid"
        )

    def test_greenhouse_hidden_required_mirror_is_not_discovered_as_a_question(
        self,
    ) -> None:
        class Locator:
            def evaluate_all(self, _: str) -> list[dict[str, object]]:
                return [
                    {
                        "id": "country",
                        "label": "Country",
                        "required": True,
                        "type": "text",
                        "hidden": False,
                    },
                    {
                        "id": "country-required",
                        "label": "",
                        "required": True,
                        "type": "text",
                        "hidden": True,
                    },
                ]

        class Page:
            def locator(self, _: str) -> Locator:
                return Locator()

        fields = discover_fields(Page())

        self.assertEqual(
            [(item.field_id, item.label) for item in fields], [("country", "Country")]
        )

    def test_discovery_groups_radio_options_by_name_and_visible_question(self) -> None:
        class Locator:
            def evaluate_all(self, _: str) -> list[dict[str, object]]:
                return [
                    {
                        "index": 0,
                        "id": "english-basic",
                        "name": "english-level",
                        "label": "Basic",
                        "groupLabel": "English proficiency",
                        "required": True,
                        "type": "radio",
                        "hidden": False,
                        "populated": False,
                    },
                    {
                        "index": 1,
                        "id": "english-advanced",
                        "name": "english-level",
                        "label": "Advanced",
                        "groupLabel": "English proficiency",
                        "required": True,
                        "type": "radio",
                        "hidden": False,
                        "populated": True,
                    },
                ]

        class Page:
            def locator(self, _: str) -> Locator:
                return Locator()

        fields = discover_fields(Page())

        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0].field_id, "english-level")
        self.assertEqual(fields[0].label, "English proficiency")
        self.assertEqual(fields[0].options, ("Basic", "Advanced"))
        self.assertTrue(fields[0].populated)

    def test_populated_group_is_not_reported_as_pending(self) -> None:
        create_application(
            self.project, ApplicationDocument(id="role-application", job_id="role")
        )
        questions = _questions_for(
            [
                BrowserField(
                    "english-level",
                    0,
                    "English proficiency",
                    True,
                    "radio",
                    False,
                    ("Basic", "Advanced"),
                    True,
                )
            ],
            load_application(self.project, "role-application"),
            set(),
        )

        self.assertEqual(questions, [])

    def test_group_options_are_preserved_in_one_pending_question(self) -> None:
        create_application(
            self.project, ApplicationDocument(id="role-application", job_id="role")
        )
        questions = _questions_for(
            [
                BrowserField(
                    "english-level",
                    0,
                    "English proficiency",
                    True,
                    "radio",
                    False,
                    ("Basic", "Advanced"),
                )
            ],
            load_application(self.project, "role-application"),
            set(),
        )

        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].options, ["Basic", "Advanced"])

    def test_greenhouse_adapter_uses_dedicated_fields_for_location_and_linkedin(
        self,
    ) -> None:
        career = load_career(self.project / "career.yml")
        career.profile.name = "Example Person"
        career.profile.linkedin = "https://www.linkedin.com/in/example"

        values = _greenhouse_profile_values(
            career.profile, "Mogi Mirim, São Paulo, Brazil"
        )

        self.assertTrue(
            _is_greenhouse_application(
                "https://job-boards.greenhouse.io/example/jobs/1"
            )
        )
        self.assertEqual(values["#first_name"], "Example")
        self.assertEqual(values["#last_name"], "Person")
        self.assertEqual(values["#country"], "Brazil")
        self.assertEqual(values["#candidate-location"], "Mogi Mirim, Sao Paulo, Brazil")
        self.assertEqual(
            values["#question_12689993007, input[name='question_12689993007']"],
            "https://www.linkedin.com/in/example",
        )

    def test_greenhouse_adapter_maps_answers_to_their_exact_controls(self) -> None:
        document = ApplicationDocument(
            id="role-application",
            job_id="role",
            answers=[
                ApplicationAnswer(
                    field_id="question-12689994007",
                    answer="Interest",
                    confirmed_for_application=True,
                ),
                ApplicationAnswer(
                    field_id="question-12689995007",
                    answer="AI tools",
                    confirmed_for_application=True,
                ),
                ApplicationAnswer(
                    field_id="question-12689996007",
                    answer="Ruby work",
                    confirmed_for_application=True,
                ),
                ApplicationAnswer(
                    field_id="question-12689997007",
                    answer="Yes",
                    sensitive=True,
                    confirmed_for_application=True,
                ),
                ApplicationAnswer(
                    field_id="question-12689998007",
                    answer="LinkedIn",
                    sensitive=True,
                    confirmed_for_application=True,
                ),
                ApplicationAnswer(
                    field_id="question-12690001007",
                    answer="No",
                    sensitive=True,
                    confirmed_for_application=True,
                ),
            ],
        )

        answers = _greenhouse_confirmed_answers(document)

        self.assertEqual(answers["question-12689994007"], ("Interest", False))
        self.assertEqual(answers["question-12689995007"], ("AI tools", False))
        self.assertEqual(answers["question-12689996007"], ("Ruby work", False))
        self.assertEqual(answers["question-12689997007"], ("Yes", True))
        self.assertEqual(answers["question-12689998007"], ("LinkedIn", True))
        self.assertEqual(answers["question-12690001007"], ("No", True))

    def test_greenhouse_adapter_attaches_english_resume_to_resume_field_only(
        self,
    ) -> None:
        expected_resume = self.project / "exports" / "resume.en.pdf"
        expected_resume.write_bytes(b"existing PDF")
        create_application(
            self.project,
            ApplicationDocument(
                id="role-application",
                job_id="role",
                attachments=["exports/resume.en.pdf"],
            ),
        )

        class Locator:
            def __init__(self) -> None:
                self.files: list[str] = []

            @property
            def first(self) -> "Locator":
                return self

            def count(self) -> int:
                return 1

            def set_input_files(self, files: list[str]) -> None:
                self.files = files

        class Page:
            def __init__(self) -> None:
                self.selector = ""
                self.field = Locator()

            def locator(self, selector: str) -> Locator:
                self.selector = selector
                return self.field

        page = Page()
        with patch("seriemacv.browser.write_resume") as render_resume:
            _attach_documents(
                page,
                [],
                self.project,
                load_application(self.project, "role-application"),
                job=SimpleNamespace(language="English"),
                greenhouse=True,
            )

        self.assertEqual(page.selector, "input#resume, input[name='resume']")
        self.assertEqual(page.field.files, [str(expected_resume)])
        render_resume.assert_not_called()

    def test_generic_adapter_uploads_without_rendering_inside_browser(self) -> None:
        expected_resume = self.project / "exports" / "resume.en.pdf"
        expected_resume.write_bytes(b"existing PDF")
        create_application(
            self.project,
            ApplicationDocument(
                id="role-application",
                job_id="role",
                attachments=["exports/resume.en.pdf"],
            ),
        )

        class Locator:
            def __init__(self) -> None:
                self.files: list[str] = []

            def nth(self, index: int) -> "Locator":
                self.index = index
                return self

            def set_input_files(self, files: list[str]) -> None:
                self.files = files

        class Page:
            def __init__(self) -> None:
                self.field = Locator()

            def locator(self, selector: str) -> Locator:
                return self.field

        page = Page()
        with patch("seriemacv.browser.write_resume") as render_resume:
            _attach_documents(
                page,
                [BrowserField("resume", 0, "Resume", True, "file", False)],
                self.project,
                load_application(self.project, "role-application"),
                job=SimpleNamespace(language="English"),
            )

        render_resume.assert_not_called()
        self.assertEqual(page.field.files, [str(expected_resume)])

    def test_resume_attachment_is_reused_before_browser_launch(self) -> None:
        expected_resume = self.project / "exports" / "resume.en.pdf"
        expected_resume.write_bytes(b"existing PDF")
        create_application(
            self.project,
            ApplicationDocument(
                id="role-application",
                job_id="role",
                attachments=["exports/resume.en.pdf"],
            ),
        )

        with patch("seriemacv.browser.write_resume") as render_resume:
            document = _prepare_resume_attachment(
                self.project,
                load_application(self.project, "role-application"),
                SimpleNamespace(language="English"),
            )

        self.assertEqual(document.attachments, ["exports/resume.en.pdf"])
        render_resume.assert_not_called()

    def test_greenhouse_combobox_requires_exact_option_and_selected_value(
        self,
    ) -> None:
        class Control:
            def __init__(self) -> None:
                self.value = ""
                self.timeouts: list[int] = []

            def count(self) -> int:
                return 1

            def get_attribute(self, name: str) -> str | None:
                return "country-options" if name == "aria-controls" else None

            def fill(self, value: str, *, timeout: int) -> None:
                self.value = value
                self.timeouts.append(timeout)

            def input_value(self) -> str:
                return self.value

        class Options:
            def __init__(self, control: Control, labels: list[str]) -> None:
                self.control = control
                self.labels = labels
                self.index = 0
                self.click_timeout = 0

            def all_inner_texts(self) -> list[str]:
                return self.labels

            def nth(self, index: int) -> "Options":
                self.index = index
                return self

            def click(self, *, timeout: int) -> None:
                self.click_timeout = timeout
                self.control.value = self.labels[self.index]

        class Page:
            def __init__(self, labels: list[str]) -> None:
                self.control = Control()
                self.options = Options(self.control, labels)
                self.wait_timeout = 0

            def locator(self, selector: str) -> object:
                return self.control if selector == "#country" else self.options

            def wait_for_selector(
                self, selector: str, *, state: str, timeout: int
            ) -> None:
                self.wait_timeout = timeout

        valid = Page(["Canada", "Brazil"])
        invalid = Page(["Brazil (+55)"])
        failed: set[str] = set()

        self.assertTrue(
            _fill_greenhouse_combobox(
                valid, "#country", "Brazil", failed=failed, failure_key="country"
            )
        )
        self.assertEqual(valid.control.timeouts, [2_000])
        self.assertEqual(valid.wait_timeout, 2_000)
        self.assertEqual(valid.options.click_timeout, 2_000)
        self.assertFalse(
            _fill_greenhouse_combobox(
                invalid, "#country", "Brazil", failed=failed, failure_key="phone"
            )
        )
        self.assertIn("phone", failed)

        invalid.control.timeouts.clear()
        self.assertFalse(
            _fill_greenhouse_combobox(
                invalid, "#country", "Brazil", failed=failed, failure_key="phone"
            )
        )
        self.assertEqual(invalid.control.timeouts, [])

    def test_questions_are_persisted_before_attachment_failure(self) -> None:
        create_application(
            self.project, ApplicationDocument(id="role-application", job_id="role")
        )
        document = load_application(self.project, "role-application")
        fields = [BrowserField("source", 0, "How did you hear?", True, "text", False)]

        def persist(discovered: list[BrowserField], filled: set[str]) -> None:
            replace_questions(
                self.project,
                document.id,
                _questions_for(discovered, document, filled),
            )

        with (
            patch("seriemacv.browser._inspect_application_page", return_value=fields),
            patch("seriemacv.browser._fill_known", return_value=set()),
            patch(
                "seriemacv.browser._attach_documents",
                side_effect=RuntimeError("upload failed"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "upload failed"):
                _fill_and_persist_application_page(
                    SimpleNamespace(),
                    self.project,
                    document,
                    SimpleNamespace(seniority="", language="English"),
                    failed_comboboxes=set(),
                    persisted=persist,
                )

        saved = load_application(self.project, "role-application")
        self.assertEqual(
            [question.field_id for question in saved.questions], ["source"]
        )

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

        self.assertEqual(
            page.calls,
            [
                ("selector", "input, select, textarea", "attached"),
                ("timeout", 500),
            ],
        )

    def test_interactive_browser_session_refills_without_closing(self) -> None:
        calls: list[str] = []

        def refill() -> tuple[list[BrowserField], set[str]]:
            calls.append("refill")
            return [], set()

        def inspect() -> tuple[list[BrowserField], set[str]]:
            calls.append("inspect")
            return [], set()

        with patch("builtins.input", side_effect=["refill", "inspect", "close"]):
            with redirect_stdout(StringIO()):
                _interactive_browser_session(refill, inspect)

        self.assertEqual(calls, ["refill", "inspect"])

    def test_application_context_is_compact_and_redacts_sensitive_answers(self) -> None:
        create_application(
            self.project,
            ApplicationDocument(
                id="role-application",
                job_id="role",
                answers=[
                    ApplicationAnswer(
                        field_id="salary",
                        answer="10000",
                        sensitive=True,
                        confirmed_for_application=True,
                    ),
                    ApplicationAnswer(
                        field_id="portfolio",
                        answer="https://example.invalid/work " + ("detail " * 80),
                        confirmed_for_application=True,
                    ),
                ],
            ),
        )

        context = application_context(self.project, "role-application")

        self.assertEqual(context["thread_key"], "role")
        answers = context["confirmed_answers"]
        self.assertEqual(
            answers[0],
            {"field_id": "salary", "answer": "[confirmed sensitive answer]"},
        )
        self.assertEqual(answers[1]["field_id"], "portfolio")
        self.assertTrue(answers[1]["answer"].endswith("…"))
        self.assertNotIn("10000", str(context))
        self.assertLessEqual(len(answers[1]["answer"]), 240)

    def test_prepare_job_creates_application_and_renders_resume_once(self) -> None:
        resume = self.project / "exports" / "resume.en.pdf"
        resume.write_bytes(b"pdf")
        with (
            patch("seriemacv.browser.write_resume", return_value=resume) as render,
            patch(
                "seriemacv.browser.load_localized_career",
                return_value=load_career(self.project / "career.yml"),
            ),
            patch("seriemacv.browser.prepare_application") as prepare,
        ):
            prepare.side_effect = lambda project, application_id, **_: load_application(
                project, application_id
            )
            document = prepare_job_application(
                self.project,
                "role",
                url="https://jobs.example.invalid/role/apply",
            )

        self.assertEqual(document.id, "role-application")
        self.assertEqual(document.attachments, ["exports/resume.en.pdf"])
        render.assert_called_once()
        prepare.assert_called_once()

    def test_cli_creates_lists_and_updates_application(self) -> None:
        with redirect_stdout(StringIO()):
            result = main(
                [
                    "applications",
                    "create",
                    str(self.project),
                    "--id",
                    "cli-application",
                    "--job-id",
                    "role",
                ]
            )
        self.assertEqual(result, 0)
        with redirect_stdout(StringIO()) as output:
            result = main(["applications", "list", str(self.project)])
        self.assertEqual(result, 0)
        self.assertIn("cli-application", output.getvalue())
        with redirect_stdout(StringIO()) as output:
            result = main(
                [
                    "applications",
                    "set-status",
                    str(self.project),
                    "cli-application",
                    "preparing",
                ]
            )
        self.assertEqual(result, 0)
        self.assertIn("preparing", output.getvalue())

    def test_cli_prints_bounded_application_context(self) -> None:
        create_application(
            self.project, ApplicationDocument(id="role-application", job_id="role")
        )

        with redirect_stdout(StringIO()) as output:
            result = main(
                [
                    "applications",
                    "context",
                    str(self.project),
                    "role-application",
                ]
            )

        self.assertEqual(result, 0)
        self.assertIn("thread_key: role", output.getvalue())
        self.assertIn("next_action: prepare the application", output.getvalue())
        self.assertNotIn("source:", output.getvalue())

    def test_cli_applies_an_explicit_application_answer(self) -> None:
        create_application(
            self.project, ApplicationDocument(id="role-application", job_id="role")
        )
        add_questions(
            self.project,
            "role-application",
            [
                ApplicationQuestion(
                    id="question-why", field_id="why", label="Why this role?"
                ),
            ],
        )

        with redirect_stdout(StringIO()) as output:
            result = main(
                [
                    "applications",
                    "apply-answer",
                    str(self.project),
                    "role-application",
                    "question-why",
                    "--answer",
                    "Because the work fits.",
                ]
            )

        self.assertEqual(result, 0)
        self.assertIn("Because the work fits.", output.getvalue())

    def test_ai_response_is_reviewable_and_requires_explicit_item_acceptance(
        self,
    ) -> None:
        create_application(
            self.project, ApplicationDocument(id="role-application", job_id="role")
        )
        add_questions(
            self.project,
            "role-application",
            [
                ApplicationQuestion(
                    id="question-why", field_id="why", label="Why this role?"
                ),
                ApplicationQuestion(
                    id="question-salary",
                    field_id="salary",
                    label="Salary",
                    sensitive=True,
                ),
            ],
        )
        request = create_ai_request(self.project, "role-ai", "role-application")
        self.assertNotIn("example@example.invalid", request.model_dump_json())
        response = ApplicationAiResponse(
            request_id="role-ai",
            answers=[
                ApplicationAiAnswer(
                    id="why-answer",
                    question_id="question-why",
                    answer="Relevant delivery experience.",
                    evidence_ids=["verified-work"],
                    confidence="high",
                )
            ],
            cover_letter=ApplicationAiCoverLetter(
                id="letter",
                body="Dear team,\n\nI delivered services.",
                evidence_ids=["verified-work"],
                confidence="medium",
            ),
        )
        self.assertEqual(
            {item.id for item in validate_ai_response(self.project, request, response)},
            {"why-answer", "letter"},
        )
        applied = apply_ai_response(
            self.project, request, response, ["why-answer", "letter"]
        )
        self.assertEqual(
            applied.questions[0].proposed_answer, "Relevant delivery experience."
        )
        self.assertTrue(applied.cover_letter_path)
        self.assertTrue((self.project / applied.cover_letter_path).is_file())
        sensitive = ApplicationAiResponse(
            request_id="role-ai",
            answers=[
                ApplicationAiAnswer(
                    id="bad",
                    question_id="question-salary",
                    answer="100",
                    confidence="low",
                )
            ],
        )
        with self.assertRaisesRegex(ValueError, "sensitive"):
            validate_ai_response(self.project, request, sensitive)

    def test_cli_ai_preview_matches_request_without_writing_domain_artifacts(
        self,
    ) -> None:
        create_application(
            self.project, ApplicationDocument(id="role-application", job_id="role")
        )
        add_questions(
            self.project,
            "role-application",
            [
                ApplicationQuestion(
                    id="question-why", field_id="why", label="Why this role?"
                ),
            ],
        )
        before = {path.relative_to(self.project) for path in self.project.rglob("*")}

        with redirect_stdout(StringIO()) as output:
            result = main(
                [
                    "applications",
                    "ai-preview",
                    str(self.project),
                    "role-application",
                    "--request-id",
                    "role-ai",
                ]
            )

        self.assertEqual(result, 0)
        self.assertEqual(
            output.getvalue(),
            dump_ai(create_ai_request(self.project, "role-ai", "role-application")),
        )
        after = {path.relative_to(self.project) for path in self.project.rglob("*")}
        self.assertEqual(
            after - before,
            {
                Path(".seriemacv/metrics"),
                Path(".seriemacv/metrics/operations.jsonl"),
            },
        )
