"""Generic, local Playwright preparation for a reviewed application."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from seriemacv.applications import (
    ApplicationDocument,
    ApplicationQuestion,
    add_questions,
    load_application,
    update_status,
)
from seriemacv.career import load_career
from seriemacv.project import load_project_configuration
from seriemacv.renderer import ResumeRenderError, write_resume
from seriemacv.variants import load_variant_career

_SENSITIVE = re.compile(r"salary|compensation|pay|legal|authorization|authori[sz]ation|visa|work permit|demographic|gender|race|ethnicity|disability|veteran|self.ident", re.I)
_PROFILE_FIELDS = {
    "name": "name", "full name": "name", "email": "email", "phone": "phone",
    "linkedin": "linkedin", "portfolio": "portfolio",
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
    raw = page.locator("input, select, textarea").evaluate_all("""elements => elements.map((element, index) => {
      const label = element.labels && element.labels.length ? element.labels[0].innerText :
        element.getAttribute('aria-label') || element.getAttribute('placeholder') || element.name || element.id || `field-${index + 1}`;
      return {id: element.id || element.name || `field-${index + 1}`, label, required: element.required || element.getAttribute('aria-required') === 'true', type: element.type || element.tagName.toLowerCase()};
    })""")
    fields: list[BrowserField] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        field_id = re.sub(r"[^a-z0-9]+", "-", str(item["id"]).lower()).strip("-") or "field"
        if field_id in seen:
            field_id = f"{field_id}-{len(seen) + 1}"
        seen.add(field_id)
        label = str(item["label"]).strip() or field_id
        fields.append(BrowserField(field_id, index, label, bool(item["required"]), str(item["type"]), bool(_SENSITIVE.search(label))))
    return fields


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
        context = playwright.chromium.launch_persistent_context(str(browser_profile_path(project_path)), headless=not interactive)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(document.url, wait_until="domcontentloaded")
            if interactive:
                input("Complete any login in the browser, then press Enter to inspect the form: ")
            fields = discover_fields(page)
            filled = _fill_known(page, fields, project_path, document)
            _attach_documents(page, fields, project_path, document)
            questions = _questions_for(fields, document, filled, include_optional=ai_assisted)
            if questions:
                add_questions(project_path, application_id, questions)
            elif document.status == "preparing":
                update_status(project_path, application_id, "ready_for_review")
            return load_application(project_path, application_id)
        finally:
            context.close()


def _fill_known(page: Any, fields: list[BrowserField], project_path: Path, document: ApplicationDocument) -> set[str]:
    career = load_career(project_path / "career.yml")
    used = {item.field_id: item for item in document.answers}
    saved_by_prompt = {item.prompt.casefold(): item for item in career.answers}
    filled: set[str] = set()
    for field in fields:
        if field.sensitive or field.input_type in {"file", "hidden", "submit", "checkbox", "radio"}:
            continue
        normalized = field.label.lower().strip()
        key = next((value for name, value in _PROFILE_FIELDS.items() if name in normalized), None)
        value = getattr(career.profile, key, "") if key else ""
        saved = used.get(field.field_id)
        reusable = saved_by_prompt.get(field.label.casefold())
        if not value and reusable and not reusable.sensitive:
            value = reusable.answer
        if not value and saved and (not saved.sensitive or saved.confirmed_for_application):
            value = saved.answer
        if value:
            page.locator("input, select, textarea").nth(field.index).fill(value)
            filled.add(field.field_id)
    return filled


def _attach_documents(page: Any, fields: list[BrowserField], project_path: Path, document: ApplicationDocument) -> None:
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
        page.locator("input, select, textarea").nth(upload_fields[0].index).set_input_files([str(path) for path in attachments])


def _questions_for(fields: list[BrowserField], document: ApplicationDocument, filled: set[str], *, include_optional: bool = False) -> list[ApplicationQuestion]:
    resolved = {item.field_id for item in document.answers} | filled
    existing = {item.field_id for item in document.questions}
    result: list[ApplicationQuestion] = []
    for field in fields:
        if (not field.required and not include_optional) or field.input_type in {"hidden", "submit", "file"} or field.field_id in resolved | existing:
            continue
        question_id = f"question-{field.field_id}"
        result.append(ApplicationQuestion(id=question_id, field_id=field.field_id, label=field.label, context="Required field detected in the local browser session.", required=True, sensitive=field.sensitive))
    return result
