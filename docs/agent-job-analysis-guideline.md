# AI job-analysis guideline

This guideline tells an AI agent how to analyze a role for seriemaCV. It produces
an advisory, reviewable analysis; it does not change `career.yml`, save a job, or
submit an application.

## Operating rules

- Treat `career.yml` and its verified evidence as the only source of candidate
  facts. Never infer experience, seniority, location eligibility, salary
  expectations, legal status, or work authorization.
- Start from the official career page or ATS (Ashby, Greenhouse, Lever, Workday),
  then the employer's LinkedIn listing and website. Use aggregators only as
  complementary sources.
- Preserve each source URL, access date, and whether a finding is `confirmed`,
  `reported`, or `unknown`. A missing fact stays unknown.
- Keep external company and compensation research separate from the canonical job
  document. It is time-sensitive advisory context, not career data.
- Cite public sources near each finding. Reviews, anecdotes, and salary estimates
  are signals, never employer-confirmed facts.
- Ask the user before using, saving, or filling legal, authorization, tax,
  demographic, self-identification, current-pay, or expected-pay information.

## Workflow

1. **Validate the role.** Capture company, title, seniority, location, work model,
   eligible countries, contract type, language, responsibilities, benefits,
   published pay, and stated visa or authorization restrictions. Confirm that the
   posting and ATS belong to the employer.
2. **Check eligibility first.** Flag country, residence, timezone, onsite,
   authorization, sponsorship, contract, and language constraints. A blocking
   constraint can make application priority `skip` even with a strong technical
   match.
3. **Normalize requirements conservatively.** Add explicit requirements as
   `required` or `preferred`. Record responsibility-derived capabilities as
   `implicit` advisory items; do not silently promote a stack mention to
   `required`.
4. **Run the deterministic match.** Use `seriemacv match <project> <job-id>` after
   an explicitly approved structured import. Keep its official classifications:
   `STRONG_MATCH`, `MATCH`, `PARTIAL_MATCH`, `TRANSFERABLE`, `NO_EVIDENCE`, and
   `CONFLICT`. Only verified `evidence_ids` can support positive conclusions.
5. **Interpret seniority and gaps.** Compare the stated scope with demonstrated
   autonomy, system design, production ownership, reviews, mentoring, architecture,
   cross-team influence, and people leadership. Call out possible overqualification
   separately. Label a likely eliminator as an advisory `blocking_gap`; do not turn
   it into a positive match.
6. **Research compensation.** Keep three values distinct: `published_salary`,
   `market_estimate`, and `recommended_expectation`. Prefer the posting, employer,
   comparable employer roles, Levels.fyi, Glassdoor/Indeed, historical openings,
   then aggregators. State country, currency, employment model, date, and source.
   Never represent a third-party range as employer-confirmed or reuse an expected
   salary without a fresh user review. When saving it, scope it to the applicable
   seniority (for example, `staff`) when the user provides that constraint.
7. **Research the company proportionately.** Summarize product, business model,
   location, stage/funding, stability signals, recent news, remote model, and
   recurring public concerns. For consulting or staffing roles, identify the final
   client, project duration, bench policy, and whether the opening is a talent pool
   when those facts are available. Mark unverified claims as unknown.
8. **Assess opportunity value.** Separately assess technical fit, hiring
   competitiveness, compensation, eligibility, company quality/stability, and
   career value. Consider scope, international exposure, domain, leadership,
   learning, brand, and the candidate's stated goals.
9. **Return a reviewable recommendation.** Use `maximum`, `high`, `medium`, `low`,
   or `skip`; explain trade-offs and blocking risks. Do not reduce this decision to
   a keyword percentage or overwrite the deterministic match score.

## Required proposal shape

Return a YAML or JSON proposal in this shape. Do not add it to the strict job
schema unless the user explicitly maps supported fields into a validated import.

```yaml
analysis_version: 1
job_id: example-role
sources:
  - url: https://careers.example.com/jobs/123
    accessed_at: 2026-08-31
    status: confirmed
eligibility:
  status: eligible # eligible | unknown | blocked
  findings:
    - statement: Brazil is listed as eligible for this remote role.
      status: confirmed
      source_urls: [https://careers.example.com/jobs/123]
requirements:
  - statement: Production Ruby on Rails experience.
    kind: required # required | preferred | implicit
    match_classification: STRONG_MATCH
    evidence_ids: [verified-evidence-id]
    blocking_gap: false
compensation:
  published_salary: null
  market_estimate:
    value: USD 8,000-10,000 monthly gross
    source_urls: [https://example.com/market-data]
    caveats: Contractor range; not employer-confirmed.
  recommended_expectation: null # requires explicit user review
company_research:
  findings: []
  risks: []
career_assessment:
  technical_fit: strong
  hiring_competitiveness: mixed
  career_value: high
  tradeoffs: []
priority:
  level: high # maximum | high | medium | low | skip
  rationale: Explain evidence, unknowns, and trade-offs.
pending_user_input: []
```

## Action boundary

The agent may search public sources, draft a structured import, generate the
deterministic report, and propose a resume variant or application answers with
evidence. It must obtain explicit user approval before persisting canonical career
facts, importing a proposed job, accepting a proposal, filling sensitive fields, or
submitting an application.
