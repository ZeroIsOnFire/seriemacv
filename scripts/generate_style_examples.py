"""Regenerate the tracked, fictitious built-in style gallery."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright
from ruamel.yaml import YAML

from seriemacv.career import CareerDocument
from seriemacv.project import ProjectConfiguration
from seriemacv.renderer import render_html
from seriemacv.styles import STYLE_IDS, load_style

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples" / "style-career.yml"
OUTPUT = ROOT / "examples" / "styles"
GALLERY_RESUME_COLOR = ProjectConfiguration(
    schema_version=2, project_name="Style gallery"
).resume_color


def main() -> None:
    career = CareerDocument.model_validate(
        YAML(typ="safe").load(SOURCE.read_text(encoding="utf-8"))
    )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for style_id in STYLE_IDS:
                style = load_style(style_id).manifest
                destination = OUTPUT / style_id
                destination.mkdir(parents=True, exist_ok=True)
                page = browser.new_page(
                    viewport={"width": 794, "height": 1123},
                    device_scale_factor=1,
                )
                try:
                    page.emulate_media(media="print")
                    page.set_content(
                        render_html(
                            career,
                            "en",
                            style_id,
                            resume_color=GALLERY_RESUME_COLOR,
                        ),
                        wait_until="load",
                    )
                    page.pdf(
                        path=destination / "resume.pdf",
                        format="A4",
                        print_background=True,
                        prefer_css_page_size=True,
                    )
                    if style.id not in {
                        "timeline",
                        "timeline-alt",
                        "contact-band",
                        "contact-band-alt",
                        "detail-sidebar",
                        "detail-sidebar-alt",
                        "left-rail",
                        "left-rail-alt",
                    }:
                        page.add_style_tag(
                            content=(
                                "body { padding-top: "
                                f"{style.tokens.margins_mm:g}mm !important; }}"
                            )
                        )
                    page.screenshot(
                        path=destination / "preview.png",
                        full_page=True,
                        animations="disabled",
                    )
                finally:
                    page.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
