"""Regenerate the tracked, fictitious built-in style gallery."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from seriemacv.career import load_career
from seriemacv.renderer import render_html
from seriemacv.styles import STYLE_IDS, load_style

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples" / "style-career.yml"
OUTPUT = ROOT / "examples" / "styles"


def main() -> None:
    career = load_career(SOURCE)
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
                        render_html(career, "en", style_id), wait_until="load"
                    )
                    page.pdf(
                        path=destination / "resume.pdf",
                        format="A4",
                        print_background=True,
                        prefer_css_page_size=True,
                    )
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
