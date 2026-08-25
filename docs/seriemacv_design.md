# seriemaCV

**Product Design Document**
**Local-first AI Career Suite**
Version 0.1 — August 2026

> From writing a truthful resume to finding the right role and completing the application.

## 1. Product summary

**seriemaCV** is a local-first career assistance suite centered on a structured YAML
career profile. It combines a native career builder, reusable visual templates, job
discovery and compatibility analysis, AI-assisted tailoring, CLI and MCP interfaces,
and optional browser automation for job applications.

The product should work well **without AI** and become substantially more capable **with AI**. AI is an integration layer, not the owner of the user's data or workflow.

The central idea is simple: the user maintains one structured, truthful career source of truth and seriemaCV turns it into the right representation for each opportunity.

### Product promise

**Build. Match. Apply.**

Supporting promise: **One career source. Every application tailored.**

### Why “seriemaCV”

The seriema is strongly associated with Brazil and gives the project a distinctive visual identity. **CV** immediately anchors the product in career documents while remaining concise and broadly understandable internationally. The product itself goes beyond document editing: job discovery, compatibility analysis, tailoring, agent access, and application assistance all live under the same brand.

The stylized name **seriemaCV** keeps “seriema” as the distinctive brand and “CV” as the functional signal. The job-discovery capability retains **Scout** as a module name rather than part of the main product name. A preliminary web check found existing software using **Seriema** alone, so the compound name provides better differentiation. This is not a trademark clearance.

---

## 2. Problem

Job hunting is fragmented across several disconnected tasks:

- Maintaining a canonical resume.
- Rewriting the resume for different roles without fabricating experience.
- Comparing a job description with actual experience.
- Writing cover letters and application answers.
- Tracking where and when a user applied.
- Re-entering the same information in ATS forms.
- Searching multiple job sources repeatedly.
- Giving an AI enough context to help without pasting the entire career history on every interaction.

Existing resume builders often optimize the document but stop before job discovery and application. Automation tools often automate forms but do not understand the user's professional history. AI chat can provide strong assistance, but the knowledge and workflow are usually temporary and disconnected from the actual resume artifacts.

seriemaCV connects these activities around a persistent local career model.

---

## 3. Product principles

### 3.1 Local-first

The canonical career data, resumes, job records, generated documents, and application history should live locally by default. Cloud synchronization may be added later, but the local project must remain portable and usable without an account.

### 3.2 YAML is the source of truth

The canonical career data lives in an editable `career.yml` file. Markdown, HTML,
DOCX and PDF are generated projections of that source, not separate documents that
silently diverge.

### 3.3 AI is optional and provider-agnostic

Users can write and manage resumes manually. AI features are exposed through commands and APIs that can be called by the native app, CLI, MCP clients, or future plugins. The system should not require a specific model vendor.

### 3.4 Never invent professional experience

The assistant may reorganize, summarize, translate, emphasize, or suggest missing information. It must clearly distinguish suggestions from verified career facts and must never silently add experience, skills, dates, employers, metrics, or credentials.

### 3.5 Human approval before external actions

Searching and analyzing can be autonomous. Sending applications, submitting forms, sending messages, or changing externally visible profile data should require an explicit user action unless the user has enabled a narrowly scoped automation policy.

### 3.6 Progressive automation

The product should be useful at four levels:

1. Manual structured career builder.
2. AI-assisted career builder and job matcher.
3. Agent-assisted job search and application preparation.
4. Browser-assisted application workflow.

A user should never need level 4 to benefit from levels 1–3.

---

## 4. Target users

### Primary persona: experienced technical professional

A developer, engineer, designer, product professional, or other knowledge worker with enough experience that one static resume no longer represents every possible role well.

They need to maintain a reliable career history while generating different resume variants for roles such as senior individual contributor, lead, architect, specialist, or international remote positions.

### Secondary persona: active job seeker

A user applying to many positions who needs matching, tracking, reusable application answers, and browser-assisted form filling.

