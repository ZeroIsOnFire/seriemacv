# Assisted applications

`applications/<id>.yml` is the local, canonical record of one application. It links
a structured job, an optional resume variant, attachments, confirmed answers, and
unresolved form questions. It never stores passwords, cookies, or submitted form
values in diagnostics.

```powershell
seriemacv applications create .\my-career --id platform-application --job-id platform-role --variant-id platform-role --url https://example.invalid/apply
seriemacv applications validate .\my-career
seriemacv applications prepare .\my-career platform-application --interactive
seriemacv applications questions .\my-career platform-application
seriemacv applications apply-answer .\my-career platform-application question-why --answer "..." --save-answer-id why-platform
seriemacv applications set-status .\my-career platform-application applied
```

`prepare --interactive` opens an isolated persistent browser profile at
`.seriemacv/browser`. Login is performed manually. The generic preparer fills only
safe profile values and non-sensitive saved answers, then creates questions for
required unresolved fields. It never fills legal statements, work authorization,
salary, demographic, or self-identification fields.

An external MCP agent can read applications and their questions and request a
reviewable answer proposal. The user must explicitly apply an answer through the
CLI; `--save-answer-id` additionally saves that confirmed answer in `career.yml`.
Sensitive answers may be saved, but are never reused automatically.

For forms with inconsistent labels or a cover letter, use the optional external-agent
workflow. `prepare --ai-assisted` includes unresolved optional fields in the question
queue. The request deliberately carries only the job identity, detected field labels,
and verified evidence; it excludes contacts, passwords, cookies, and form values.

```powershell
seriemacv applications prepare .\my-career platform-application --interactive --ai-assisted
seriemacv applications ai-preview .\my-career platform-application --request-id platform-form
seriemacv applications ai-request .\my-career platform-application --request-id platform-form --output .\platform-form-request.yml
# Ask Codex, Claude Code, or another local agent to return a response YAML.
seriemacv applications ai-review .\my-career .\platform-form-request.yml .\platform-form-response.yml
seriemacv applications ai-apply .\my-career .\platform-form-request.yml .\platform-form-response.yml --accept why-answer --accept cover-letter
```

`ai-preview` prints the exact request YAML without writing it or sending data. Review
it before sharing it with an external agent; the subsequent `ai-request` file has the
same content.

The response can map semantic field names and propose a separate cover letter, but
every accepted item is selected individually. The agent cannot propose answers for
sensitive fields. Run `prepare` again after accepting answers to fill the approved
values in the local browser session.

There is no submission command. Review the page and submit it yourself in the
browser, then record `applied`. Use `clear-browser-profile` to remove the isolated
browser profile.
