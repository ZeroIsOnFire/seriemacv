# Complete seriemaCV usage guide

[Manual em português](../pt-BR/index.md) · [Project README](../../../README.md)

seriemaCV stores career information locally in a canonical `career.yml` and turns
that document into Markdown, HTML, PDF, and DOCX resumes. The source YAML always
remains under the user's control.

## Guide by feature

| Feature | What it does | Guide |
| --- | --- | --- |
| Installation | Installs the CLI and the optional Chromium runtime for PDF | [Installation](installation.md) |
| Career projects | Creates, configures, and validates the local workspace | [Projects and configuration](projects.md) |
| Career Builder | Maintains canonical facts and localized career wording | [Career Builder](career-builder.md) |
| Resume generation | Lists styles and renders Markdown, HTML, PDF, and DOCX | [Resumes and styles](resume-rendering.md) |
| Local AI proposals | Exchanges reviewable YAML proposals with Codex, Claude Code, or another agent | [Local AI proposals](proposals.md) |
| Jobs and match | Imports jobs, generates explainable reports, and prepares job-specific proposals | [Jobs and match](jobs-and-match.md) |
| Assisted applications | Prepares local, reviewable browser applications without submitting them | [Assisted applications](applications.md) |
| Templates | Exposes the current YAML contract to people and external tools | [Templates and external tools](templates.md) |
| Diagnostics | Explains validation, browser, filesystem, and Python errors | [Troubleshooting](troubleshooting.md) |

## Recommended first workflow

```powershell
python -m pip install -e .
seriemacv init .\my-career --name "My career" --language en --style clean
seriemacv career set-profile .\my-career --name "Your Name" --email you@example.com
seriemacv career add-experience .\my-career --id current-role --company "Company" --start-date 2024-01
# Add the profile title and current-role wording to career.locales/en.yml.
seriemacv career validate .\my-career
seriemacv career locale validate .\my-career --language en
seriemacv resume render .\my-career --format docx
```

Use `seriemacv validate .\my-career` when you need to check the project structure.
Use `seriemacv career validate .\my-career` when you need to check the actual career
facts. Use `career locale validate` to check the selected career wording together
with its application i18n catalog before rendering.

## Current scope

The local workflow covers career data, resume generation, structured job imports,
explainable match reports, reviewable tailoring proposals, and a read-only Studio.
