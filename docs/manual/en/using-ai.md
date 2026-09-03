# Using Seriema with AI

[Back to the complete guide](index.md) · [Português](../pt-BR/uso-com-ia.md)

An AI agent works with a local Seriema project; it does not own the project or make
career facts up. Give it the project location when needed and make the outcome
explicit. Review every proposed canonical change and any sensitive application
answer.

## Start a project from an existing resume

Ask the agent to create the local workspace, then attach or provide the resume:

```text
Create a Seriema project at .\my-career in English using the clean style.
I will attach my current resume. Extract only the facts stated in it into a proposed
career.yml, list missing information, and wait for my review before saving anything.
```

The agent may turn the resume into a reviewable YAML proposal, but it must not infer
dates, employers, skills, metrics, or credentials that are not present in the source.
`career.yml` becomes canonical only after you explicitly accept the proposed facts.

## Verify evidence before using it

Evidence powers compatibility reports, tailored wording, and application answers.
Review it before importing jobs or tailoring a resume:

```text
Show my career evidence and identify statements that need verification. Mark only the
items I confirm as verified; leave inferred or unsupported claims pending.
```

Only verified evidence can support a positive match or a factual claim in a tailored
resume. A missing or unverified item remains a gap rather than an assumed skill.

## Import and evaluate a role

```text
Import this job: https://careers.example.com/jobs/123.
Validate the posting, analyze my compatibility, identify gaps and eligibility risks,
and research a salary expectation with sources.
```

The agent should locate the official posting when possible, create a validated local
job record after approval, and return an explainable match. It must distinguish the
employer's published compensation from a market estimate and unknown information.

## Improve verified career data and regenerate resumes

```text
In my career evidence, add `NoSQL` to every verified item that already mentions
MongoDB or Redis, and add `REST` to items that already mention an API. Then validate
my career and regenerate the English and Portuguese PDF and DOCX resumes.
```

The agent applies the canonical YAML change only when the user explicitly requests
it. It can regenerate artifacts only after the career document validates.

## Prepare an application

```text
Let's apply to platform-engineer. My expectation is BRL 20,000.
First make sure the compatibility analysis is current. Prepare the English resume and
the application answers, ask me about any missing required fields, then open the
application in Playwright for review.
```

The agent must not guess work authorization, visa, demographic, tax, current-pay, or
salary information. It opens the browser so you can log in and inspect the form. It
submits only when you explicitly authorize submission.

## Record the outcome

```text
I submitted the Platform Engineer application. Mark it as applied.
```

The agent updates only the local application record. It should report pending
questions or failures instead of assuming the external application succeeded.

## Privacy boundary

Before sharing a local request with an external AI provider, inspect what it contains.
Seriema proposal requests use verified career evidence and exclude contact details,
passwords, cookies, and browser form values. See [Local AI proposals](proposals.md)
for the provider-neutral YAML exchange.