### Future persona: career advisor or recruiter-side assistant

Potential later support for consultants helping multiple people, but this should not distort the initial personal/local-first design.

---

## 5. Product surface

seriemaCV is composed of six surfaces that share the same local project.

### 5.1 seriemaCV Studio

The native desktop experience.

Responsibilities:

- Structured career-data builder.
- Live rendered preview.
- Resume section navigation.
- Structured metadata editing.
- Style/template picker.
- Job workspace.
- Match reports.
- Application tracker.
- AI command palette.
- Diff view for AI-proposed edits.

### 5.2 seriemaCV CLI

The automation-friendly interface and reference implementation of core features.

Example commands:

```bash
seriemacv init
seriemacv resume validate
seriemacv resume render --style clean --format pdf
seriemacv resume styles
```

Job, match, tailoring, application, and MCP commands remain roadmap examples. The
public jobs interface is paused while the product focuses on resume rendering.

The GUI should call the same application/core layer used by the CLI whenever possible.

### 5.3 seriemaCV MCP

An MCP server lets external agents use seriemaCV as a career context and action provider.

Candidate tools:

```text
career.get_profile
career.get_resume
career.search_experience
resume.validate
resume.render
resume.propose_tailoring
jobs.add
jobs.search
jobs.get
jobs.match
jobs.compare
applications.prepare
applications.get_status
applications.list
browser.prepare_application
```

Potential resources:

```text
seriemacv://career
seriemacv://resume/generated/master
seriemacv://jobs/{id}
seriemacv://applications/{id}
seriemacv://knowledge/answers
```

Write-capable tools should be intentionally narrower than read tools.

### 5.4 AI adapters

The core exposes deterministic operations; AI adapters implement reasoning operations.

Initial adapters can include:

- OpenAI-compatible HTTP API.
- Anthropic-compatible API.
- Local OpenAI-compatible endpoints such as llama.cpp or LM Studio.
- External agent through MCP, where seriemaCV itself does not call an LLM.

The user can therefore choose between **built-in AI**, **CLI-only workflows**, or **bring-your-own-agent**.

### 5.5 Job connectors

Job ingestion should be adapter-based. A connector converts a public job page, pasted description, API result, or browser extraction into the internal Job model.

Initial sources:

- URL import.
- Raw text / Markdown paste.
- Browser capture.
- Generic structured JSON import.

Dedicated website integrations should remain optional because job platforms change frequently and can impose automation restrictions.

### 5.6 Browser automation

Playwright is the browser execution layer for application workflows.

It should not be treated as a blind “auto apply bot.” Its primary purpose is to:

- Open an application page.
- Identify fields.
- Map known profile data to fields.
- Draft answers for unknown text fields.
- Attach the selected resume.
- Pause for user review.
- Submit only after confirmation by default.

---

## 6. Core user flows

### Flow A — Create the career source

```text
Create project
    ↓
Start structured builder / import existing resume
    ↓
Edit manually or ask AI for suggestions
    ↓
Validate career facts and structure
    ↓
Preview style
    ↓
Export PDF / DOCX / HTML
```

### Flow B — Evaluate a job

```text
Paste URL or job description
    ↓
Normalize job data
    ↓
Extract requirements
    ↓
Compare with verified career profile
    ↓
Match report
    ├─ strong matches
    ├─ partial matches
    ├─ missing requirements
    ├─ evidence from career history
    └─ interview / application notes
```

The match should be explainable. A score without evidence is not enough.

### Flow C — Tailor a resume

```text
Career YAML + Career knowledge + Job
                ↓
          Tailoring proposal
                ↓
              Diff
        <- accept   reject ->
      Generated variant          Canonical YAML unchanged
        ↓
Render using selected style
```

Tailoring changes emphasis, ordering, wording, and selected details. It does not modify the canonical facts unless the user explicitly edits them.

### Flow D — Apply

