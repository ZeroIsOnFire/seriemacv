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
| Career Builder | Maintains profile, experience, education, skills, and evidence | [Career Builder](career-builder.md) |
| Resume generation | Lists styles and renders Markdown, HTML, PDF, and DOCX | [Resumes and styles](resume-rendering.md) |
| Templates | Exposes the current YAML contract to people and external tools | [Templates and external tools](templates.md) |
| NuExtract Docker | Runs the optional local extraction runtime in Docker | [NuExtract with Docker](nuextract-docker.md) |
| Diagnostics | Explains validation, browser, filesystem, and Python errors | [Troubleshooting](troubleshooting.md) |

## Recommended first workflow

```powershell
python -m pip install -e .
seriemacv init .\my-career --name "My career" --language en --style clean
seriemacv career set-profile .\my-career --name "Your Name" --title "Your Role" --email you@example.com
seriemacv career add-experience .\my-career --id current-role --company "Company" --title "Role" --start-date 2024-01
seriemacv career validate .\my-career
seriemacv resume render .\my-career --format docx
```

Use `seriemacv validate .\my-career` when you need to check the project structure.
Use `seriemacv career validate .\my-career` when you need to check the actual career
content and its completeness.

## Current scope

The public workflow currently focuses on career data and resume generation. The job
domain and existing job files are preserved, but job commands are intentionally
hidden while that area is paused.
