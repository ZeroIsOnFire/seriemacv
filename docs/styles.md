# Compatible resume layouts

[Leia em português](styles.pt-BR.md) · [Back to README](../README.md)

These layouts are original seriemaCV presentations built from generic resume
patterns. They do not copy third-party templates. Every preview and PDF uses the
fictitious [gallery career](../examples/style-career.yml).

## Choosing a layout

- `classic`: traditional serif presentation with a centered header.
- `clean`: neutral default for broad use.
- `clean-executive`: formal hierarchy for senior and leadership profiles.
- `compact`: reduced spacing for longer careers.
- `modern`: stronger navy hierarchy for contemporary roles.
- `sidebar`: human-first two-column presentation; experimental and not ATS-safe.
- `timeline`: dates in a mascot-green side rail and content in a main column,
  without a photo; experimental and not ATS-safe.

All other families are single-column and ATS-safe. A standard ID draws section
dividers; its `-alt` pair removes them. Neither Classic variant draws a divider below
the header. Markdown preserves the information hierarchy but cannot reproduce fonts,
colors, columns, or the Timeline date rail.

## Gallery

| Style | Preview | Characteristics | Example |
| --- | --- | --- | --- |
| `classic` | <img src="../examples/styles/classic/preview.png" width="180" alt="Classic resume preview"> | Traditional serif, centered header, ATS-safe | [PDF](../examples/styles/classic/resume.pdf) |
| `classic-alt` | <img src="../examples/styles/classic-alt/preview.png" width="180" alt="Classic Alt resume preview"> | Classic without section dividers, ATS-safe | [PDF](../examples/styles/classic-alt/resume.pdf) |
| `clean` | <img src="../examples/styles/clean/preview.png" width="180" alt="Clean resume preview"> | Neutral, single-column, ATS-safe | [PDF](../examples/styles/clean/resume.pdf) |
| `clean-alt` | <img src="../examples/styles/clean-alt/preview.png" width="180" alt="Clean Alt resume preview"> | Clean without section dividers, ATS-safe | [PDF](../examples/styles/clean-alt/resume.pdf) |
| `clean-executive` | <img src="../examples/styles/clean-executive/preview.png" width="180" alt="Clean Executive resume preview"> | Formal hierarchy for senior profiles, ATS-safe | [PDF](../examples/styles/clean-executive/resume.pdf) |
| `clean-executive-alt` | <img src="../examples/styles/clean-executive-alt/preview.png" width="180" alt="Clean Executive Alt resume preview"> | Clean Executive without section dividers, ATS-safe | [PDF](../examples/styles/clean-executive-alt/resume.pdf) |
| `compact` | <img src="../examples/styles/compact/preview.png" width="180" alt="Compact resume preview"> | Dense layout for longer careers, ATS-safe | [PDF](../examples/styles/compact/resume.pdf) |
| `compact-alt` | <img src="../examples/styles/compact-alt/preview.png" width="180" alt="Compact Alt resume preview"> | Compact without section dividers, ATS-safe | [PDF](../examples/styles/compact-alt/resume.pdf) |
| `modern` | <img src="../examples/styles/modern/preview.png" width="180" alt="Modern resume preview"> | Contemporary navy accents, ATS-safe | [PDF](../examples/styles/modern/resume.pdf) |
| `modern-alt` | <img src="../examples/styles/modern-alt/preview.png" width="180" alt="Modern Alt resume preview"> | Modern without section dividers, ATS-safe | [PDF](../examples/styles/modern-alt/resume.pdf) |
| `sidebar` | <img src="../examples/styles/sidebar/preview.png" width="180" alt="Sidebar resume preview"> | Two-column, human-first, not ATS-safe | [PDF](../examples/styles/sidebar/resume.pdf) |
| `sidebar-alt` | <img src="../examples/styles/sidebar-alt/preview.png" width="180" alt="Sidebar Alt resume preview"> | Sidebar without section dividers, not ATS-safe | [PDF](../examples/styles/sidebar-alt/resume.pdf) |
| `timeline` | <img src="../examples/styles/timeline/preview.png" width="180" alt="Timeline resume preview"> | Mascot-green date rail, no photo, not ATS-safe | [PDF](../examples/styles/timeline/resume.pdf) |
| `timeline-alt` | <img src="../examples/styles/timeline-alt/preview.png" width="180" alt="Timeline Alt resume preview"> | Timeline without section dividers, not ATS-safe | [PDF](../examples/styles/timeline-alt/resume.pdf) |

## Design basis

The layouts follow general guidance to keep typography readable, spacing
consistent, sections recognizable, and ATS-oriented documents free of tables,
graphics, and text boxes. The current career contract naturally supports
reverse-chronological and lightly combined presentations. A true functional or
skills-first layout remains deferred until skills can reference supporting evidence.

`timeline` is an original, photo-free adaptation of a common date-rail pattern. Its
visual grid is intentionally excluded from the ATS-safe group.

Research references and provenance are recorded in
[resume layout references](referencias/README.md).

Regenerate the gallery with:

```powershell
$env:PYTHONPATH = 'src'
python .\scripts\generate_style_examples.py
```
