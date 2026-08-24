# seriemacv

[Leia em português](README.pt-BR.md)

<img src="mascot.png" width="140" alt="seriemaCV mascot">

Local-first workspace for maintaining canonical career data in YAML and rendering
editable or publication-ready resumes.

seriemacv is currently a command-line interface designed first for AI agents and
local automation. Its initial goal is to help agents turn verified career experience
into structured YAML and generate consistent resumes without owning the user's data
or decisions. People can also use every command directly. A future standalone GUI
may provide the same core workflows without depending on an agent.

## Documentation

See the [complete usage guide](docs/manual/en/index.md) for installation, project
configuration, every Career Builder command, resume formats, templates, and
troubleshooting.

## Career Builder

```powershell
seriemacv init .\my-career --name "My career" --language en --style modern
seriemacv career set-profile .\my-career --name "Your Name" --email you@example.com
seriemacv career add-experience .\my-career --id current-company --company "Company" --start-date 2024-01
seriemacv career validate .\my-career
```

Each project includes an empty `career.yml` plus fictional `career.yml.example`
and `seriemacv.yml.example` files. `career.yml` is the canonical source for facts;
`career.locales/<locale>.yml` contains the localized resume wording and catalog.

The jobs workspace is temporarily paused. Existing job files and the underlying
validated domain remain intact, but job commands are not exposed by the CLI.

## Render a resume

```powershell
seriemacv resume styles
seriemacv resume render .\my-career --format markdown
seriemacv resume render .\my-career --language en --format pdf --format docx
seriemacv resume render .\my-career --format html --style classic
seriemacv resume render .\my-career --format pdf --style modern
seriemacv resume render .\my-career --format docx --style compact
```

`resume_style` in `seriemacv.yml` defines the default. `--style` overrides it for one
render without changing the project. Every format atomically replaces its fixed
`exports/resume.*` artifact. PDF requires local Chromium:
`python -m playwright install chromium`.

`resume_color` sets the RGB color for configurable visual styles, including `modern`,
`timeline`, `sidebar`, `right-rail`, `centered`, `split-header`, `contact-band`,
`left-rail`, and `detail-sidebar` (including `-alt`); its default is mascot green
`#647D74`.

Markdown styles vary hierarchy, separators, and density; Markdown cannot represent
fonts, colors, or columns. DOCX remains editable. The `sidebar` and `timeline`
families, plus the new rail, band, split-header, and detail-sidebar families, use
non-linear visual layouts and are explicitly experimental and not ATS-safe; the
remaining families remain linear.

Every family has a standard style with section divider lines and an `-alt` style
without them. `classic` and `classic-alt` never draw a line below the centered
header; only their section-title dividers differ.

## Compatible layouts

Browse previews, ATS notes, selection guidance, and downloadable examples in the
[compatible layout gallery](docs/styles.md). It includes the formal
`clean-executive` family and the photo-free visual `timeline` family.

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
