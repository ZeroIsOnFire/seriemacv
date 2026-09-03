"""Generic, local Playwright preparation for a reviewed application."""

from __future__ import annotations

import re
import shutil
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from seriemacv.applications import (
    ApplicationDocument,
    ApplicationQuestion,
    load_application,
    replace_questions,
    update_status,
)
from seriemacv.career import SavedAnswer, load_career, load_localized_career
from seriemacv.jobs import load_job
from seriemacv.project import load_project_configuration
from seriemacv.renderer import ResumeRenderError, write_resume
from seriemacv.variants import load_variant_career

_SENSITIVE = re.compile(r"salary|compensation|pay|legal|authori[sz](ation|ed)|visa|sponsor(ship)?|work permit|sole proprietor|invoice|demographic|gender|race|ethnicity|disability|veteran|self.ident", re.I)
_PROFILE_FIELDS = {
    "full name": "name", "email": "email", "phone": "phone",
    "linkedin": "linkedin", "portfolio": "portfolio", "github": "portfolio",
}
_FORM_CONTROLS = "input, select, textarea"
_TEXT_INPUT_TYPES = {"text", "email", "tel", "url", "textarea"}
_GREENHOUSE_ANSWER_FIELDS = {
    "question-12689994007": ("#question_12689994007, textarea[name='question_12689994007']", False),
    "question-12689995007": ("#question_12689995007, textarea[name='question_12689995007']", False),
    "question-12689996007": ("#question_12689996007, textarea[name='question_12689996007']", False),
    "question-12689997007": ("#question_12689997007, input[name='question_12689997007']", True),
    "question-12689998007": ("#question_12689998007, input[name='question_12689998007']", True),
    "question-12690000007": ("#question_12690000007, input[name='question_12690000007']", True),
    "question-12690001007": ("#question_12690001007, input[name='question_12690001007']", True),
}


@dataclass(frozen=True)
class BrowserField:
    field_id: str
    index: int
    label: str
    required: bool
    input_type: str
    sensitive: bool


def browser_profile_path(project_path: Path) -> Path:
    return project_path / ".seriemacv" / "browser"


def clear_browser_profile(project_path: Path) -> None:
    profile = browser_profile_path(project_path)
    if profile.exists():
        shutil.rmtree(profile)


def discover_fields(page: Any) -> list[BrowserField]:
    """Inspect generic form controls without retaining their values."""
    raw = page.locator(_FORM_CONTROLS).evaluate_all("""elements => elements.map((element, index) => {
      const label = element.labels && element.labels.length ? element.labels[0].innerText :
        element.getAttribute('aria-label') || element.getAttribute('placeholder') ||
        (element.type === 'checkbox' ? element.parentElement?.innerText : '') ||
        element.name || element.id || `field-${index + 1}`;
      return {
        id: element.id || element.name || `field-${index + 1}`,
        label,
        required: element.required || element.getAttribute('aria-required') === 'true',
        type: element.type || element.tagName.toLowerCase(),
        hidden: element.type === 'hidden' || element.getAttribute('aria-hidden') === 'true'
      };
    })""")
    fields: list[BrowserField] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if item.get("hidden"):
            continue
        field_id = re.sub(r"[^a-z0-9]+", "-", str(item["id"]).lower()).strip("-") or "field"
        if field_id in seen:
            field_id = f"{field_id}-{len(seen) + 1}"
        seen.add(field_id)
        label = str(item["label"]).strip() or field_id
        fields.append(BrowserField(field_id, index, label, bool(item["required"]), str(item["type"]), bool(_SENSITIVE.search(label))))
    return fields


def _profile_value_for_field(label: str, career: Any) -> str:
    """Return a safe deterministic profile value for common application labels."""
    normalized = label.casefold().strip()
    name = career.profile.name.strip()
    name_parts = name.split()
    if "first name" in normalized or "given name" in normalized:
        return name_parts[0] if name_parts else ""
    if "last name" in normalized or "family name" in normalized or "surname" in normalized:
        return " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    key = next((value for field_name, value in _PROFILE_FIELDS.items() if field_name in normalized), None)
    return str(getattr(career.profile, key, "")) if key else ""


