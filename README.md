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

## Render a resume

```powershell
seriemacv resume render .\my-career --format markdown
seriemacv resume render .\my-career --format html
seriemacv resume render .\my-career --format pdf
```

The command validates `career.yml` before writing `exports/resume.md`,
`exports/resume.html`, or `exports/resume.pdf`. PDF requires local Chromium:
`python -m playwright install chromium`.

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
