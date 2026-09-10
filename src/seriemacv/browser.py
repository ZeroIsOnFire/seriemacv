"""Generic, local Playwright preparation for a reviewed application."""

from __future__ import annotations

import re
import shutil
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from seriemacv.applications import (
    ApplicationDocument,
    ApplicationQuestion,
    configure_application,
    create_application,
    list_applications,
    load_application,
    replace_questions,
    update_status,
)
from seriemacv.career import SavedAnswer, load_career, load_localized_career
from seriemacv.jobs import load_job
from seriemacv.operations import record_browser_call
from seriemacv.project import load_project_configuration
from seriemacv.renderer import write_resume
from seriemacv.variants import list_variants, load_variant, load_variant_career

_SENSITIVE = re.compile(
    r"salary|compensation|pay|legal|authori[sz](ation|ed)|visa|sponsor(ship)?|work permit|sole proprietor|invoice|demographic|gender|race|ethnicity|disability|veteran|self.ident",
    re.I,
)
_PROFILE_FIELDS = {
    "full name": "name",
    "email": "email",
    "phone": "phone",
    "linkedin": "linkedin",
    "portfolio": "portfolio",
    "github": "portfolio",
}
_FORM_CONTROLS = "input, select, textarea"
_TEXT_INPUT_TYPES = {"text", "email", "tel", "url", "textarea"}
_COMBOBOX_TIMEOUT_MS = 2_000
_GREENHOUSE_ANSWER_FIELDS = {
    "question-12689994007": (
        "#question_12689994007, textarea[name='question_12689994007']",
        False,
    ),
    "question-12689995007": (
        "#question_12689995007, textarea[name='question_12689995007']",
        False,
    ),
    "question-12689996007": (
        "#question_12689996007, textarea[name='question_12689996007']",
        False,
    ),
    "question-12689997007": (
        "#question_12689997007, input[name='question_12689997007']",
        True,
    ),
    "question-12689998007": (
        "#question_12689998007, input[name='question_12689998007']",
        True,
    ),
    "question-12690000007": (
        "#question_12690000007, input[name='question_12690000007']",
        True,
    ),
    "question-12690001007": (
        "#question_12690001007, input[name='question_12690001007']",
        True,
    ),
}


@dataclass(frozen=True)
class BrowserField:
    field_id: str
    index: int
    label: str
    required: bool
    input_type: str
    sensitive: bool
    options: tuple[str, ...] = ()
    populated: bool = False


def browser_profile_path(project_path: Path) -> Path:
    return project_path / ".seriemacv" / "browser"


def clear_browser_profile(project_path: Path) -> None:
    profile = browser_profile_path(project_path)
    if profile.exists():
        shutil.rmtree(profile)


def discover_fields(page: Any) -> list[BrowserField]:
    """Inspect generic form controls without retaining their values."""
    raw = page.locator(_FORM_CONTROLS).evaluate_all("""elements => elements.map((element, index) => {
      const optionLabel = element.labels && element.labels.length ? element.labels[0].innerText :
        element.getAttribute('aria-label') || element.getAttribute('placeholder') ||
        (element.type === 'checkbox' ? element.parentElement?.innerText : '') ||
        element.name || element.id || `field-${index + 1}`;
      const container = element.closest('fieldset, .application-question, .application-row, [role="group"]');
      const groupLabel = container?.querySelector('legend, .application-label, [data-qa$="-label"]')?.innerText || '';
      return {
        index,
        id: element.id || element.name || `field-${index + 1}`,
        name: element.name || '',
        label: optionLabel,
        groupLabel,
        required: element.required || element.getAttribute('aria-required') === 'true',
        type: element.type || element.tagName.toLowerCase(),
        hidden: element.type === 'hidden' || element.getAttribute('aria-hidden') === 'true',
        populated: ['radio', 'checkbox'].includes(element.type) ? element.checked : Boolean(element.value)
      };
    })""")
    fields: list[BrowserField] = []
    seen: set[str] = set()
    grouped: dict[tuple[str, str], int] = {}
    group_counts: dict[tuple[str, str], int] = {}
    for item in raw:
        input_type = str(item["type"])
        name = str(item.get("name", ""))
        if not item.get("hidden") and name and input_type in {"radio", "checkbox"}:
            key = (input_type, name)
            group_counts[key] = group_counts.get(key, 0) + 1
    for raw_index, item in enumerate(raw):
        if item.get("hidden"):
            continue
        input_type = str(item["type"])
        name = str(item.get("name", ""))
        group_key = (input_type, name)
        is_group = input_type == "radio" or group_counts.get(group_key, 0) > 1
        option = str(item["label"]).strip()
        if is_group and name and group_key in grouped:
            position = grouped[group_key]
            current = fields[position]
            fields[position] = BrowserField(
                current.field_id,
                current.index,
                current.label,
                current.required or bool(item["required"]),
                current.input_type,
                current.sensitive or bool(_SENSITIVE.search(option)),
                (*current.options, option)
                if option not in current.options
                else current.options,
                current.populated or bool(item.get("populated")),
            )
            continue
        identifier = name if is_group and name else str(item["id"])
        field_id = re.sub(r"[^a-z0-9]+", "-", identifier.lower()).strip("-") or "field"
        if field_id in seen:
            field_id = f"{field_id}-{len(seen) + 1}"
        seen.add(field_id)
        label = str(item.get("groupLabel", "")).strip() if is_group else option
        label = label or (name if is_group else option) or field_id
        fields.append(
            BrowserField(
                field_id,
                int(item.get("index", raw_index)),
                label,
                bool(item["required"]),
                input_type,
                bool(_SENSITIVE.search(" ".join((label, option)))),
                (option,) if is_group and option else (),
                bool(item.get("populated")),
            )
        )
        if is_group and name:
            grouped[group_key] = len(fields) - 1
    return fields


