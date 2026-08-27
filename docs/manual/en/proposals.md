# Local AI proposals

[Back to the complete guide](index.md) · [Português](../pt-BR/propostas.md)

seriemaCV uses a provider-neutral YAML exchange. It does not call an API, launch an
agent, or send data automatically. Codex, Claude Code, or a person can read a request
file and write a response file; seriemaCV validates and applies only explicitly
accepted items.

## Create a request

```powershell
seriemacv proposal request .\my-career `
  --id platform-tailor `
  --variant-id platform-role `
  --language en `
  --output .\platform-request.yml
```

The request includes localized resume wording, titles, career records, and only
verified evidence. It deliberately excludes email, phone, links, saved answers,
stories, and pending evidence. Share it only with the agent or tool you chose.

## Write a response

The external agent writes strict YAML. Each item has an ID, confidence, pending
information, and evidence IDs. `variant_selection` and `variant_locale` form a resume
variant; `cover_letter` produces a separate Markdown artifact.

```yaml
schema_version: 1
request_id: platform-tailor
items:
  - id: selection
    kind: variant_selection
    selection: {experience: [current-role], education: [], skills: [python]}
    style: clean
    evidence_ids: []
    confidence: high
    pending_information: []
  - id: wording
    kind: variant_locale
    locale_override:
      summary: Builds reliable platform services.
    evidence_ids: [platform-delivery]
    confidence: medium
    pending_information: [Confirm the target seniority.]
  - id: letter
    kind: cover_letter
    body: I am interested in this platform engineering opportunity.
    evidence_ids: [platform-delivery]
    confidence: medium
    pending_information: []
```

Every claim in tailored wording or a cover letter requires evidence that exists in
`career.yml` and is marked `verified: true`. Unknown, pending, or duplicate evidence
IDs are rejected.

## Review and apply

```powershell
seriemacv proposal review .\my-career .\platform-request.yml .\platform-response.yml
seriemacv proposal apply .\my-career .\platform-request.yml .\platform-response.yml `
  --accept selection --accept wording --accept letter
```

Review prints a YAML diff per item. Omit an item from `--accept` to reject it.
Accepted variant items create `resume/variants/<variant-id>/`; an accepted letter
writes `exports/cover-letters/<proposal-id>.<locale>.md`. Canonical career facts are
never modified, and an existing variant is never overwritten.
