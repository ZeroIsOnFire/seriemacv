from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from seriemacv.styles import STYLE_IDS, StyleManifest, list_styles, load_style


class ResumeStyleTests(unittest.TestCase):
    def test_tracked_gallery_contains_fictitious_previews_and_pdfs(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = root / "examples/style-career.yml"

        self.assertIn("Seriema Example", source.read_text(encoding="utf-8"))
        self.assertIn("example.invalid", source.read_text(encoding="utf-8"))
        for style_id in STYLE_IDS:
            with self.subTest(style=style_id):
                preview = root / "examples/styles" / style_id / "preview.png"
                pdf = root / "examples/styles" / style_id / "resume.pdf"
                self.assertTrue(preview.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertTrue(pdf.read_bytes().startswith(b"%PDF-"))

    def test_loads_all_strict_built_in_style_packages(self) -> None:
        styles = list_styles()

        self.assertEqual(tuple(style.id for style in styles), STYLE_IDS)
        self.assertEqual(
            {style.id for style in styles if style.ats_safe},
            {
                "clean",
                "clean-alt",
                "classic",
                "classic-alt",
                "modern",
                "modern-alt",
                "compact",
                "compact-alt",
            },
        )
        self.assertEqual(load_style("sidebar").manifest.layout, "two-column")
        self.assertEqual(load_style("sidebar-alt").manifest.layout, "two-column")
        for family in ("clean", "classic", "modern", "compact", "sidebar"):
            standard = load_style(family).manifest
            alternative = load_style(f"{family}-alt").manifest

            self.assertEqual(standard.layout, alternative.layout)
            self.assertEqual(standard.ats_safe, alternative.ats_safe)
            self.assertEqual(standard.supported_formats, alternative.supported_formats)
            self.assertEqual(standard.markdown_variant, alternative.markdown_variant)
            self.assertNotEqual(
                standard.tokens.section_divider,
                "none",
            )
            self.assertEqual(
                alternative.tokens.section_divider,
                "none",
            )
            standard_tokens = standard.tokens.model_dump()
            alternative_tokens = alternative.tokens.model_dump()
            standard_tokens.pop("section_divider")
            alternative_tokens.pop("section_divider")
            self.assertEqual(standard_tokens, alternative_tokens)
        for style_id in STYLE_IDS:
            package = load_style(style_id)
            self.assertIn("{{main}}", package.template)
            self.assertIn("@page", package.css)

    def test_rejects_unknown_styles_and_malformed_manifests(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown resume style"):
            load_style("unknown")

        invalid = load_style("clean").manifest.model_dump()
        invalid["unexpected"] = True
        with self.assertRaises(ValidationError):
            StyleManifest.model_validate(invalid)

        invalid = load_style("sidebar").manifest.model_dump()
        invalid["ats_safe"] = True
        with self.assertRaisesRegex(ValidationError, "not ATS-safe"):
            StyleManifest.model_validate(invalid)

    def test_rejects_a_manifest_id_that_differs_from_its_package(self) -> None:
        package = load_style("clean")
        document = package.manifest.model_dump()
        document["id"] = "modern"
        with patch("seriemacv.styles.YAML") as yaml:
            yaml.return_value.load.return_value = document
            with self.assertRaisesRegex(ValueError, "contains manifest id"):
                load_style("clean")
