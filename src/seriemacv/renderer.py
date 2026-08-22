"""Deterministic ATS-safe resume projections."""

from __future__ import annotations

import os
import tempfile
from html import escape
from importlib.resources import files
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict
from ruamel.yaml import YAML

from seriemacv.career import CareerDocument, Education, Experience, Skill
from seriemacv.i18n import Locale, translate

ResumeLocale = Literal["pt-BR", "en"]
ResumeFormat = Literal["markdown", "html", "pdf"]
_FILENAMES = {"markdown": "resume.md", "html": "resume.html", "pdf": "resume.pdf"}


class ResumeRenderError(ValueError):
    pass


class StyleManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1]
    id: Literal["clean"]
    layout: Literal["single-column"]
    page_size: Literal["A4"]
    supported_sections: list[str]


class PdfRenderer(Protocol):
    def render(self, html: str) -> bytes: ...


class PlaywrightPdfRenderer:
    def render(self, html: str) -> bytes:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page()
                    page.set_content(html, wait_until="load")
                    return page.pdf(
                        format="A4", print_background=True, prefer_css_page_size=True
                    )
                finally:
                    browser.close()
        except Exception as error:
            raise ResumeRenderError(
                "PDF rendering requires Chromium; run 'python -m playwright install chromium'"
            ) from error


def render_markdown(career: CareerDocument, locale: ResumeLocale) -> str:
    labels = _labels(locale)
    profile = career.profile
    blocks = [f"# {profile.name}", profile.title]
    contact = [x for x in (profile.location, profile.email, profile.phone) if x]
    if contact:
        blocks.append(" | ".join(contact))
    links = {**profile.links}
    if profile.linkedin:
        links.setdefault("LinkedIn", profile.linkedin)
    if profile.portfolio:
        links.setdefault("Portfolio", profile.portfolio)
    blocks.extend(f"{name}: {url}" for name, url in links.items())
    if career.summary:
        blocks.append(_md_section(labels["summary"], career.summary))
    if career.experience:
        blocks.append(
            _md_records(labels["experience"], _ordered(career.experience), labels, True)
        )
    if career.education:
        blocks.append(
            _md_records(labels["education"], _ordered(career.education), labels, False)
        )
    if career.skills:
        blocks.append(
            _md_section(labels["skills"], _markdown_skills(career.skills, labels))
        )
    if profile.languages:
        blocks.append(
            _md_section(
                labels["languages"], "\n".join(f"- {x}" for x in profile.languages)
            )
        )
    return "\n\n".join(x for x in blocks if x) + "\n"


def render_html(career: CareerDocument, locale: ResumeLocale) -> str:
    labels = _labels(locale)
    profile = career.profile
    manifest, template, css = _assets()
    contact = " · ".join(
        escape(x) for x in (profile.location, profile.email, profile.phone) if x
    )
    profile_links = {**profile.links}
    if profile.linkedin:
        profile_links.setdefault("LinkedIn", profile.linkedin)
    if profile.portfolio:
        profile_links.setdefault("Portfolio", profile.portfolio)
    links = " ".join(
        f'<a href="{escape(url, quote=True)}">{escape(name)}</a>'
        for name, url in profile_links.items()
    )
    sections = []
    if career.summary:
        sections.append(
            _html_section(labels["summary"], f"<p>{escape(career.summary)}</p>")
        )
    if career.experience:
        sections.append(
            _html_records(
                labels["experience"], _ordered(career.experience), labels, True
            )
        )
    if career.education:
        sections.append(
            _html_records(
                labels["education"], _ordered(career.education), labels, False
            )
        )
    if career.skills:
        sections.append(
            _html_section(labels["skills"], _html_skills(career.skills, labels))
        )
    if profile.languages:
        sections.append(
            _html_section(labels["languages"], _html_list(profile.languages))
        )
    header = f'<header><h1>{escape(profile.name)}</h1><p class="title">{escape(profile.title)}</p><p>{contact}</p><p>{links}</p></header>'
    return (
        template.replace("{{title}}", escape(profile.name))
        .replace("{{css}}", css)
        .replace("{{body}}", header + "".join(sections))
        .replace("{{style_id}}", manifest.id)
    )


def write_resume(
    project_path: Path,
    career: CareerDocument,
    locale: ResumeLocale,
    output_format: ResumeFormat,
    pdf_renderer: PdfRenderer | None = None,
) -> Path:
    path = project_path / "exports" / _FILENAMES[output_format]
    path.parent.mkdir(parents=True, exist_ok=True)
    content: bytes
    if output_format == "markdown":
        content = render_markdown(career, locale).encode()
    elif output_format == "html":
        content = render_html(career, locale).encode()
    else:
        content = (pdf_renderer or PlaywrightPdfRenderer()).render(
            render_html(career, locale)
        )
    _atomic_write(path, content)
    return path


def write_markdown_resume(
    project_path: Path, career: CareerDocument, locale: ResumeLocale
) -> Path:
    return write_resume(project_path, career, locale, "markdown")


