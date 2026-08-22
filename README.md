# seriemacv

[Leia em português](README.pt-BR.md)

![seriemaCV mascot](mascot.png)

Local-first workspace for maintaining canonical career data in YAML.

## Career Builder

```powershell
seriemacv init .\my-career --name "My career" --language en
seriemacv career set-profile .\my-career --name "Your Name" --title "Your role" --email you@example.com
seriemacv career add-experience .\my-career --id current-company --company "Company" --title "Role" --start-date 2024-01
seriemacv career validate .\my-career
```

Each project includes an empty `career.yml` plus fictional `career.yml.example`
and `seriemacv.yml.example` files. `career.yml` is always the canonical source.

## Local jobs

```powershell
seriemacv jobs add .\my-career --id platform-engineer --title "Platform Engineer" --description "Build reliable systems." --requirement python="Professional Python experience"
seriemacv jobs import .\my-career .\role.yml
seriemacv jobs validate .\my-career
seriemacv jobs list .\my-career
```

Jobs are stored atomically in `jobs/<id>.yml`. Import accepts only strict structured
JSON or YAML proposals, which can be produced by an AI or another local tool; the
original proposal is retained verbatim as source metadata.
Uppercase letters in record and requirement IDs are normalized to lowercase during
import; other characters outside kebab-case are rejected.

```yaml
schema_version: 1
id: platform-engineer
title: Platform Engineer
description: Build and operate reliable cloud-platform services.
requirements:
  - id: python
    statement: Professional Python experience
    priority: required
salary_range: USD 120,000-150,000 annually
```

The same fields may be supplied as JSON.

## Templates for AI tools

An external AI or local script can request the exact current contracts without
reading project files directly:

```powershell
seriemacv template show .\my-career career
seriemacv template show .\my-career job
```

The command prints the fictitious YAML examples created by `init`. The job template
is the input shape for `seriemacv jobs import`; the importer adds its own `source`
metadata to the stored canonical document.
Tracked copies are also available in [`examples/`](examples/).

## Render a resume

```powershell
seriemacv resume render .\my-career --format markdown
seriemacv resume render .\my-career --format html
seriemacv resume render .\my-career --format pdf
seriemacv resume render .\my-career --format docx
```

The command validates `career.yml` before writing `exports/resume.md`,
`exports/resume.html`, or `exports/resume.pdf`. PDF requires local Chromium:
`python -m playwright install chromium`.

The DOCX export writes `exports/resume.docx`: an editable, one-column A4 document
using the built-in `clean` layout. Legacy `.doc` export is not available yet.

`resume_language`, set during `init`, localizes fixed labels only; canonical user
content is never translated or rewritten.

## Skills and links

```yaml
skills:
  - id: ruby
    name: Ruby
    category: Programming
    level: advanced
    core: true
```

Skills are grouped by category and `core` skills are emphasized. Stable level codes
in YAML are localized during rendering. The profile also accepts explicit HTTP(S)
URLs in `linkedin` and `portfolio`.

## Local verification

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python -m ruff check src tests
```

Install development tools with `python -m pip install -e ".[dev]"`.