```text
Selected job
    ↓
Choose resume variant
    ↓
Generate / select cover letter
    ↓
Open browser session
    ↓
Fill deterministic fields
    ↓
Draft uncertain answers
    ↓
User review checkpoint
    ↓
Submit
    ↓
Record application metadata
```

---

## 7. Career data model

The career YAML should remain human-readable and hold the complete user-owned
career source. Markdown is generated from it when a text representation is needed.

Suggested project layout:

```text
my-career/
├── seriemacv.yml
├── career.yml
├── career.locales/
│   └── <locale>.yml
├── i18n/
│   └── <locale>.yml
├── resume/
│   └── variants/
│       └── <id>/
│           ├── variant.yml
│           └── locales/<locale>.yml
├── jobs/
│   ├── index.jsonl
│   └── sources/
├── applications/
├── styles/
├── exports/
└── .seriemacv/
    ├── cache/
    ├── browser/
    └── index/
```

### career.yml

Contains the canonical profile, experience, education, skills, verified evidence,
reusable answers and stories. Deterministic application data such as location,
links, languages, work authorization preferences, notice period and contact data
also live here.

The file may contain reusable facts that may not all fit in one rendered resume:

```yaml
evidence:
  - id: gov-processing-optimization
    company: example-company
    tags: [performance, rails, postgres, concurrency]
    statement: Reduced a large processing workflow from ~24 hours to ~2.5 hours.
    evidence:
      - batching
      - query optimization
      - controlled concurrency
    verified: true
```

This gives the agent a richer source than a finished two-page resume while keeping claims explicit.

---

## 8. Career YAML format

The first version uses a versioned, documented YAML schema. Markdown is a generated
format, not a format that users need to edit to use seriemaCV.

Example:

~~~yaml
schema_version: 1
profile:
  name: Jane Doe
  title: Senior Software Engineer
  location: São Paulo, Brazil
  links:
    github: https://github.com/example
    linkedin: https://linkedin.com/in/example
summary: Senior Software Engineer focused on ...
experience:
  - company: Example Corp
    title: Senior Software Engineer
    start_date: 2025-01
    highlights:
      - Built ...
      - Reduced ...
skills: [Ruby, Rails, PostgreSQL, AWS]
~~~

## 9. Resume style system

Styles should separate **content** from **presentation**.

A style package can contain:

```text
styles/clean/
├── style.yml
├── template.html
├── print.css
└── preview.png
```

`style.yml` may define page size, typography tokens, spacing, supported sections, and capabilities.

Initial style goals:

- ATS-safe single-column.
- Compact technical resume.
- Modern professional.
- Minimal international.

Rendering pipeline:

```text
Career YAML
   ↓
Resume model
   ↓
HTML template + CSS
   ↓
Browser renderer
   ↓
PDF
```

Markdown and DOCX use dedicated renderers because neither document format should be
generated from PDF. Legacy `.doc` export is intentionally unsupported.

---

## 10. Matching engine

Matching should combine deterministic extraction with optional LLM reasoning.

### Stage 1 — Job normalization

Extract:

- Role title.
- Seniority.
- Required skills.
- Preferred skills.
- Responsibilities.
- Domain experience.
- Location/timezone requirements.
- Language requirements.
- Employment model.
- Compensation when available.

### Stage 2 — Evidence retrieval

For each requirement, retrieve evidence from the user's verified career knowledge.

### Stage 3 — Classification

Each requirement becomes one of:

```text
STRONG_MATCH
MATCH
PARTIAL_MATCH
TRANSFERABLE
NO_EVIDENCE
CONFLICT
```

### Stage 4 — Weighted score

The numerical score is derived from classified requirements rather than requested directly from an LLM.

Suggested dimensions:

```text
Core technical fit        35%
Experience / seniority    20%
Responsibilities          15%
Domain                    10%
Location / schedule       10%
Language                   5%
Other constraints          5%
```

Weights should be configurable.

### Stage 5 — Explanation

