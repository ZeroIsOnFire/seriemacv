# Installation

[Back to the complete guide](index.md) · [Português](../pt-BR/instalacao.md)

## Requirements

- Python 3.11 or newer.
- A local checkout of this repository.
- Playwright Chromium only when generating PDF files.

DOCX generation uses `python-docx` and does not require Microsoft Word. Markdown and
HTML generation do not require a browser.

## Install the CLI

From the repository root, install the project in editable mode:

```powershell
python -m pip install -e .
```

For development and local verification, install the optional development tools:

```powershell
python -m pip install -e ".[dev]"
```

Confirm that the command is available:

```powershell
seriemacv --help
seriemacv resume styles
```

## Enable PDF generation

Playwright is installed as a Python dependency, but Chromium is installed separately:

```powershell
python -m playwright install chromium
```

The browser is used locally. Resume generation does not need network access after the
browser runtime is installed.

## Windows Python resolution

If the Microsoft Store alias named `python.exe` is selected instead of the installed
interpreter, use the full Python 3.11+ executable path or fix the Windows application
execution aliases. The Python launcher can also be used when it sees the installation:

```powershell
py -3.12 -m pip install -e .
```

Continue with [Projects and configuration](projects.md).
