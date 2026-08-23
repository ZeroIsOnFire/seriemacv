# seriemacv

[Leia em português](README.pt-BR.md)

![seriemaCV mascot](mascot.png)

Local-first workspace for maintaining canonical career data in YAML and rendering
editable or publication-ready resumes.

## Documentation

See the [complete usage guide](docs/manual/en/index.md) for installation, project
configuration, every Career Builder command, resume formats, templates, and
troubleshooting.

## Career Builder

```powershell
seriemacv init .\my-career --name "My career" --language en --style modern
seriemacv career set-profile .\my-career --name "Your Name" --title "Your role" --email you@example.com
seriemacv career add-experience .\my-career --id current-company --company "Company" --title "Role" --start-date 2024-01
seriemacv career validate .\my-career
```

Each project includes an empty `career.yml` plus fictional `career.yml.example`
and `seriemacv.yml.example` files. `career.yml` is always the canonical source.
`resume_language` localizes fixed labels; canonical user content is never translated.

The jobs workspace is temporarily paused. Existing job files and the underlying
validated domain remain intact, but job commands are not exposed by the CLI.

## Render a resume

```powershell
seriemacv resume styles
seriemacv resume render .\my-career --format markdown
seriemacv resume render .\my-career --format html --style classic
seriemacv resume render .\my-career --format pdf --style modern
seriemacv resume render .\my-career --format docx --style compact
```

`resume_style` in `seriemacv.yml` defines the default. `--style` overrides it for one
render without changing the project. Every format atomically replaces its fixed
`exports/resume.*` artifact. PDF requires local Chromium:
`python -m playwright install chromium`.

Markdown styles vary hierarchy, separators, and density; Markdown cannot represent
fonts, colors, or columns. DOCX remains editable. `clean`, `classic`, `modern`, and
`compact` preserve a linear ATS-safe structure. `sidebar` is a two-column visual
layout and is explicitly experimental and not ATS-safe.

Every family has a standard style with section divider lines and an `-alt` style
without them. `classic` and `classic-alt` never draw a line below the centered
header; only their section-title dividers differ.

## Built-in style gallery

All previews and PDFs below use the fictitious [gallery career](examples/style-career.yml).

| Style | Preview | Characteristics | Example |
| --- | --- | --- | --- |
| `clean` | <img src="examples/styles/clean/preview.png" width="180" alt="Clean resume preview"> | Neutral, single-column, ATS-safe | [PDF](examples/styles/clean/resume.pdf) |
| `clean-alt` | <img src="examples/styles/clean-alt/preview.png" width="180" alt="Clean Alt resume preview"> | Clean without section dividers, ATS-safe | [PDF](examples/styles/clean-alt/resume.pdf) |
| `classic` | <img src="examples/styles/classic/preview.png" width="180" alt="Classic resume preview"> | Traditional serif, centered header, ATS-safe | [PDF](examples/styles/classic/resume.pdf) |
| `classic-alt` | <img src="examples/styles/classic-alt/preview.png" width="180" alt="Classic Alt resume preview"> | Classic without section dividers, ATS-safe | [PDF](examples/styles/classic-alt/resume.pdf) |
| `modern` | <img src="examples/styles/modern/preview.png" width="180" alt="Modern resume preview"> | Contemporary navy accents, ATS-safe | [PDF](examples/styles/modern/resume.pdf) |
| `modern-alt` | <img src="examples/styles/modern-alt/preview.png" width="180" alt="Modern Alt resume preview"> | Modern without section dividers, ATS-safe | [PDF](examples/styles/modern-alt/resume.pdf) |
| `compact` | <img src="examples/styles/compact/preview.png" width="180" alt="Compact resume preview"> | Dense layout for longer careers, ATS-safe | [PDF](examples/styles/compact/resume.pdf) |
| `compact-alt` | <img src="examples/styles/compact-alt/preview.png" width="180" alt="Compact Alt resume preview"> | Compact without section dividers, ATS-safe | [PDF](examples/styles/compact-alt/resume.pdf) |
| `sidebar` | <img src="examples/styles/sidebar/preview.png" width="180" alt="Sidebar resume preview"> | Two-column, human-first, not ATS-safe | [PDF](examples/styles/sidebar/resume.pdf) |
| `sidebar-alt` | <img src="examples/styles/sidebar-alt/preview.png" width="180" alt="Sidebar Alt resume preview"> | Sidebar without section dividers, not ATS-safe | [PDF](examples/styles/sidebar-alt/resume.pdf) |

Regenerate the gallery with:

```powershell
$env:PYTHONPATH = 'src'
python .\scripts\generate_style_examples.py
```

## Templates and structured skills

External tools can read the current fictional career contract with:

```powershell
seriemacv template show .\my-career career
```

```yaml
skills:
  - id: ruby
    name: Ruby
    category: Programming
    level: advanced
    core: true
```

Skills are grouped by category and `core` skills are emphasized. Stable level codes
are localized during rendering. The profile also accepts explicit HTTP(S) URLs in
`linkedin` and `portfolio`.

## Local verification

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python -m ruff check src tests scripts
```

Install development tools with `python -m pip install -e ".[dev]"`.