def _assets() -> tuple[StyleManifest, str, str]:
    root = files("seriemacv").joinpath("assets", "clean")
    return (
        StyleManifest.model_validate(
            YAML(typ="safe").load(root.joinpath("style.yml").read_text())
        ),
        root.joinpath("template.html").read_text(),
        root.joinpath("print.css").read_text(),
    )


def _labels(locale: str) -> dict[str, str]:
    if locale not in {"pt-BR", "en"}:
        raise ValueError(f"Unsupported resume locale: {locale}")
    return {
        key: translate(locale, key)
        for key in (
            "summary",
            "experience",
            "education",
            "skills",
            "languages",
            "current",
            "other",
        )
    }


def _ordered(
    records: list[Experience] | list[Education],
) -> list[Experience] | list[Education]:
    return sorted(
        records,
        key=lambda x: (x.end_date is None, x.end_date or "", x.start_date),
        reverse=True,
    )


def _details(
    record: Experience | Education, labels: dict[str, str], experience: bool
) -> str:
    values = (
        [record.location] if experience else [record.field_of_study, record.location]
    )
    if experience and record.employment_type:
        values.append(record.employment_type)
    end = (
        _format_date(record.end_date, labels) if record.end_date else labels["current"]
    )
    values.append(f"{_format_date(record.start_date, labels)} — {end}")
    return " | ".join(x for x in values if x)


def _md_section(title: str, content: str) -> str:
    return f"## {title}\n\n{content}"


def _markdown_skills(skills: list[Skill], labels: dict[str, str]) -> str:
    return "\n\n".join(
        (f"**{category}:** " if category else "")
        + ", ".join(_markdown_skill(skill, labels) for skill in items)
        for category, items in _skill_groups(skills, labels).items()
    )


def _markdown_skill(skill: Skill, labels: dict[str, str]) -> str:
    name = f"**{skill.name}**" if skill.core else skill.name
    return name + (
        f" ({translate(_locale_for(labels), f'level.{skill.level}')})"
        if skill.level
        else ""
    )


def _html_skills(skills: list[Skill], labels: dict[str, str]) -> str:
    groups = []
    for category, items in _skill_groups(skills, labels).items():
        values = []
        for skill in items:
            name = (
                f"<strong>{escape(skill.name)}</strong>"
                if skill.core
                else escape(skill.name)
            )
            level = (
                translate(_locale_for(labels), f"level.{skill.level}")
                if skill.level
                else ""
            )
            values.append(name + (f" ({escape(level)})" if level else ""))
        groups.append(
            f"<p>{f'<strong>{escape(category)}:</strong> ' if category else ''}{', '.join(values)}</p>"
        )
    return "".join(groups)


def _skill_groups(
    skills: list[Skill], labels: dict[str, str]
) -> dict[str, list[Skill]]:
    groups: dict[str, list[Skill]] = {}
    has_category = any(skill.category for skill in skills)
    for skill in skills:
        category = skill.category or (labels["other"] if has_category else "")
        groups.setdefault(category, []).append(skill)
    return groups


def _locale_for(labels: dict[str, str]) -> Locale:
    return "pt-BR" if labels["current"] == "Atual" else "en"


def _format_date(value: str, labels: dict[str, str]) -> str:
    year, month = value.split("-")
    is_portuguese = labels["current"] == "Atual"
    names = (
        (
            "Jan.",
            "Fev.",
            "Mar.",
            "Abr.",
            "Mai.",
            "Jun.",
            "Jul.",
            "Ago.",
            "Set.",
            "Out.",
            "Nov.",
            "Dez.",
        )
        if is_portuguese
        else (
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        )
    )
    name = names[int(month) - 1]
    return f"{name} de {year}" if is_portuguese else f"{name} {year}"


def _md_records(
    title: str,
    records: list[Experience] | list[Education],
    labels: dict[str, str],
    experience: bool,
) -> str:
    values = []
    for x in records:
        heading = (
            f"{x.title} — {x.company}"
            if experience
            else f"{x.degree} — {x.institution}"
        )
        values.append(
            "\n".join(
                [
                    f"### {heading}",
                    _details(x, labels, experience),
                    *[f"- {h}" for h in x.highlights],
                ]
            )
        )
    return _md_section(title, "\n\n".join(values))


def _html_list(values: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{escape(x)}</li>" for x in values) + "</ul>"


def _html_section(title: str, content: str) -> str:
    return f"<section><h2>{escape(title)}</h2>{content}</section>"


def _html_records(
    title: str,
    records: list[Experience] | list[Education],
    labels: dict[str, str],
    experience: bool,
) -> str:
    articles = []
    for x in records:
        heading = (
            f"{x.title} — {x.company}"
            if experience
            else f"{x.degree} — {x.institution}"
        )
        articles.append(
            f"<article><h3>{escape(heading)}</h3><p>{escape(_details(x, labels, experience))}</p>{_html_list(x.highlights) if x.highlights else ''}</article>"
        )
    return _html_section(title, "".join(articles))


def _atomic_write(path: Path, content: bytes) -> None:
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(content)
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise
