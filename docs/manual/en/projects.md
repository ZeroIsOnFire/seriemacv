# Projects and configuration

[Back to the complete guide](index.md) · [Português](../pt-BR/projetos.md)

## Create a project

```powershell
seriemacv init .\my-career --name "My career" --language en --style modern
```

| Argument | Purpose | Values/default |
| --- | --- | --- |
| `path` | Directory that will own the project | Required |
| `--name` | Human-readable project name | Required |
| `--language` | Language for fixed resume labels | `pt-BR` or `en`; default `pt-BR` |
| `--style` | Default resume style | A built-in family ID or its `-alt` variant; default `clean` |

The families are `clean`, `classic`, `modern`, `compact`, and `sidebar`. Add `-alt`
to select the same family without section divider lines, for example `modern-alt`.

`init` refuses to overwrite an existing project. It creates a user-owned empty
`career.yml`, fictional examples, the local SQLite index, export directories, and
reserved directories for future capabilities.

## Important files

| Path | Role |
| --- | --- |
| `seriemacv.yml` | Versioned project settings |
| `career.yml` | Canonical career information owned by the user |
| `career.yml.example` | Complete fictional career contract |
| `seriemacv.yml.example` | Fictional configuration example |
| `exports/resume.*` | Generated artifacts; never canonical data |
| `.seriemacv/index/` | Internal local SQLite state |
| `jobs/` | Preserved workspace for the paused jobs capability |

## Configuration

```yaml
schema_version: 1
project_name: My career
resume_language: en
resume_style: modern
```

`resume_language` translates only labels maintained by seriemaCV, such as section
titles, months, skill levels, and “Present”. It never translates user content.

Projects created before `resume_style` existed remain compatible and use `clean`.
Unknown configuration fields are rejected to expose spelling mistakes early.

## Validate the project structure

```powershell
seriemacv validate .\my-career
```

When `path` is omitted, the current directory is validated. This command checks the
configuration, required directories, required artifacts, and local SQLite index. It
does not validate whether the resume content is complete.

For content validation, continue with [Career Builder](career-builder.md).
