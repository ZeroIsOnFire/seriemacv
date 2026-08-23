"""Strict built-in resume style packages."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from ruamel.yaml import YAML

ResumeStyleId = Literal[
    "clean",
    "clean-alt",
    "classic",
    "classic-alt",
    "modern",
    "modern-alt",
    "compact",
    "compact-alt",
    "clean-executive",
    "clean-executive-alt",
    "timeline",
    "timeline-alt",
    "sidebar",
    "sidebar-alt",
]
ResumeLayout = Literal["single-column", "two-column", "timeline"]
MarkdownVariant = Literal[
    "standard",
    "classic",
    "modern",
    "compact",
    "clean-executive",
    "timeline",
    "sidebar",
]
SupportedFormat = Literal["markdown", "html", "pdf", "docx"]

STYLE_FAMILIES: tuple[str, ...] = (
    "clean",
    "classic",
    "modern",
    "compact",
    "clean-executive",
    "timeline",
    "sidebar",
)

STYLE_IDS: tuple[ResumeStyleId, ...] = (
    "clean",
    "clean-alt",
    "classic",
    "classic-alt",
    "modern",
    "modern-alt",
    "compact",
    "compact-alt",
    "clean-executive",
    "clean-executive-alt",
    "timeline",
    "timeline-alt",
    "sidebar",
    "sidebar-alt",
)


class StrictStyleModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class StyleTokens(StrictStyleModel):
    font_family: str = Field(min_length=1)
    body_size_pt: float = Field(gt=0)
    name_size_pt: float = Field(gt=0)
    section_size_pt: float = Field(gt=0)
    record_size_pt: float = Field(gt=0)
    margins_mm: float = Field(gt=0)
    line_spacing: float = Field(gt=0)
    section_spacing_pt: float = Field(ge=0)
    primary_color: str = Field(pattern=r"^[0-9A-Fa-f]{6}$")
    accent_color: str = Field(pattern=r"^[0-9A-Fa-f]{6}$")
    header_alignment: Literal["left", "center"]
    section_divider: Literal["none", "line", "accent"]
    sidebar_width_mm: float | None = Field(default=None, gt=0)


class StyleManifest(StrictStyleModel):
    schema_version: Literal[1]
    id: ResumeStyleId
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    layout: ResumeLayout
    page_size: Literal["A4"]
    ats_safe: bool
    supported_sections: list[
        Literal["summary", "experience", "education", "skills", "languages"]
    ] = Field(min_length=1)
    supported_formats: list[SupportedFormat] = Field(min_length=1)
    markdown_variant: MarkdownVariant
    tokens: StyleTokens

    @model_validator(mode="after")
    def layout_contract(self) -> "StyleManifest":
        if len(self.supported_sections) != len(set(self.supported_sections)):
            raise ValueError("supported_sections must not contain duplicates")
        if len(self.supported_formats) != len(set(self.supported_formats)):
            raise ValueError("supported_formats must not contain duplicates")
        if self.layout in {"two-column", "timeline"}:
            if self.ats_safe:
                raise ValueError("non-linear styles must be marked as not ATS-safe")
            if self.tokens.sidebar_width_mm is None:
                raise ValueError("non-linear styles require sidebar_width_mm")
        elif self.tokens.sidebar_width_mm is not None:
            raise ValueError("single-column styles must not define sidebar_width_mm")
        return self


@dataclass(frozen=True)
class StylePackage:
    manifest: StyleManifest
    template: str
    css: str


def load_style(style_id: str) -> StylePackage:
    if style_id not in STYLE_IDS:
        raise ValueError(
            f"Unknown resume style '{style_id}'; choose one of: {', '.join(STYLE_IDS)}"
        )
    root = files("seriemacv").joinpath("assets", "styles", style_id)
    document = YAML(typ="safe").load(
        root.joinpath("style.yml").read_text(encoding="utf-8")
    )
    manifest = StyleManifest.model_validate(document)
    if manifest.id != style_id:
        raise ValueError(
            f"Style package directory '{style_id}' contains manifest id '{manifest.id}'"
        )
    return StylePackage(
        manifest=manifest,
        template=root.joinpath("template.html").read_text(encoding="utf-8"),
        css=root.joinpath("print.css").read_text(encoding="utf-8"),
    )


def list_styles() -> tuple[StyleManifest, ...]:
    return tuple(load_style(style_id).manifest for style_id in STYLE_IDS)
