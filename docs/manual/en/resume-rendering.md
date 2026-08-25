# Resumes and styles

[Back to the complete guide](index.md) · [Português](../pt-BR/renderizacao.md)

Resume generation is a read-only projection of canonical `career.yml` facts plus a
complete `career.locales/<locale>.yml` editorial document. Each output
is written atomically to a fixed path under `exports/`.

## Structured variants

Static, reusable wording remains in `career.locales/`. A job-specific variant uses
this separate layout:

```text
resume/variants/<id>/
├── variant.yml
└── locales/
    ├── en.yml
    └── pt-BR.yml
```

`variant.yml` may reference a preserved `job_id`, choose a style, and select or
order canonical experience, education, and skill IDs. Files under `locales/` are
partial editorial overrides: omitted fields inherit the static career locale. They
cannot change names, contacts, employers, institutions, dates, or other canonical
facts. A tailored summary or highlights require `evidence_ids` that exist and are
marked `verified: true` in `career.yml`.

```powershell
seriemacv resume variants list .\my-career
seriemacv resume variants validate .\my-career
seriemacv resume variants validate .\my-career --id platform-role
seriemacv resume render .\my-career --variant platform-role --language en --format pdf
```

Variant artifacts use `exports/resume.<variant>.<locale>.<ext>` and never overwrite
the base resume. Style precedence is `--style`, then the variant style, then the
project default. A variant locale is optional; without one, selection and ordering
still apply while all wording comes from the static locale.

## List styles

```powershell
seriemacv resume styles
```

| Style | Layout | ATS status | Intended use |
| --- | --- | --- | --- |
| `clean` | One column, neutral sans-serif | ATS-safe | General applications |
| `classic` | One column, centered serif header | ATS-safe | Traditional roles |
| `modern` | One column, navy visual hierarchy | ATS-safe | Contemporary presentation |
| `compact` | One column, reduced spacing | ATS-safe | Longer careers |
| `clean-executive` | One column, formal hierarchy | ATS-safe | Senior and leadership profiles |
| `sidebar` | Two columns | Experimental, not ATS-safe | Human-first visual copy |
| `timeline` | Date rail plus main column | Experimental, not ATS-safe | Visual chronology without photo |
| `centered` | Centered single column | ATS-safe | Compact linear reading |
| `right-rail`, `split-header`, `contact-band`, `left-rail`, `detail-sidebar` | Original visual columns | Experimental, not ATS-safe | Human-first visual copies |

The `sidebar` and `timeline` DOCX files use borderless tables; their HTML/PDF output
uses visual grids. Prefer one of the five linear styles when an applicant tracking
system will parse the document.

Each family also provides an `-alt` pair. Standard IDs draw section-title dividers;
`-alt` IDs remove them while preserving typography, spacing, layout, formats, and
ATS status. The centered `classic` header never has a bottom divider in either
variant.

## Render an artifact

```powershell
seriemacv resume render .\my-career --format markdown
seriemacv resume render .\my-career --format html --style classic
seriemacv resume render .\my-career --format pdf --style modern
seriemacv resume render .\my-career --format docx --style compact
```

`--format` is required. `--style` is optional and overrides `resume_style` for that
execution only.

## Color

`resume_color` in `seriemacv.yml` sets one RGB hexadecimal color. The default is
`#647D74`, the mascot green used by `timeline`. It changes both the primary and accent
color of the configurable visual families (`modern`, `timeline`, `sidebar`,
`right-rail`, `centered`, `split-header`, `contact-band`, `left-rail`, and
`detail-sidebar`) and their `-alt` variants; other styles keep their built-in colors.
Both `#647D74` and `647D74` are accepted.

| Format | Output | Notes |
| --- | --- | --- |
| `markdown` | `exports/resume.<locale>.md` | Portable text; fonts, colors, and columns are flattened |
| `html` | `exports/resume.<locale>.html` | Semantic standalone HTML with embedded CSS and no network assets |
| `pdf` | `exports/resume.<locale>.pdf` | A4 PDF generated from HTML in local Chromium |
| `docx` | `exports/resume.<locale>.docx` | Editable Word document from the dedicated renderer |

Rendering another style in the same format replaces that format's previous artifact.
Other formats are untouched. If validation or generation fails, an existing artifact
is preserved.

## Content rules

- Experience and education are sorted in reverse chronology.
- A missing `end_date` means the record is current.
- Empty optional sections are omitted.
- Summary, highlights, locations, employment types, and other user text are preserved.
- Only fixed labels, dates, and skill levels are localized.
- Evidence, saved answers, and stories are not printed.
- HTML content is escaped before insertion.

## PDF prerequisite

```powershell
python -m playwright install chromium
```

If Chromium is unavailable, the command reports this installation instruction and
does not overwrite an existing PDF.

See the [compatible layout gallery](../../styles.md) for PNG
previews and downloadable example PDFs.
