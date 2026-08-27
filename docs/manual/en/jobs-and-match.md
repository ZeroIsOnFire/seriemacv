# Jobs and match

[Back to the complete guide](index.md) · [Português](../pt-BR/vagas-e-match.md)

Jobs are local structured YAML documents. Their original imported source is retained
inside the canonical job record.

```powershell
seriemacv jobs import .\my-career .\role.yml
seriemacv jobs import .\my-career .\jobs.zip
seriemacv jobs list .\my-career
seriemacv jobs show .\my-career platform-engineer
seriemacv jobs extract-requirements .\my-career platform-engineer
```

`extract-requirements` only prints conservative, deterministic candidates when a
document has no structured requirements. It never changes the job file.

Generate a report with:

```powershell
seriemacv match .\my-career platform-engineer
```

The YAML report contains every requirement, its official classification, verified
`evidence_ids`, gaps, conflicts, interview notes, and a weighted score. Only verified
career evidence can support a positive or conflicting conclusion. `NO_EVIDENCE` has
no evidence IDs and never increases the score.

The default dimension weights are configurable in `seriemacv.yml`:

```yaml
match_weights:
  core_technical_fit: 35
  experience_seniority: 20
  responsibilities: 15
  domain: 10
  location_schedule: 10
  language: 5
  other_constraints: 5
```

The values must be non-negative and total 100.

To request a job-specific resume variant from a local agent, include the job ID:

```powershell
seriemacv proposal request .\my-career --id platform-tailor `
  --variant-id platform-engineer --language en --job-id platform-engineer `
  --output .\platform-request.yml
```

The request contains the deterministic match report and verified evidence. The agent
returns a separate proposal that must still be reviewed and explicitly accepted.

## MCP

`seriemacv-mcp` is a dependency-free stdio MCP server for compatible hosts such as
Codex and Claude Code. It provides read-only search, job listing, and match-report
tools, plus `propose_resume_tailoring`, which only returns a request and never writes
to the project.

## Local Studio

Start the initial read-only job workspace with
`seriemacv studio .\my-career`. It listens only on `127.0.0.1` by default and shows
imported jobs and their live deterministic match reports. It has no editing or
submission controls.