The system should display not just “87% match,” but why:

```text
Rails             STRONG_MATCH   12+ years, multiple production systems
PostgreSQL        STRONG_MATCH   optimization and advanced queries
Kubernetes        PARTIAL_MATCH  practical knowledge, limited production ownership
US timezone       MATCH          availability overlaps requested hours
Go                NO_EVIDENCE    no verified experience
```

---

## 11. AI architecture

AI functionality should operate on explicit **skills/use cases**, not arbitrary access to the whole application.

Recommended internal interface:

```text
AIUseCase
├── analyze_job(job, context)
├── match_job(job, career_evidence)
├── propose_resume_changes(job, resume, evidence)
├── draft_cover_letter(job, resume, evidence)
├── answer_application_question(question, context)
└── summarize_company(company_context)
```

Every AI result that may change career artifacts should return structured output with provenance:

```json
{
  "proposal": "...",
  "evidence_ids": ["gov-processing-optimization"],
  "confidence": "high",
  "requires_user_fact": false
}
```

The application can reject a suggestion if it references nonexistent evidence.
Local extraction proposals follow the same contract: runtime locality does not make
model output trusted or authorize persistence.

### Context strategy

Do not send the entire project to the model on every request.

Use a local retrieval layer over:

- Resume sections.
- Achievements.
- Skills.
- Previous application answers.
- Interview stories.
- Job requirements.

Start with lexical + metadata filtering. Add embeddings only when necessary.

---

## 12. MCP design

MCP should make seriemaCV useful from Codex, Claude Code, IDE agents, or other compatible hosts.

### Read tools

```text
get_career_source
get_generated_resume
get_resume_variant
get_job
list_jobs
get_match_report
search_career_evidence
list_applications
```

### Proposal tools

```text
propose_resume_tailoring
propose_cover_letter
propose_application_answer
propose_job_match
```

These return changes without mutating the project.

### Write tools

```text
save_resume_variant
save_job
save_application_draft
update_application_status
```

### High-risk tools

Browser submission should be deliberately isolated:

```text
prepare_browser_application
fill_browser_application
submit_browser_application
```

`submit_browser_application` should require an explicit confirmation token generated by a user-approved review step.

---

## 13. Playwright application engine

The browser automation engine should be implemented as a state machine rather than one large AI prompt.

Suggested states:

```text
OPEN_PAGE
  ↓
DETECT_PLATFORM
  ↓
DISCOVER_FIELDS
  ↓
MAP_KNOWN_FIELDS
  ↓
RESOLVE_UNKNOWN_FIELDS
  ↓
ATTACH_DOCUMENTS
  ↓
VALIDATE_PAGE
  ↓
REVIEW
  ↓
SUBMIT
  ↓
CAPTURE_RESULT
```

### Field resolution priority

1. Exact deterministic profile mapping.
2. Saved answer mapping.
3. Rule-based transformation.
4. AI-generated proposal from verified context.
5. Ask the user.

This ordering minimizes hallucination and token cost.

### Safety rules

The application engine should never automatically:

- Agree to false legal statements.
- Invent work authorization.
- Invent salary history.
- Invent demographic information.
- Answer voluntary self-identification questions without configured user data.
- Submit an application with unresolved required fields.

Sensitive fields should be excluded from the general AI context unless specifically needed and explicitly configured.

---

## 14. Application tracking

Each application gets a persistent record:

```yaml
id: example-senior-rails-2026-08
company: Example
role: Senior Rails Engineer
job_id: job-123
status: applied
applied_at: 2026-08-21
resume: resume/variants/example-senior-rails.md
cover_letter: applications/example/cover-letter.md
source_url: https://example.com/jobs/123
notes: ""
```

Suggested statuses:

```text
saved → evaluating → preparing → applied → recruiter → interview → offer
                                             -> rejected
                                             -> withdrawn
```

The tracker eventually enables useful analytics: response rate by resume style, source, role family, geography, or matching score.

