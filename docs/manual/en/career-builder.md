# Career Builder

[Back to the complete guide](index.md) · [Português](../pt-BR/career-builder.md)

Career data is split by responsibility. `career.yml` owns canonical,
language-independent facts. `career.locales/<locale>.yml` owns reusable resume
wording such as titles, summaries, highlights, and localized skill names. Generated
resumes never write changes back to either file.

| Canonical section | Facts in `career.yml` | Wording in `career.locales/<locale>.yml` |
| --- | --- | --- |
| `profile` | Name, contact, links | Title, location, languages, work wording |
| `experience` | ID, employer, dates | Role, location, employment type, bullets, and at most one highlight |
| `education` | ID, institution, dates | Degree, field, location, highlights |
| `skills` | ID, level, tags, editorial priority | Display name, category |
| `evidence` | Traceable support for professional statements | Not localized or printed |
| `answers` | Reusable answers for future workflows | Not localized or printed |
| `stories` | Structured situation/action/result stories | Not localized or printed |

The locale document also owns the professional `summary`. Fixed section labels,
months, translated level names, “Present”, and `date_format` belong in
`i18n/<locale>.yml`.

All record IDs use lowercase kebab-case, such as `example-company-senior`, and must
be unique inside their section. Dates use `YYYY-MM`; an end date cannot precede its
start date. LinkedIn, portfolio, and named links accept explicit HTTP(S) URLs. The
strict schema rejects unknown fields.

## Validate career content

```powershell
seriemacv career validate .\my-career
```

This validates canonical facts, including required name and email, YAML syntax,
unknown fields, duplicate IDs, dates, and evidence references. Validate the complete
renderable projection separately:

```powershell
seriemacv career locale list .\my-career
seriemacv career locale validate .\my-career --language en
```

Locale validation requires matching `career.locales/en.yml` and `i18n/en.yml` files,
checks every canonical record reference, and confirms that the composed resume has a
localized profile title. Diagnostics include a field path and line/column when
available.

## Set profile fields

`set-profile` performs a partial update; omitted scalar fields retain their values.

```powershell
seriemacv career set-profile .\my-career `
  --name "Your Name" `
  --email you@example.com `
  --phone "+1 555 0100" `
  --linkedin https://www.linkedin.com/in/example `
  --portfolio https://example.invalid `
  --link GitHub=https://github.com/example
```

`--link` is repeatable and named links are merged into existing `profile.links`.
LinkedIn and portfolio also have dedicated fields. Edit the title, location,
languages, and other locale-specific profile wording in
`career.locales/<locale>.yml`.

## Add experience

```powershell
seriemacv career add-experience .\my-career `
  --id example-company-senior `
  --company "Example Company" `
  --start-date 2022-03 `
  --end-date 2025-08
```

`--id`, `--company`, and `--start-date` are required. Omit `--end-date` for the
current role. Then add the same ID under `experience` in each required career locale
with its role title, regular bullets, and at most one factual highlight. If no source
achievement is explicitly emphasized, omit `highlights`.

## Add education

```powershell
seriemacv career add-education .\my-career `
  --id example-university `
  --institution "Example University" `
  --start-date 2014-01 `
  --end-date 2017-12
```

Institution, ID, and start date are required. Add the degree, field, location, and
highlights under the matching ID in each career locale.

## Add skills

```powershell
seriemacv career add-skill .\my-career `
  --id python `
  --level advanced `
  --core `
  --tag backend
```

Skill levels are stable English codes: `beginner`, `intermediate`, `advanced`, and
`expert`. Rendering localizes these codes. `--core` marks editorial priority and
renders the skill with emphasis. Add the display name and category under the matching
skill ID in each career locale. Categories group the complete skill list; an
uncategorized skill is placed under the localized “Other” group only when categorized
skills also exist.

## Add evidence

```powershell
seriemacv career add-evidence .\my-career `
  --id deployment-reliability `
  --statement "Improved deployment reliability through automated checks." `
  --experience-id example-company-senior `
  --detail "Change documented in the internal delivery report." `
  --tag reliability `
  --verified
```

Tags and details are repeatable. `--experience-id` must reference an existing
experience. Omit `--verified` when the statement still needs confirmation. Evidence
is kept in the canonical document but is not printed in resumes.

## Add reusable answers and stories

```powershell
seriemacv career add-answer .\my-career `
  --id availability `
  --prompt "When can you start?" `
  --answer "I can start immediately." `
  --tag availability `
  --evidence-id deployment-reliability

seriemacv career add-story .\my-career `
  --id deployment-recovery `
  --title "Deployment recovery" `
  --situation "A release needed recovery." `
  --action "Coordinated the recovery." `
  --result "Service was restored." `
  --evidence-id deployment-reliability
```

Answers can omit `--evidence-id` when they contain user-configured operational
information. When supplied, every evidence ID must exist and be marked
`verified: true`. Stories require situation, action, and result; neither record is
printed in a resume.

## Search verified evidence

```powershell
seriemacv career search-evidence .\my-career reliability
seriemacv career search-evidence .\my-career --tag python --experience-id example-company-senior
```

Search reads `career.yml` directly. It only returns evidence marked `verified: true`;
pending evidence is never included in results. Provide text, one or more `--tag`
filters, or `--experience-id`. Repeated tags are combined, and the output is
validated YAML.

## Inspect sections

```powershell
seriemacv career list .\my-career profile
seriemacv career list .\my-career experience
seriemacv career list .\my-career skills
```

Valid canonical sections are `profile`, `experience`, `education`, `skills`,
`evidence`, `answers`, and `stories`. Output is validated YAML suitable for inspection
or use by another local tool. Locale documents remain directly inspectable YAML.

## Fields without editing commands

The CLI does not yet edit localized wording or existing records. Edit canonical facts
in `career.yml` and professional wording in
`career.locales/<locale>.yml`, following their `.example` files. Then run both
`career validate` and `career locale validate`. Unknown fields are rejected, and a
failed CLI write does not modify the canonical file.

Continue with [Resumes and styles](resume-rendering.md).
