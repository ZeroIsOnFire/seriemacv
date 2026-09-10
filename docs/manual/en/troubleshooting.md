# Troubleshooting

[Back to the complete guide](index.md) · [Português](../pt-BR/solucao-de-problemas.md)

## `seriemacv` is not recognized

Install the local checkout and confirm its Scripts directory is on `PATH`:

```powershell
python -m pip install -e .
python -m pip show seriemacv
```

## Windows opens the Microsoft Store Python alias

Use the full installed Python 3.11+ path, use a working `py -3.12`, or disable the
conflicting application execution alias in Windows settings.

## Project validation fails

Run:

```powershell
seriemacv validate .\my-career
```

Restore the specifically reported missing directory or artifact. If the project
predates the current layout, validation automatically recognizes the supported legacy
contract. An old `.seriemacv/index/` directory is ignored and can be kept as a backup.

## Career validation fails

```powershell
seriemacv career validate .\my-career
```

Read diagnostics as `file:line:column: field.path: message`. Common causes are an
empty name/title/email, invalid indentation, an unknown field, duplicate IDs, an
invalid date, or an evidence reference to a missing experience.

Technical errors redact credentials and personal values, including tokens, passwords,
cookies, email addresses, phone numbers, and sensitive application fields. The field
name remains visible so the problem can still be located.

## Share a diagnostic bundle safely

```powershell
seriemacv diagnostics bundle .\my-career --output .\diagnostics.zip
```

The ZIP contains only `diagnostics.json` with the seriemaCV version and redacted
project-structure validation. It excludes career YAML, job and application records,
exports, browser profiles, and AI request/response files. seriemaCV
does not collect or send telemetry.

Dates must use `YYYY-MM`, for example `2024-01`. Current records omit `end_date`.

## An operation produced excessive output

The CLI and MCP server record only numeric local metrics under
`.seriemacv/metrics/operations.jsonl`. Arguments, paths, URLs, selectors, and content
are not stored. Inspect totals and the largest results with:

```powershell
seriemacv diagnostics operations .\my-career --limit 10
```

By default, the warning appears above 65,536 bytes and the latest 1,000 records are
retained. These values can be changed without changing the project schema version:

```yaml
operation_metrics:
  output_warning_bytes: 65536
  max_records: 1000
```

These metrics are never transmitted and do not include Codex tokens or its internal
cache. Reading the summary does not record another operation.

## PDF says Chromium is missing

```powershell
python -m playwright install chromium
```

Run the command with the same Python environment that installed seriemaCV.

## A different style replaced my resume

Outputs are deliberately fixed as `exports/resume.<ext>`. Rendering a second style
in the same format replaces the previous artifact atomically. Copy or rename an
artifact before rendering another style when both versions must be kept.

## Markdown does not look like PDF or DOCX

Markdown has no reliable representation for page geometry, fonts, colors, or
sidebars. It preserves content and varies only structural elements such as headings,
separators, density, and grouping.

## `sidebar` or `timeline` is parsed poorly by an ATS

This is expected: both families are explicitly non-ATS-safe. Render `clean`,
`classic`, `modern`, `compact`, `clean-executive`, or one of their `-alt` variants
for automated parsing.
