"""Deterministic ATS-safe resume projections."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from html import escape
from importlib.resources import files
from io import BytesIO
from pathlib import Path
from typing import Literal, Protocol

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt
from pydantic import BaseModel, ConfigDict
from ruamel.yaml import YAML

from seriemacv.career import CareerDocument, Education, Experience, Skill
from seriemacv.i18n import Locale, translate

ResumeLocale = Literal["pt-BR", "en"]
ResumeFormat = Literal["markdown", "html", "pdf", "docx"]
_FILENAMES = {
    "markdown": "resume.md",
    "html": "resume.html",
    "pdf": "resume.pdf",
    "docx": "resume.docx",
}


class ResumeRenderError(ValueError):
    pass


class StyleManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1]
    id: Literal["clean"]
    layout: Literal["single-column"]
    page_size: Literal["A4"]
    supported_sections: list[str]


@dataclass(frozen=True)
class ResumePresentation:
    career: CareerDocument
    labels: dict[str, str]
    contacts: tuple[str, ...]
    links: tuple[tuple[str, str], ...]
    experience: list[Experience]
    education: list[Education]


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
    presentation = _presentation(career, locale)
    labels = presentation.labels
    profile = presentation.career.profile
    blocks = [f"# {profile.name}", profile.title]
    if presentation.contacts:
        blocks.append(" | ".join(presentation.contacts))
    blocks.extend(f"{name}: {url}" for name, url in presentation.links)
    if career.summary:
        blocks.append(_md_section(labels["summary"], career.summary))
    if presentation.experience:
        blocks.append(
            _md_records(labels["experience"], presentation.experience, labels, True)
        )
    if presentation.education:
        blocks.append(
            _md_records(labels["education"], presentation.education, labels, False)
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
    presentation = _presentation(career, locale)
    labels = presentation.labels
    profile = presentation.career.profile
    manifest, template, css = _assets()
    contact = " | ".join(escape(item) for item in presentation.contacts)
    links = " ".join(
        f'<a href="{escape(url, quote=True)}">{escape(name)}</a>'
        for name, url in presentation.links
    )
    sections = []
    if career.summary:
        sections.append(
            _html_section(labels["summary"], f"<p>{escape(career.summary)}</p>")
        )
    if presentation.experience:
        sections.append(
            _html_records(
                labels["experience"], presentation.experience, labels, True
            )
        )
    if presentation.education:
        sections.append(
            _html_records(
                labels["education"], presentation.education, labels, False
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


def render_docx(career: CareerDocument, locale: ResumeLocale) -> bytes:
    presentation = _presentation(career, locale)
    document = Document()
    _configure_docx(document)
    profile = presentation.career.profile

    name = document.add_paragraph()
    name.paragraph_format.space_after = Pt(2)
    name_run = name.add_run(profile.name)
    name_run.bold = True
    name_run.font.size = Pt(22)

    title = document.add_paragraph(profile.title)
    title.paragraph_format.space_after = Pt(2)
    if presentation.contacts:
        document.add_paragraph(" | ".join(presentation.contacts))
    for label, url in presentation.links:
        document.add_paragraph(f"{label}: {url}")

    if career.summary:
        _docx_section(document, presentation.labels["summary"])
        document.add_paragraph(career.summary)
    if presentation.experience:
        _docx_records(
            document,
            presentation.labels["experience"],
            presentation.experience,
            presentation.labels,
            True,
        )
    if presentation.education:
        _docx_records(
            document,
            presentation.labels["education"],
            presentation.education,
            presentation.labels,
            False,
        )
    if career.skills:
        _docx_section(document, presentation.labels["skills"])
        for category, skills in _skill_groups(career.skills, presentation.labels).items():
            paragraph = document.add_paragraph()
            if category:
                category_run = paragraph.add_run(f"{category}: ")
                category_run.bold = True
            for index, skill in enumerate(skills):
                if index:
                    paragraph.add_run(", ")
                skill_run = paragraph.add_run(skill.name)
                skill_run.bold = skill.core
                if skill.level:
                    paragraph.add_run(
                        f" ({translate(_locale_for(presentation.labels), f'level.{skill.level}')})"
                    )
    if profile.languages:
        _docx_section(document, presentation.labels["languages"])
        document.add_paragraph(" | ".join(profile.languages))

    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


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
    elif output_format == "pdf":
        content = (pdf_renderer or PlaywrightPdfRenderer()).render(
            render_html(career, locale)
        )
    else:
        content = render_docx(career, locale)
    _atomic_write(path, content)
    return path


def write_markdown_resume(
    project_path: Path, career: CareerDocument, locale: ResumeLocale
) -> Path:
    return write_resume(project_path, career, locale, "markdown")


def _presentation(career: CareerDocument, locale: ResumeLocale) -> ResumePresentation:
    profile = career.profile
    links = {**profile.links}
    if profile.linkedin:
        links.setdefault("LinkedIn", profile.linkedin)
    if profile.portfolio:
        links.setdefault("Portfolio", profile.portfolio)
    return ResumePresentation(
        career=career,
        labels=_labels(locale),
        contacts=tuple(
            item for item in (profile.location, profile.email, profile.phone) if item
        ),
        links=tuple(links.items()),
        experience=list(_ordered(career.experience)),
        education=list(_ordered(career.education)),
    )


def _configure_docx(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(16)
    section.bottom_margin = Mm(16)
    section.left_margin = Mm(16)
    section.right_margin = Mm(16)
    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10)
    normal.paragraph_format.line_spacing = 1.35
    normal.paragraph_format.space_after = Pt(0)
    heading = document.styles.add_style("Resume Heading", WD_STYLE_TYPE.PARAGRAPH)
    heading.font.name = "Arial"
    heading.font.size = Pt(14)
    heading.font.bold = True
    heading.paragraph_format.space_before = Pt(18)
    heading.paragraph_format.space_after = Pt(4)


def _docx_section(document: Document, title: str) -> None:
    paragraph = document.add_paragraph(title, style="Resume Heading")
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "777777")
    borders.append(bottom)
    paragraph._p.get_or_add_pPr().append(borders)


def _docx_records(
    document: Document,
    title: str,
    records: list[Experience] | list[Education],
    labels: dict[str, str],
    experience: bool,
) -> None:
    _docx_section(document, title)
    for record in records:
        heading = _record_heading(record, experience)
        name = document.add_paragraph()
        name_run = name.add_run(heading)
        name_run.bold = True
        name_run.font.size = Pt(11)
        document.add_paragraph(_details(record, labels, experience))
        for highlight in record.highlights:
            _docx_plain_bullet(document, highlight)


def _docx_plain_bullet(document: Document, value: str) -> None:
    """Use visible text rather than Word list XML for straightforward ATS parsing."""
    paragraph = document.add_paragraph(f"- {value}")
    paragraph.paragraph_format.left_indent = Mm(4.5)
    paragraph.paragraph_format.first_line_indent = Mm(-3)


def _record_heading(record: Experience | Education, experience: bool) -> str:
    values = (
        (record.title, record.company)
        if experience
        else (record.degree, record.institution)
    )
    return " - ".join(values)


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
    values.append(" - ".join((_format_date(record.start_date, labels), end)))
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
        heading = _record_heading(x, experience)
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
        heading = _record_heading(x, experience)
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
