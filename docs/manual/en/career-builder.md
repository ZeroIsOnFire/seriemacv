# Career Builder

[Back to the complete guide](index.md) · [Português](../pt-BR/career-builder.md)

`career.yml` is the canonical source for profile data, summary, experience,
education, skills, evidence, saved answers, and stories. Generated resumes never
write changes back to it.

| Section | Purpose | Printed in resumes |
| --- | --- | --- |
| `profile` | Identity, contact, links, languages, and work preferences | Contact fields and languages |
| `summary` | Professional summary written by the user | Yes |
| `experience` | Employment history and factual highlights | Yes |
| `education` | Formal education and highlights | Yes |
| `skills` | Categorized competencies, level, tags, and editorial priority | Yes, except tags |
| `evidence` | Traceable support for professional statements | No |
| `answers` | Reusable answers for future workflows | No |
| `stories` | Structured situation/action/result stories | No |

All record IDs use lowercase kebab-case, such as `example-company-senior`, and must
be unique inside their section. Dates use `YYYY-MM`; an end date cannot precede its
start date. LinkedIn, portfolio, and named links accept explicit HTTP(S) URLs. The
strict schema rejects unknown fields.

## Validate career content

```powershell
seriemacv career validate .\my-career
```

A renderable document requires at least `profile.name`, `profile.title`, and
`profile.email`. Validation also detects invalid YAML, unknown fields, duplicate IDs,
invalid `YYYY-MM` dates, malformed sections, and evidence references to unknown
experiences. Diagnostics include a field path and line/column when available.

## Set profile fields

`set-profile` performs a partial update; omitted scalar fields retain their values.

```powershell
seriemacv career set-profile .\my-career `
  --name "Your Name" `
  --title "Senior Software Engineer" `
  --location "City, Country" `
  --email you@example.com `
  --phone "+1 555 0100" `
  --linkedin https://www.linkedin.com/in/example `
  --portfolio https://example.invalid `
  --work-preference "Remote" `
  --work-authorization "Authorized" `
  --notice-period "30 days" `
  --language English `
  --language Portuguese `
  --link GitHub=https://github.com/example
```

`--language` and `--link` are repeatable. Supplying languages replaces the current
language list. Named links are merged into existing `profile.links`. LinkedIn and
portfolio also have dedicated fields.

## Add experience

```powershell
seriemacv career add-experience .\my-career `
  --id example-company-senior `
  --company "Example Company" `
  --title "Senior Engineer" `
  --start-date 2022-03 `
  --location "Remote" `
  --employment-type "Full-time" `
  --highlight "Improved delivery reliability." `
  --highlight "Mentored engineers."
```

`--id`, `--company`, `--title`, and `--start-date` are required. Use `--end-date
YYYY-MM` for a finished role. Omit it for the current role. `--highlight` is
repeatable and should contain factual statements only.

## Add education

```powershell
seriemacv career add-education .\my-career `
  --id example-university `
  --institution "Example University" `
  --degree "Bachelor of Technology" `
  --field-of-study "Software Development" `
  --location "City, Country" `
  --start-date 2014-01 `
  --end-date 2017-12 `
  --highlight "Completed a final software project."
```

Institution, degree, ID, and start date are required. Education highlights are also
repeatable.

## Add skills

```powershell
seriemacv career add-skill .\my-career `
  --id python `
  --name Python `
  --category Programming `
  --level advanced `
  --core `
  --tag backend
```

Skill levels are stable English codes: `beginner`, `intermediate`, `advanced`, and
`expert`. Rendering localizes these codes. `--core` marks editorial priority and
renders the skill with emphasis. Categories group the complete skill list; an
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

## Inspect sections

```powershell
seriemacv career list .\my-career profile
seriemacv career list .\my-career experience
seriemacv career list .\my-career skills
```

Valid sections are `profile`, `summary`, `experience`, `education`, `skills`,
`evidence`, `answers`, and `stories`. Output is validated YAML suitable for inspection
or use by another local tool.

## Fields without editing commands

The CLI does not yet edit the summary, saved answers, stories, or existing records.
Edit those sections directly in `career.yml`, following `career.yml.example`, then
run `career validate`. Unknown fields are rejected, and failed CLI writes do not
modify the file.

Continue with [Resumes and styles](resume-rendering.md).