---

## 15. Desktop architecture

A good initial desktop architecture is **Tauri + web frontend + Rust host**, while keeping the career engine separately callable from the CLI.

One possible structure:

```text
┌────────────────────────────────────────────┐
│             seriemaCV Studio               │
│ Editor · Preview · Jobs · Match · Tracker  │
└──────────────────┬─────────────────────────┘
                   │
          ┌────────▼────────┐
          │ Application Core│
          │ domain/use cases│
          └───┬─────────┬───┘
              │         │
       ┌──────▼───┐ ┌──▼──────────┐
       │ Career DB│ │ AI Gateway  │
       │ + files  │ │ + Retrieval │
       └──────────┘ └─────┬───────┘
                          │
             ┌────────────┼────────────┐
             │            │            │
          OpenAI       Local LLM    MCP Host

CLI ───────────────► Application Core
MCP Server ────────► Application Core
Playwright Worker ─► Application Core
```

The key architectural rule is that the GUI must not become the only place where business logic exists.

### Alternative

If faster delivery matters more than native packaging, the same architecture can begin as a local web application plus CLI, then move into Tauri later. The domain model and command layer should make that migration inexpensive.

---

## 16. Persistence and indexing

Recommended v1 persistence:

- YAML files for user-owned career artifacts and generated Markdown documents.
- SQLite for indexes, job/application state, caches, and normalized records.
- Optional full-text search via SQLite FTS5.

Why hybrid storage:

- Git-friendly resumes and knowledge files.
- Easy backup and portability.
- Transactional internal state.
- No requirement for a separate database server.

Embeddings can be stored later in SQLite or an optional local vector index.

---

## 17. Internal domain model

Core entities:

```text
CareerProfile
CareerEvidence
Skill
Resume
ResumeVariant
ResumeStyle
Job
JobRequirement
MatchReport
Company
Application
ApplicationAnswer
DocumentArtifact
BrowserSession
AIProposal
```

Important relationships:

```text
CareerProfile 1 ── * CareerEvidence
Resume        1 ── * ResumeVariant
Job           1 ── 1 MatchReport
Job           1 ── 0..1 Application
Application   * ── 1 ResumeVariant
AIProposal    * ── * CareerEvidence
```

`CareerEvidence` is particularly important because it gives the system a factual layer that is richer than a resume and safer than free-form model memory.

---

## 18. Privacy and security

Career projects contain high-value personal information. The local-first design should make privacy part of the architecture rather than a policy page added later.

Requirements:

- No telemetry containing resume text by default.
- Clear disclosure of what context is sent to an AI provider.
- Per-provider configuration.
- Secrets stored using OS credential storage when possible.
- Browser profiles isolated per project or user.
- Logs redact credentials, tokens, and sensitive field values.
- Optional encrypted project secrets.
- Exported diagnostic bundles exclude personal artifacts unless explicitly selected.

---

## 19. Suggested repository architecture

A monorepo fits the shared-core model:

```text
seriemacv/
├── apps/
│   ├── studio/
│   └── cli/
├── packages/
│   ├── core/
│   ├── career-yaml/
│   ├── renderer/
│   ├── matching/
│   ├── ai/
│   ├── mcp/
│   ├── playwright/
│   └── connectors/
├── styles/
├── examples/
├── docs/
└── tests/
```

If the implementation language makes a single-package CLI easier initially, preserve these boundaries conceptually even before splitting physical packages.

---

## 20. MVP

The first useful release should prove the **career source → job → tailored resume** loop before attempting broad auto-apply.

### MVP 0 — Career builder

- Create/open a seriemaCV project.
- Structured career builder.
- Versioned career YAML schema.
- Live resume preview.
- 2–3 ATS-safe styles.
- Markdown, HTML, PDF and DOCX export; legacy `.doc` is out of scope.
- CLI edit/validate/render commands.

### MVP 1 — Career knowledge + AI