def _profile_value_for_field(label: str, career: Any) -> str:
    """Return a safe deterministic profile value for common application labels."""
    normalized = label.casefold().strip()
    name = career.profile.name.strip()
    name_parts = name.split()
    if "first name" in normalized or "given name" in normalized:
        return name_parts[0] if name_parts else ""
    if (
        "last name" in normalized
        or "family name" in normalized
        or "surname" in normalized
    ):
        return " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    key = next(
        (
            value
            for field_name, value in _PROFILE_FIELDS.items()
            if field_name in normalized
        ),
        None,
    )
    return str(getattr(career.profile, key, "")) if key else ""


def _is_greenhouse_application(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    return hostname == "greenhouse.io" or hostname.endswith(".greenhouse.io")


def _greenhouse_profile_values(profile: Any, location: str) -> dict[str, str]:
    """Map known facts to the current Greenhouse form identifiers."""
    name_parts = profile.name.split()
    location = (
        unicodedata.normalize("NFKD", location)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
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


def _greenhouse_confirmed_answers(
    document: ApplicationDocument,
) -> dict[str, tuple[str, bool]]:
    """Return reviewed answers only for exact, known Greenhouse controls."""
    confirmed = {
        item.field_id: item
        for item in document.answers
        if item.confirmed_for_application
    }
    return {
        field_id: (confirmed[field_id].answer, is_combobox)
        for field_id, (_, is_combobox) in _GREENHOUSE_ANSWER_FIELDS.items()
        if field_id in confirmed
    }


def _resume_locale_for_job(job: Any, default_locale: str) -> str:
    return "en" if job.language.casefold() == "english" else default_locale


def _fill_greenhouse_combobox(
    page: Any,
    selector: str,
    value: str,
    *,
    failed: set[str],
    failure_key: str,
) -> bool:
    if failure_key in failed:
        return False
    control = page.locator(selector)
    if not control.count():
        failed.add(failure_key)
        return False
    try:
        control.fill(value, timeout=_COMBOBOX_TIMEOUT_MS)
        record_browser_call("fill")
        listbox_id = control.get_attribute("aria-controls") or control.get_attribute(
            "aria-owns"
        )
        option_selector = "[role='listbox']:visible [role='option']"
        if listbox_id and re.fullmatch(r"[A-Za-z0-9_-]+", listbox_id):
            option_selector = f"#{listbox_id} [role='option']:visible"
        page.wait_for_selector(
            option_selector, state="visible", timeout=_COMBOBOX_TIMEOUT_MS
        )
        options = page.locator(option_selector)
        expected = " ".join(value.split()).casefold()
        matches = [
            index
            for index, label in enumerate(options.all_inner_texts())
            if " ".join(label.split()).casefold() == expected
        ]
        if len(matches) != 1:
            control.fill("", timeout=_COMBOBOX_TIMEOUT_MS)
            record_browser_call("fill")
            failed.add(failure_key)
            return False
        options.nth(matches[0]).click(timeout=_COMBOBOX_TIMEOUT_MS)
        selected = " ".join(control.input_value().split()).casefold()
        if selected != expected:
            control.fill("", timeout=_COMBOBOX_TIMEOUT_MS)
            record_browser_call("fill")
            failed.add(failure_key)
            return False
        return True
    except Exception as error:
        if error.__class__.__name__ != "TimeoutError":
            raise
        failed.add(failure_key)
        return False


def _fill_greenhouse_known(
    page: Any,
    fields: list[BrowserField],
    project_path: Path,
    document: ApplicationDocument,
    job: Any,
    failed_comboboxes: set[str],
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
    for selector, value in _greenhouse_profile_values(
        localized_career.profile, localized_career.profile.location
    ).items():
        field_id = selector_field_ids[selector]
        if field_id not in available:
            continue
        if selector in {"#country", "#candidate-location"}:
            if _fill_greenhouse_combobox(
                page,
                selector,
                value,
                failed=failed_comboboxes,
                failure_key=field_id,
            ):
                filled.add(field_id)
            continue
        control = page.locator(selector)
        if control.count():
            control.fill(value)
            record_browser_call("fill")
            filled.add(field_id)
    for field_id, (answer, is_combobox) in _greenhouse_confirmed_answers(
        document
    ).items():
        if field_id not in available:
            continue
        selector, _ = _GREENHOUSE_ANSWER_FIELDS[field_id]
        if is_combobox:
            if _fill_greenhouse_combobox(
                page,
                selector,
                answer,
                failed=failed_comboboxes,
                failure_key=field_id,
            ):
                filled.add(field_id)
            continue
        control = page.locator(selector)
        if not control.count():
            continue
        control.fill(answer)
        record_browser_call("fill")
        filled.add(field_id)
    return filled


def _wait_for_form_controls(page: Any) -> None:
    """Wait for client-rendered application controls after initial navigation."""
    page.wait_for_selector(_FORM_CONTROLS, state="attached")
    page.wait_for_timeout(500)


def _launch_isolated_context(
    playwright: Any, project_path: Path, *, interactive: bool
) -> tuple[Any, Path | None]:
    """Use a temporary project-local profile if a previous browser kept the main one locked."""
    profile = browser_profile_path(project_path)
    try:
        return playwright.chromium.launch_persistent_context(
            str(profile), headless=not interactive
        ), None
    except Exception as error:
        if error.__class__.__name__ != "TargetClosedError":
            raise
        temporary_profile = Path(
            tempfile.mkdtemp(
                prefix="browser-recovery-", dir=project_path / ".seriemacv"
            )
        )
        return (
            playwright.chromium.launch_persistent_context(
                str(temporary_profile), headless=not interactive
            ),
            temporary_profile,
        )


def _inspect_application_page(page: Any) -> list[BrowserField]:
    _wait_for_form_controls(page)
    record_browser_call("inspection")
    return discover_fields(page)


def _fill_and_persist_application_page(
    page: Any,
    project_path: Path,
    document: ApplicationDocument,
    job: Any,
    *,
    failed_comboboxes: set[str],
    persisted: Callable[[list[BrowserField], set[str]], None],
) -> tuple[list[BrowserField], set[str]]:
    fields = _inspect_application_page(page)
    greenhouse = _is_greenhouse_application(document.url)
    filled = (
        _fill_greenhouse_known(
            page,
            fields,
            project_path,
            document,
            job,
            failed_comboboxes,
        )
        if greenhouse
        else _fill_known(page, fields, project_path, document)
    )
    persisted(fields, filled)
    _attach_documents(
        page, fields, project_path, document, job=job, greenhouse=greenhouse
    )
    return fields, filled


def _interactive_browser_session(refill: Any, inspect: Any) -> None:
    """Keep one browser window controllable through its owning CLI process."""
    print("Browser session ready. Commands: refill, inspect, close.")
    while True:
        command = input("browser> ").strip().casefold()
        if command in {"close", "done", "exit", "finish"}:
            return
        if command in {"refill", "fill"}:
            refill()
            print("Known fields and attachments were filled again.")
            continue
        if command in {"", "inspect", "review"}:
            fields, filled = inspect()
            unresolved = sum(
                field.required
                and field.field_id not in filled
                and not field.populated
                and field.input_type not in {"hidden", "submit", "file"}
                for field in fields
            )
            print(f"Form inspected. Unresolved required controls: {unresolved}.")
            continue
        print("Unknown command. Use refill, inspect, or close.")


def prepare_application(
    project_path: Path,
    application_id: str,
    *,
    interactive: bool = False,
    ai_assisted: bool = False,
) -> ApplicationDocument:
    """Open an isolated browser, fill safe known values, and queue unknown required fields."""
    document = load_application(project_path, application_id)
    if not document.url:
        raise ValueError("application URL is required for browser preparation")
    job = load_job(project_path / "jobs" / f"{document.job_id}.yml")
    document = _prepare_resume_attachment(project_path, document, job)
    if document.status == "saved":
        document = update_status(project_path, application_id, "preparing")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:  # pragma: no cover
        raise ValueError("Playwright is required for browser preparation") from error
    with sync_playwright() as playwright:
        context, temporary_profile = _launch_isolated_context(
            playwright, project_path, interactive=interactive
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            record_browser_call("navigation")
            page.goto(document.url, wait_until="domcontentloaded")
            career = load_career(project_path / "career.yml")
            saved_answers = _saved_answers_for_job(
                career.answers, job.seniority, job.language
            )
            failed_comboboxes: set[str] = set()

            def persist(fields: list[BrowserField], filled: set[str]) -> None:
                current = load_application(project_path, application_id)
                questions = _questions_for(
                    fields,
                    current,
                    filled,
                    include_optional=ai_assisted,
                    include_optional_sensitive=not _is_greenhouse_application(
                        current.url
                    ),
                    saved_answers=saved_answers,
                )
                replace_questions(project_path, application_id, questions)

            def refill() -> tuple[list[BrowserField], set[str]]:
                current = load_application(project_path, application_id)
                return _fill_and_persist_application_page(
                    page,
                    project_path,
                    current,
                    job,
                    failed_comboboxes=failed_comboboxes,
                    persisted=persist,
                )

            def inspect() -> tuple[list[BrowserField], set[str]]:
                fields = _inspect_application_page(page)
                persist(fields, set())
                return fields, set()

            refill()
            if interactive:
                _interactive_browser_session(refill, inspect)
                if not page.is_closed():
                    inspect()
            return load_application(project_path, application_id)
        finally:
            try:
                context.close()
            except Exception as error:
                if error.__class__.__name__ != "TargetClosedError":
                    raise
            if temporary_profile is not None:
                shutil.rmtree(temporary_profile, ignore_errors=True)


def prepare_job_application(
    project_path: Path,
    job_id: str,
    *,
    application_id: str | None = None,
    url: str = "",
    variant_id: str | None = None,
    interactive: bool = False,
    ai_assisted: bool = False,
) -> ApplicationDocument:
    """Resolve assets and prepare the unique application associated with a job."""
    job = load_job(project_path / "jobs" / f"{job_id}.yml")
    matches = [
        item for item in list_applications(project_path) if item.job_id == job_id
    ]
    if application_id:
        selected = next((item for item in matches if item.id == application_id), None)
        if selected is None and matches:
            raise ValueError("application id does not match the selected job")
    elif len(matches) > 1:
        raise ValueError(
            "multiple applications exist for this job; provide --application-id"
        )
    else:
        selected = matches[0] if matches else None

    if selected is not None and selected.status in {
        "applied",
        "recruiter",
        "interview",
        "offer",
        "rejected",
        "withdrawn",
    }:
        raise ValueError(
            f"application is already in terminal workflow state: {selected.status}"
        )

    chosen_variant = variant_id or (selected.variant_id if selected else None)
    if chosen_variant is None:
        candidates = [
            item.id for item in list_variants(project_path) if item.job_id == job_id
        ]
        if len(candidates) > 1:
            raise ValueError(
                "multiple variants exist for this job; provide --variant-id"
            )
        chosen_variant = candidates[0] if candidates else None
    if chosen_variant is not None:
        variant = load_variant(project_path, chosen_variant)
        if variant.job_id not in {None, job_id}:
            raise ValueError("variant does not belong to the selected job")

    if selected is None:
        if not url:
            raise ValueError("--url is required when creating a job application")
        identifier = application_id or f"{job_id}-application"
        create_application(
            project_path,
            ApplicationDocument(
                id=identifier,
                job_id=job_id,
                variant_id=chosen_variant,
                url=url,
            ),
        )
        selected = load_application(project_path, identifier)
    else:
        if url and selected.url and url != selected.url:
            raise ValueError("application already has a different URL")
        if variant_id and selected.variant_id and variant_id != selected.variant_id:
            raise ValueError("application already uses a different variant")
        selected = configure_application(
            project_path,
            selected.id,
            url=url or None,
            variant_id=chosen_variant if selected.variant_id is None else None,
        )

    selected = _prepare_resume_attachment(project_path, selected, job)

    return prepare_application(
        project_path,
        selected.id,
        interactive=interactive,
        ai_assisted=ai_assisted,
    )


def _fill_known(
    page: Any,
    fields: list[BrowserField],
    project_path: Path,
    document: ApplicationDocument,
) -> set[str]:
    career = load_career(project_path / "career.yml")
    used = {item.field_id: item for item in document.answers}
    filled: set[str] = set()
    for field in fields:
        if field.sensitive or field.input_type in {
            "file",
            "hidden",
            "submit",
            "checkbox",
            "radio",
        }:
            continue
        value = _profile_value_for_field(field.label, career)
        saved = used.get(field.field_id)
        if (
            not value
            and saved
            and (not saved.sensitive or saved.confirmed_for_application)
        ):
            value = saved.answer
        if value:
            page.locator(_FORM_CONTROLS).nth(field.index).fill(value)
            record_browser_call("fill")
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
        "en": "en",
        "english": "en",
        "pt": "pt",
        "pt-br": "pt",
        "portuguese": "pt",
        "português": "pt",
    }
    return aliases.get(normalized, normalized)


def _prepare_resume_attachment(
    project_path: Path,
    document: ApplicationDocument,
    job: Any,
) -> ApplicationDocument:
    """Resolve a reusable PDF before entering a Playwright browser session."""
    existing = [
        project_path / relative_path
        for relative_path in document.attachments
        if Path(relative_path).suffix.casefold() == ".pdf"
        and (project_path / relative_path).is_file()
    ]
    if existing:
        return document

    configuration = load_project_configuration(project_path)
    locale = _resume_locale_for_job(job, configuration.resume_language)
    if document.variant_id:
        variant, career = load_variant_career(project_path, document.variant_id, locale)
        style_id = variant.style or configuration.resume_style
    else:
        career = load_localized_career(project_path, locale)
        style_id = configuration.resume_style
    resume = write_resume(
        project_path,
        career,
        locale,
        "pdf",
        style_id=style_id,
        resume_color=configuration.resume_color,
        variant_id=document.variant_id,
    )
    relative_resume = resume.relative_to(project_path).as_posix()
    attachments = [*document.attachments]
    if relative_resume not in attachments:
        attachments.append(relative_resume)
    return configure_application(project_path, document.id, attachments=attachments)


def _attach_documents(
    page: Any,
    fields: list[BrowserField],
    project_path: Path,
    document: ApplicationDocument,
    *,
    job: Any | None = None,
    greenhouse: bool = False,
) -> None:
    attachments = [
        project_path / path
        for path in document.attachments
        if (project_path / path).is_file()
    ]
    if greenhouse:
        resume = next(
            (path for path in attachments if path.suffix.casefold() == ".pdf"), None
        )
        if resume is None:
            return
        field = page.locator("input#resume, input[name='resume']").first
        if field.count():
            field.set_input_files([str(resume)])
            record_browser_call("upload")
        return
    upload_fields = [field for field in fields if field.input_type == "file"]
    if not upload_fields:
        return
    if attachments:
        page.locator(_FORM_CONTROLS).nth(upload_fields[0].index).set_input_files(
            [str(path) for path in attachments]
        )
        record_browser_call("upload")


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
            (
                not field.required
                and not include_optional
                and (not field.sensitive or not include_optional_sensitive)
            )
            or field.input_type in {"hidden", "submit", "file"}
            or field.field_id in resolved
            or field.populated
        ):
            continue
        question_id = f"question-{field.field_id}"
        candidate = (saved_answers or {}).get(field.label.casefold())
        proposal = candidate if candidate and candidate[2] == field.sensitive else None
        result.append(
            ApplicationQuestion(
                id=question_id,
                field_id=field.field_id,
                label=field.label,
                context="Required field detected in the local browser session.",
                required=field.required,
                sensitive=field.sensitive,
                options=list(field.options),
                proposed_answer=proposal[0] if proposal else None,
                proposed_evidence_ids=proposal[1] if proposal else [],
            )
        )
    return result
