# AGENTS.md — seriemaCV

## Project purpose

seriemaCV is a local-first career-management suite. It keeps canonical career
data in YAML and uses it to create Markdown, DOCX, and PDF representations,
analyze job descriptions, generate explainable compatibility reports, and
prepare applications.

The product must work without AI. When used, AI is an optional,
provider-agnostic integration and never owns the user's data or workflow.

## Non-negotiable principles

- The user's career is local, portable, and inspectable. `career.yml` is the
  canonical career-data source; SQLite is for indexes, normalized state, and cache.
- Markdown, DOCX, and PDF are artifacts generated from YAML. An importer or AI
  proposal may suggest YAML changes, but never changes the canonical source without
  an explicit user action.
- Never invent professional experience, skills, roles, dates, employers, metrics,
  credentials, or legal statements. Suggestions must use verified evidence and
  clearly distinguish facts from pending information.
- Every match must be explainable: each job requirement shows its classification and
  corresponding evidence, including when no evidence exists.
- External actions (applications, form submissions, messages, or profile updates)
  require explicit human approval by default.
- Preserve a useful progression: structured manual builder → AI assistance → agents
  → browser automation. Advanced features cannot be prerequisites.

## Architecture and boundaries

- Centralize rules in the application/domain core. Studio, CLI, MCP, and the
  Playwright worker must use the same use cases; do not duplicate business logic in
  interfaces.
- Keep clear boundaries between domain, persistence, rendering, AI, job connectors,
  and browser automation.
- AI operations that propose changes return structured data, `evidence_ids`,
  confidence, and information requiring user input. Proposals never persist changes
  automatically.
- Start context retrieval with lexical search and metadata filters. Do not introduce
  embeddings or vector infrastructure without a proven need.
- The matching engine calculates scores from deterministic classifications:
  `STRONG_MATCH`, `MATCH`, `PARTIAL_MATCH`, `TRANSFERABLE`, `NO_EVIDENCE`, and
  `CONFLICT`; never from a free-form model percentage.
- Browser workflows are state machines. Prioritize deterministic profile data, saved
  answers, rules, evidence-based AI proposals, then user questions. Never submit an
  unresolved required field.

## Privacy and security

- Do not include resume text in telemetry by default. Explain what context is sent
  to every AI provider.
- Use operating-system secure storage for secrets where possible; never expose
  tokens, passwords, credentials, or sensitive values in logs.
- Validate all external input: URLs, Markdown, YAML, JSON, files, connector
  responses, environment variables, and AI results.
- Isolate browser profiles per project or user. Logs and diagnostics must redact
  credentials and sensitive fields; diagnostic bundles exclude personal data unless
  explicitly selected.
- Do not fill or accept legal statements, work authorization, salary history,
  demographic data, or self-identification without user-configured data and suitable
  review.

## Development and quality

- Before reading large files, use `rg` to find relevant excerpts; avoid generated
  artifacts, logs, and dumps.
- The core and CLI use Python. In PowerShell, run tests with
  `$env:PYTHONPATH = 'src'; python -m unittest discover -s tests -v`; if Windows
  cannot resolve `python`, use Python 3.11+ or `py -3`. Run
  `python -m ruff check src tests` after installing `.[dev]`.
- Load YAML with `ruamel.yaml` in round-trip mode and validate it with strict
  Pydantic models. Do not use unsafe loaders or accept unknown fields in central
  schemas without an explicit compatibility decision.
- `seriemacv validate` checks project structure; `seriemacv career validate` checks
  career content, references, and completeness.
- Preserve compatibility with legacy projects. Conversions must be explicit and must
  not delete the legacy canonical file.
- `resume render --format markdown|html|pdf|docx [--style ID]` validates a complete
  career and atomically writes fixed `exports/resume.*` artifacts. Project config
  supplies the default style; PDF requires Playwright Chromium.
- Built-in ATS-safe styles use linear DOCX text with plain bullets and no tables,
  images, text boxes, or automatic lists. A manifest marked `ats_safe: false` may use
  non-linear structures; the `sidebar` family uses a borderless table and stays
  experimental.
- Each built-in style family has a standard ID with section dividers and an `-alt`
  ID without them. Neither `classic` variant draws a divider below its header.
- Canonical `skills.level` values are English codes. `i18n.py` localizes fixed labels,
  months, and levels; `core` is an explicit editorial priority, while categories keep
  the complete skills list readable.
- Job documents and their strict domain remain preserved, but the public jobs CLI is
  paused. Do not delete existing job data or contracts when working on resume styles.
- `template show <project> career` is the active read-only template interface.
- Tracked `examples/career.yml` and `examples/job.yml` must exactly match the
  templates written by `init`; keep their synchronization test updated.
- Explicitly close every SQLite connection, including reads: a connection context
  manager commits or rolls back transactions but does not guarantee closing on Windows.
- Preserve public formats and stable contracts. Validate predictable errors at system
  boundaries and return structured diagnostics.
- For behavioral changes, write or update the test covering the rule or regression
  first. Tests must not require network access, remote models, GPUs, secrets, or real
  career data.
- Run focused validation while changing code and risk-proportionate validation before
  completion. Never report success for a failed, timed-out, or skipped command.
- After development, review the uncommitted diff, fix actionable findings, and rerun
  affected validation.
- Do not add dependencies, external services, or platform automation without explicit
  authorization.
- The active slice is canonical career data and multi-style Markdown, DOCX, and PDF
  generation. Job matching remains paused; do not add scrapers or application flows.

## Git and delivery

- Keep the main README in English and `README.pt-BR.md` in Portuguese, with visible
  cross-links near the top of both files.
- Keep the feature-based user manual under `docs/manual/` in English and Portuguese;
  both README files link to their language index as the complete usage guide.
- Keep changes small and focused; do not discard existing user changes outside scope.
- Commits must be atomic, in Portuguese, and follow Conventional Commits.
- At handoff, briefly report changed files, validations run, limitations, and
  remaining risks.

## Project learnings

- Keep durable, useful implementation learnings concise in this file under the
  relevant heading; omit temporary details and sensitive data.
- Keep this `AGENTS.md` to at most 150 lines. Near the limit, compact it and remove
  repeated, temporary, or low-value information.
- Architecture decisions belong in `docs/funcionalidades.md`; update it when an
  architecture decision changes.
- Implementation progress belongs in `docs/checklist.md`. Mark an item complete only
  after implementation and risk-proportionate validation.
- External resume references belong in `docs/referencias/`, with provenance and terms
  of use recorded. They are for analysis only; never reuse personal content or present
  them as product-owned styles.