- Structured achievements/evidence.
- AI provider abstraction.
- Resume improvement proposals with diff/accept/reject.
- Translation without changing facts.
- Cover letter generation.
- MCP read access to career context.

### MVP 2 — Job workspace

- Add job from URL or text.
- Requirement extraction.
- Evidence-based compatibility report.
- Resume tailoring per job.
- Job/application tracker.
- MCP job/match tools.

### MVP 3 — Application assistant

- Playwright browser launcher.
- Field discovery and deterministic autofill.
- Reusable answers.
- AI suggestions for free-text questions.
- Resume attachment.
- Review-before-submit workflow.

### Post-MVP

- Job search connectors and scheduled scouting.
- Browser adapters for popular ATS platforms.
- Plugin SDK.
- Optional encrypted sync.
- Mobile/read-only companion.
- Interview preparation from the exact job + application history.
- Application analytics.

---

## 21. What not to build initially

To keep the project achievable, v1 should avoid:

- A proprietary rich-text resume format.
- A hosted social network/profile service.
- Fully autonomous mass application.
- A large collection of brittle website-specific scrapers.
- An internal LLM runtime.
- Complex vector infrastructure before retrieval quality demands it.
- Cloud accounts/sync as a requirement.

---

## 22. Differentiation

seriemaCV should not position itself as “another AI resume builder.” Its stronger category is:

**A programmable, local-first career workspace for humans and agents.**

The differentiators are the combination of:

- Human-owned YAML career source.
- Verified reusable career evidence.
- Explainable job compatibility.
- Provider-agnostic AI.
- CLI automation.
- MCP-native agent access.
- Resume variants tied to actual jobs.
- Playwright-assisted application.
- A workflow that remains useful without AI.

---

## 23. Naming system

Recommended public brand:

# **seriemaCV**

Primary product name in UI: **seriemaCV**

Suggested component names:

| Component | Name |
|---|---|
| Desktop application | seriemaCV Studio |
| CLI | `seriemacv` |
| MCP server | `seriemacv-mcp` |
| Job discovery | Scout |
| Compatibility report | Match |
| Resume variants | Tailor |
| Browser application workflow | Apply |
| Career fact store | Career Library |

Possible command language then becomes naturally concise:

```text
Scout this role.
Match against my profile.
Tailor a resume.
Prepare the application.
```

---

## 24. Suggested first technical milestone

The best vertical slice is not the browser automation. It is:

```text
career.yml
   +
career evidence
   +
job description
   ↓
explainable match
   ↓
tailoring diff
   ↓
job-specific generated resume
   ↓
PDF
```

This validates the most important domain abstractions while producing something immediately useful. The same core can then power the GUI, CLI, MCP tools, and later Playwright flow.

### Definition of done

A user can create a career project, maintain a canonical career YAML, import a job,
get an evidence-backed match report, accept selected structured resume changes, and
export a visually polished job-specific Markdown, DOCX or PDF without modifying the
canonical career source.

---

## 25. Product identity direction

The seriema mascot should feel **alert, fast, slightly opinionated, and professional rather than corporate**.

A useful visual metaphor is the bird scanning the horizon for opportunities. Unlike the generic “AI sparkle” aesthetic, the product identity can use the seriema's crest, long legs, and silhouette as recognizable UI motifs.

Potential microcopy:

> **Scout found a strong match.**

> **No evidence found for this requirement. Add context or leave it out.**

> **Tailoring changed emphasis, not facts.**

> **Application ready for review.**

The mascot can have personality; the actual career data and matching UI should remain precise and restrained.

---

## 26. North-star architecture rule

**seriemaCV owns the career context; agents borrow it.**

The user's professional history should not live primarily in a model prompt, a provider account, or browser automation code. It lives in the seriemaCV project as portable, inspectable data.

That single decision allows the same career context to be used by the editor, CLI, MCP, AI providers, match engine, Playwright workflow, and future plugins without coupling the product to any one interface or model.