def _is_greenhouse_application(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    return hostname == "greenhouse.io" or hostname.endswith(".greenhouse.io")


def _greenhouse_profile_values(profile: Any, location: str) -> dict[str, str]:
    """Map known facts to the current Greenhouse form identifiers."""
    name_parts = profile.name.split()
    location = unicodedata.normalize("NFKD", location).encode("ascii", "ignore").decode("ascii")
    country = location.rsplit(",", 1)[-1].strip() if "," in location else ""
    values = {
        "#first_name": name_parts[0] if name_parts else "",
        "#last_name": " ".join(name_parts[1:]),
        "#email": profile.email,
        "#phone": profile.phone,
        "#country": country,
        "#candidate-location": location,
        "#question_12689993007, input[name='question_12689993007']": profile.linkedin,
    }
    return {selector: value for selector, value in values.items() if value}


def _greenhouse_confirmed_answers(document: ApplicationDocument) -> dict[str, tuple[str, bool]]:
    """Return reviewed answers only for exact, known Greenhouse controls."""
    confirmed = {item.field_id: item for item in document.answers if item.confirmed_for_application}
    return {
        field_id: (confirmed[field_id].answer, is_combobox)
        for field_id, (_, is_combobox) in _GREENHOUSE_ANSWER_FIELDS.items()
        if field_id in confirmed
    }


def _resume_locale_for_job(job: Any, default_locale: str) -> str:
    return "en" if job.language.casefold() == "english" else default_locale


def _resume_attachment_for_job(project_path: Path, job: Any) -> Path:
    configuration = load_project_configuration(project_path)
    locale = _resume_locale_for_job(job, configuration.resume_language)
    path = project_path / "exports" / f"resume.{locale}.pdf"
    if path.is_file():
        return path
    return write_resume(
        project_path,
        load_localized_career(project_path, locale),
        locale,
        "pdf",
        style_id=configuration.resume_style,
    )


def _fill_greenhouse_combobox(page: Any, selector: str, value: str) -> bool:
    control = page.locator(selector)
    if not control.count():
        return False
    control.fill(value)
    control.press("ArrowDown")
    control.press("Enter")
    return True


def _fill_greenhouse_known(
    page: Any, fields: list[BrowserField], project_path: Path, document: ApplicationDocument, job: Any
) -> set[str]:
    configuration = load_project_configuration(project_path)
    locale = _resume_locale_for_job(job, configuration.resume_language)
    localized_career = load_localized_career(project_path, locale)
    selector_field_ids = {
        "#first_name": "first-name",
        "#last_name": "last-name",
        "#email": "email",
        "#phone": "phone",
        "#country": "country",
        "#candidate-location": "candidate-location",
        "#question_12689993007, input[name='question_12689993007']": "question-12689993007",
    }
    available = {field.field_id for field in fields}
    filled: set[str] = set()
    for selector, value in _greenhouse_profile_values(localized_career.profile, localized_career.profile.location).items():
        field_id = selector_field_ids[selector]
        if field_id not in available:
            continue
        if selector in {"#country", "#candidate-location"}:
            if _fill_greenhouse_combobox(page, selector, value):
                filled.add(field_id)
            continue
        control = page.locator(selector)
        if control.count():
            control.fill(value)
            filled.add(field_id)
    for field_id, (answer, is_combobox) in _greenhouse_confirmed_answers(document).items():
        if field_id not in available:
            continue
        selector, _ = _GREENHOUSE_ANSWER_FIELDS[field_id]
        control = page.locator(selector)
        if not control.count():
            continue
        control.fill(answer)
        if is_combobox:
            control.press("ArrowDown")
            control.press("Enter")
        filled.add(field_id)
    return filled


def _wait_for_form_controls(page: Any) -> None:
    """Wait for client-rendered application controls after initial navigation."""
    page.wait_for_selector(_FORM_CONTROLS, state="attached")
    page.wait_for_timeout(500)


def _launch_isolated_context(playwright: Any, project_path: Path, *, interactive: bool) -> tuple[Any, Path | None]:
    """Use a temporary project-local profile if a previous browser kept the main one locked."""
    profile = browser_profile_path(project_path)
    try:
        return playwright.chromium.launch_persistent_context(str(profile), headless=not interactive), None
    except Exception as error:
        if error.__class__.__name__ != "TargetClosedError":
            raise
        temporary_profile = Path(tempfile.mkdtemp(prefix="browser-recovery-", dir=project_path / ".seriemacv"))
        return (
            playwright.chromium.launch_persistent_context(str(temporary_profile), headless=not interactive),
            temporary_profile,
        )


def prepare_application(project_path: Path, application_id: str, *, interactive: bool = False, ai_assisted: bool = False) -> ApplicationDocument:
    """Open an isolated browser, fill safe known values, and queue unknown required fields."""
    document = load_application(project_path, application_id)
    if not document.url:
        raise ValueError("application URL is required for browser preparation")
    if document.status == "saved":
        document = update_status(project_path, application_id, "preparing")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:  # pragma: no cover
        raise ValueError("Playwright is required for browser preparation") from error
    with sync_playwright() as playwright:
        context, temporary_profile = _launch_isolated_context(playwright, project_path, interactive=interactive)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(document.url, wait_until="domcontentloaded")
            _wait_for_form_controls(page)
            job = load_job(project_path / "jobs" / f"{document.job_id}.yml")
            fields = discover_fields(page)
            greenhouse = _is_greenhouse_application(document.url)
            filled = (
                _fill_greenhouse_known(page, fields, project_path, document, job)
                if greenhouse else _fill_known(page, fields, project_path, document)
            )
            _attach_documents(page, fields, project_path, document, job=job, greenhouse=greenhouse)
            if interactive:
                input("Review the pre-filled safe fields and complete any login, then press Enter to inspect unresolved fields: ")
            _wait_for_form_controls(page)
            fields = discover_fields(page)
            filled.update(
                _fill_greenhouse_known(page, fields, project_path, document, job)
                if greenhouse else _fill_known(page, fields, project_path, document)
            )
            _attach_documents(page, fields, project_path, document, job=job, greenhouse=greenhouse)
            career = load_career(project_path / "career.yml")
            saved_answers = _saved_answers_for_job(career.answers, job.seniority, job.language)
            questions = _questions_for(
                fields, document, filled, include_optional=ai_assisted,
                include_optional_sensitive=not greenhouse,
                saved_answers=saved_answers,
            )
            replace_questions(project_path, application_id, questions)
            return load_application(project_path, application_id)
        finally:
            context.close()
            if temporary_profile is not None:
                shutil.rmtree(temporary_profile, ignore_errors=True)


def _fill_known(page: Any, fields: list[BrowserField], project_path: Path, document: ApplicationDocument) -> set[str]:
    career = load_career(project_path / "career.yml")
    used = {item.field_id: item for item in document.answers}
    filled: set[str] = set()
    for field in fields:
        if field.sensitive or field.input_type in {"file", "hidden", "submit", "checkbox", "radio"}:
            continue
        value = _profile_value_for_field(field.label, career)
        saved = used.get(field.field_id)
        if not value and saved and (not saved.sensitive or saved.confirmed_for_application):
            value = saved.answer
        if value:
            page.locator(_FORM_CONTROLS).nth(field.index).fill(value)
            filled.add(field.field_id)
    return filled


def _saved_answers_for_job(
    answers: list[SavedAnswer], seniority: str, language: str
) -> dict[str, tuple[str, list[str], bool]]:
    """Offer saved answers only for matching role and language scopes, for review."""
    normalized_seniority = seniority.casefold()
    normalized_language = _normalized_language_scope(language)
    return {
        item.prompt.casefold(): (item.answer, item.evidence_ids, item.sensitive)
        for item in answers
        if (not item.role_scope or normalized_seniority in item.role_scope)
        and (not item.language_scope or normalized_language in item.language_scope)
    }


def _normalized_language_scope(language: str) -> str:
    """Map a job's declared language to the stable answer-scope identifier."""
    normalized = language.strip().casefold()
    aliases = {
        "en": "en", "english": "en",
        "pt": "pt", "pt-br": "pt", "portuguese": "pt", "português": "pt",
    }
    return aliases.get(normalized, normalized)


def _attach_documents(
    page: Any,
    fields: list[BrowserField],
    project_path: Path,
    document: ApplicationDocument,
    *,
    job: Any | None = None,
    greenhouse: bool = False,
) -> None:
    if greenhouse and job is not None:
        resume = _resume_attachment_for_job(project_path, job)
        field = page.locator("input#resume, input[name='resume']").first
        if field.count():
            field.set_input_files([str(resume)])
        return
    upload_fields = [field for field in fields if field.input_type == "file"]
    if not upload_fields:
        return
    attachments = [project_path / path for path in document.attachments]
    if not attachments and document.variant_id:
        configuration = load_project_configuration(project_path)
        variant, career = load_variant_career(project_path, document.variant_id, configuration.resume_language)
        try:
            attachments = [write_resume(
                project_path, career, configuration.resume_language, "pdf",
                style_id=variant.style or configuration.resume_style,
                variant_id=document.variant_id,
            )]
        except ResumeRenderError:
            # The field remains visibly unresolved for the human reviewer when
            # Chromium is unavailable; do not replace it with another format.
            return
    if attachments:
        page.locator(_FORM_CONTROLS).nth(upload_fields[0].index).set_input_files([str(path) for path in attachments])


def _questions_for(
    fields: list[BrowserField],
    document: ApplicationDocument,
    filled: set[str],
    *,
    include_optional: bool = False,
    include_optional_sensitive: bool = True,
    saved_answers: dict[str, tuple[str, list[str], bool]] | None = None,
) -> list[ApplicationQuestion]:
    resolved = {item.field_id for item in document.answers} | filled
    result: list[ApplicationQuestion] = []
    for field in fields:
        if (
            (not field.required and not include_optional and (not field.sensitive or not include_optional_sensitive))
            or field.input_type in {"hidden", "submit", "file"}
            or field.field_id in resolved
        ):
            continue
        question_id = f"question-{field.field_id}"
        candidate = (saved_answers or {}).get(field.label.casefold())
        proposal = candidate if candidate and candidate[2] == field.sensitive else None
        result.append(ApplicationQuestion(
            id=question_id,
            field_id=field.field_id,
            label=field.label,
            context="Required field detected in the local browser session.",
            required=field.required,
            sensitive=field.sensitive,
            proposed_answer=proposal[0] if proposal else None,
            proposed_evidence_ids=proposal[1] if proposal else [],
        ))
    return result
