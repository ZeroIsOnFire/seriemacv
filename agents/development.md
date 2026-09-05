# Development agent — seriemaCV

Use this profile only for product and repository work. It does not authorize edits
to a user's canonical career data or external actions on the user's behalf.

## Product boundaries

- Centralize rules in the domain core. Studio, CLI, MCP, and Playwright workers use
  the same use cases; do not duplicate business logic in interface layers.
- Keep boundaries clear between domain, persistence, rendering, AI, job connectors,
  and browser automation.
- `career.yml` is canonical. Markdown, DOCX, PDF, and other artifacts are generated
  from YAML. Proposals remain reviewable and never persist canonical data by
  themselves.
- AI proposals return structured data, `evidence_ids`, confidence, and missing user
  input. Begin retrieval with lexical search and metadata filters; do not add vector
  infrastructure without a proven need.
- Matching is deterministic and explainable: `STRONG_MATCH`, `MATCH`,
  `PARTIAL_MATCH`, `TRANSFERABLE`, `NO_EVIDENCE`, and `CONFLICT` only.
- Browser workflows are state machines. They prioritize deterministic profile data,
  saved answers, rules, evidence-based proposals, then user questions; never submit
  unresolved required fields.

## Privacy and safety

- Do not include resume text in telemetry by default. Explain context sent to AI
  providers.
- Use operating-system secure storage for secrets where possible. Isolate browser
  profiles per user or project, redact diagnostics, and exclude personal data from
  diagnostic bundles unless explicitly selected.
- Validate URLs, Markdown, YAML, JSON, files, connector responses, and environment
  variables at system boundaries.
- Do not add dependencies, external services, scraping, or platform automation
  without explicit authorization.

## Engineering practice

- Before reading large files, use `rg` to find relevant excerpts. Avoid generated
  artifacts, logs, and dumps.
- The core and CLI use Python. After installing `.[dev]`, run the official gate with
  `python scripts/check_quality.py`; use Python 3.11+ if `python` is unavailable.
- Do not weaken checks, broaden exclusions, add blanket ignores, or remove assertions
  merely to make the gate pass. Fix the cause or document a narrowly scoped,
  reviewable baseline. Expand the typed-file list as existing type debt is resolved.
- Load YAML with `ruamel.yaml` in round-trip mode and validate strict Pydantic
  models. Do not silently accept unknown central-schema fields.
- `seriemacv validate` checks project structure and `seriemacv career validate`
  checks career content, references, and completeness. Keep legacy project support;
  conversions must be explicit and must not remove legacy canonical data.
- `resume render --format markdown|html|pdf|docx [--style ID]` validates before
  atomically writing `exports/resume.*`; PDF requires Playwright Chromium.
- Canonical PDF rendering is content-addressed: reuse a current cached PDF through
  the normal renderer instead of launching Playwright again. Do not delete or bypass
  `.seriemacv/cache` to force work. Job-specific variants intentionally render fresh.
- Preserve the ATS-safe style constraints and the documented style-family contracts.
  Keep tracked examples exactly synchronized with `init` templates.
- Write or update behavioral tests before implementing a behavior change. Tests must
  not require network access, secrets, remote models, or real career data.
- Use only fictitious tracked fixtures. Never copy `.local-resumes`, browser state,
  application answers, downloaded personal documents, or generated diagnostics into
  tests, examples, commits, or tool output.
- Bound retries. After the same command or browser action fails twice for the same
  reason, stop repeating it, inspect the cause, and change the approach. Never hide
  a retry loop behind a longer timeout.
- Run focused checks while working, then risk-proportionate validation. Review the
  diff and fix actionable findings before handoff; never report failed, timed-out,
  or skipped validation as success.

## Documentation and delivery

- Keep the English and Brazilian Portuguese READMEs cross-linked and maintain the
  corresponding manuals under `docs/manual/` when user-facing behavior changes.
- Keep changes focused; preserve unrelated user changes. Commits are atomic, in
  Portuguese, and use Conventional Commits.
- Review dependency diffs and `python -m pip check`; do not add or loosen a dependency
  merely to silence a quality failure.
- At handoff report changed files, validations, limitations, and remaining risks.
