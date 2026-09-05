# Complete seriemaCV usage guide

[Manual em português](../pt-BR/index.md) · [Project README](../../../README.md)

seriemaCV stores career information locally in a canonical `career.yml` and turns
that document into Markdown, HTML, PDF, and DOCX resumes. The source YAML always
remains under the user's control.

## Guide by feature

| Feature | What it does | Guide |
| --- | --- | --- |
| Installation | Installs the CLI and the optional Chromium runtime for PDF | [Installation](installation.md) |
| Using Seriema with AI | Gives an AI agent reviewable, evidence-grounded career tasks | [Using Seriema with AI](using-ai.md) |
| Using Seriema CLI | Runs the same local workflows directly in PowerShell | [Using Seriema CLI](using-cli.md) |
| Career projects | Creates, configures, and validates the local workspace | [Projects and configuration](projects.md) |
| Career Builder | Maintains canonical facts and localized career wording | [Career Builder](career-builder.md) |
| Resume generation | Lists styles and renders Markdown, HTML, PDF, and DOCX | [Resumes and styles](resume-rendering.md) |
| Local AI proposals | Exchanges reviewable YAML proposals with Codex, Claude Code, or another agent | [Local AI proposals](proposals.md) |
| Jobs and match | Imports jobs, generates explainable reports, and prepares job-specific proposals | [Jobs and match](jobs-and-match.md) |
| Assisted applications | Prepares local, reviewable browser applications without submitting them | [Assisted applications](applications.md) |
| Templates | Exposes the current YAML contract to people and external tools | [Templates and external tools](templates.md) |
| Diagnostics | Explains validation, browser, filesystem, and Python errors | [Troubleshooting](troubleshooting.md) |

## Choose your interface

Use [Using Seriema with AI](using-ai.md) to delegate reviewable work to an AI agent,
or [Using Seriema CLI](using-cli.md) to run commands directly. Both paths use the
same local project and preserve the YAML source under your control.

## Current scope

The local workflow covers career data, resume generation, structured job imports,
explainable match reports, reviewable tailoring proposals, and a read-only Studio.
