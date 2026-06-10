# CLAUDE.md

This file gives Claude Code project-specific instructions. Follow it before making implementation decisions.

## Product Truth

This project is a visa-risk triage dashboard for international students in the UK. It must never behave like a legal eligibility oracle.

Use conservative signal language:

- Worth applying
- Verify first
- Likely blocked
- Unknown

Do not generate copy that says:

- "You are eligible"
- "You can apply"
- "This role is safe"
- "This company will sponsor you"
- "This replaces immigration advice"

Preferred wording:

- "No detected blocker"
- "Verify with employer"
- "Sponsor-register match found"
- "Evidence is ambiguous"
- "Likely blocked for this visa situation"

## Core v1 Features

Prioritise these before anything else:

1. Sponsor-register matching.
2. Deterministic job-description phrase scanning.
3. Status-aware decision rules.
4. Evidence display for every label.
5. Paste-a-job checker.
6. Static dashboard with filters.
7. Local-only tracking and export/import.
8. Evaluation scripts and labelled test data.

Avoid v1 scope creep:

- no accounts;
- no CV upload;
- no auto-apply;
- no email digests;
- no LinkedIn or Indeed scraping;
- no employer portal;
- no generic AI cover-letter tool.

## Technical Preferences

Recommended stack:

- Frontend: React, TypeScript, Vite.
- Pipeline: Python.
- Entity matching: RapidFuzz or equivalent transparent fuzzy matcher.
- Data output: static JSON.
- Scheduler: GitHub Actions.
- Hosting: static hosting.

If a different stack already exists, follow the existing codebase unless it undermines the product requirements.

## Data Principles

Public server-side data may include:

- job title;
- employer name;
- job description;
- source URL;
- location;
- salary text;
- source metadata;
- sponsor-register match metadata.

Personal data must stay browser-local in v1:

- visa status;
- visa expiry month;
- target cities;
- saved jobs;
- notes;
- deadlines.

Do not add analytics or telemetry without documenting what is collected.

## Visa Engine Rules

Always preserve evidence. A classification without evidence is not acceptable.

Engine outputs should include:

- `label`;
- `reason`;
- `evidence`;
- `employer_match`;
- `confidence`;
- `what_to_verify`;
- `limitations`.

Low confidence must remain visible to the user.

Deterministic rules beat LLM output. The LLM may only handle ambiguous cases and must cite exact phrases.

## UI Principles

The UI should feel like a serious job-search workbench, not a marketing landing page.

Prioritise:

- dense but readable job list;
- obvious labels;
- visible evidence;
- fast filtering;
- plain language;
- no decorative clutter.

Every job card should show:

- title;
- employer;
- location;
- source;
- freshness;
- label;
- one-line reason;
- key evidence if available.

Every job detail page should show:

- label and reason;
- employer sponsor-register match;
- exact matched phrase;
- salary/start-date concerns if available;
- what the user should verify;
- original apply link.

## Evaluation Requirement

Before claiming success, create and run an evaluation set of 150-200 real job descriptions.

Track:

- false red rate;
- false green rate;
- sponsor match precision;
- evidence extraction accuracy;
- unknown rate;
- dead-link/stale rate.

README claims must match measured results.

## Implementation Style

- Keep modules small and testable.
- Separate source fetching, normalisation, matching, scanning, classification, and rendering.
- Keep decision rules readable.
- Prefer explicit rule tables over hidden prompt logic.
- Add tests around edge cases, not just happy paths.
- Do not silently swallow classification uncertainty.

## Useful Docs

Read these before building:

- `Visa_Aware_Job_Dashboard_Plan.md`
- `docs/PRODUCT_SPEC.md`
- `docs/VISA_ENGINE_SPEC.md`
- `docs/DATA_CONTRACTS.md`
- `docs/EVALUATION_PLAN.md`
- `docs/ROADMAP.md`
