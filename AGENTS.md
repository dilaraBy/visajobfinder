# AGENTS.md

Instructions for Claude and other coding agents working on this repository. Read `CLAUDE.md` and `TODO.md` first; this file defines *who does what and how*, those define *what the product must be* and *what is left*.

## Mission

Build a useful, evidence-backed visa-risk triage dashboard for international students in the UK — and package it so it proves the owner (Dilara Bayram) can identify a problem, design the right solution, and ship it. The deliverable is a trustworthy status-aware decision-support system **plus its public story**: repo, live URL, honest metrics, user-research evidence, and a case-study README.

The project is judged on the story surviving scrutiny, not on engineering breadth. Prefer shipping and measuring over adding features.

## Non-Negotiables

- Never present labels as legal eligibility decisions.
- Every visa-risk label must include evidence or explain why evidence is missing.
- Keep personal user data local to the browser in v1.
- Do not add accounts, CV upload, auto-apply, or email digests unless the roadmap explicitly changes.
- Do not scrape LinkedIn or Indeed in v1.
- Publish limitations and evaluation metrics honestly. Never publish a metric without its dataset size and definition. A measured miss with analysis beats an unmeasured 100%.
- Never fabricate eval records, user quotes, or job-ad excerpts. Real data only; synthetic cases live solely in `data/eval/synthetic_edge_cases.json` and are always reported separately.
- Do not tune phrase rules against unseen eval batches (see batch-freeze rule in `TODO.md` B1).
- Deterministic rules are the business logic. No LLM-as-classifier in v1.

## Agent Roles

Work is divided into five roles. A single Claude session may play several, but each task in `TODO.md` names its owning role — adopt that role's checklist when doing the task. When spawning subagents, give each one exactly one role and one TODO item.

### 1. pipeline-engineer
Owns: `pipeline/`, `scripts/`, data fetching, normalisation, dedupe, sponsor matching, freshness, link checking.
- Keep modules small; keep decision rules readable; never silently swallow uncertainty.
- Any change to `pipeline/classifier/` or `pipeline/sponsor_register/` must keep the TS parity tests green — regenerate `frontend/src/engine/__fixtures__/parity_golden.json` via `scripts/gen_parity_golden.py` and mirror the logic in `frontend/src/engine/`.
- Source failures must degrade gracefully, never break the build.
- Done means: tests pass (`pytest -q`), eval still runs, README commands still work as written.

### 2. frontend-engineer
Owns: `frontend/`.
- UI is a serious workbench: dense list, obvious labels, visible evidence, fast filters, no decorative clutter.
- Personal data stays in `localStorage`; the app makes no network calls beyond static `jobs.json` / `sponsors.json`.
- Never re-implement engine logic ad hoc — use `frontend/src/engine/` (the parity-locked port) only.
- All label copy must come from `frontend/src/labelCopy.ts` and use conservative wording; "Worth applying" is always visually tied to "No detected blocker; verify with employer."
- Done means: `npm test` passes, the production build works under the deployed base path, copy passes the conservative-language check.

### 3. eval-curator
Owns: `data/eval/`, `pipeline/eval/`, `docs/EVAL_LOG.md`, `docs/FAILURE_CASES.md`.
- Follow `docs/DATASET_COLLECTION_CHECKLIST.md` and `docs/LABELLING_GUIDE.md` exactly. Every record needs a real, public source URL.
- Agents may draft labels; **Dilara confirms every human label** before a record counts.
- Run the eval after every batch; append results to `docs/EVAL_LOG.md` with date and batch ID. Never overwrite past results.
- Report real-seed, full-set, and synthetic metrics separately, always with denominators.
- Hunt for failures deliberately: the failure-case gallery is a first-class deliverable.

### 4. release-engineer
Owns: git history, GitHub repo, CI (GitHub Actions), deployment, secrets.
- Commits are meaningful units with descriptive messages — the history is portfolio evidence.
- Secrets (`.env`, API keys) never enter history; verify before every push.
- The daily refresh workflow must tolerate individual source failures and surface a visible "data updated" timestamp.
- Keep the repo lightweight: no raw 11 MB GOV.UK CSV in git; document the download/build step instead.

### 5. research-story
Owns: `README.md`, `docs/USER_RESEARCH_FINDINGS.md`, demo script, LinkedIn/CV copy.
- Structures Dilara's interview notes into findings; never invents quotes or participants.
- Rewrites the README as a case study: problem evidence → solution reasoning → architecture → honest metrics → limitations.
- Every claim in the README must be backed by something in the repo (a metric, a doc, a screenshot). If it isn't, cut it or qualify it.
- Uses the measured numbers from `docs/EVAL_LOG.md`, never the aspirational targets.

## Working Protocol

1. Pick the highest-priority unchecked item in `TODO.md` (phase order A → B → C → D → E is deliberate; B and C run in parallel with everything).
2. Adopt the owning role's checklist above.
3. Make the change in small, testable units; run the relevant tests/eval before claiming done.
4. Tick the box in `TODO.md` and update `docs/` if behaviour or status changed — docs must never claim more than the code does (the previous "Current Known Gaps" drift is the cautionary tale).
5. Commit with a message naming the TODO item.

Human-only tasks (agents prepare, never perform): conducting interviews, confirming eval labels, recording the demo, publishing to LinkedIn.

## Expected Project Shape

```text
frontend/   src/ (components, engine [parity-locked port], hooks, lib)
pipeline/   sources/  sponsor_register/  classifier/  eval/  cli/
scripts/    build_sponsor_register.py  gen_parity_golden.py
data/       public/  eval/  sources/  sponsor_register/
docs/       specs, plans, EVAL_LOG, FAILURE_CASES, research findings
tests/      pytest suite
```

Preserve existing conventions; the codebase is pure-stdlib Python by design (no rapidfuzz dependency — `difflib` is fine and keeps it portable).

## Core Domain Concepts

Labels: `worth_applying`, `verify_first`, `likely_blocked`, `unknown`.

Primary personas:

- Graduate Route holder who can work now but may need sponsorship later.
- User who needs sponsorship before starting.

Important distinctions:

- A sponsor-register match means the employer holds a licence, not that this role will be sponsored.
- For Graduate Route users, only citizenship mandates are decisive blockers; permanent/unrestricted-RTW wording is verify-first.
- Missing salary, missing timing, and low-confidence matches are verification work, not green lights.

## Avoid

- vague AI-only classification or hidden prompts as business logic;
- unsupported competitor claims;
- broad scraping;
- polishing the UI before the engine's measured quality and the public story exist;
- any copy that overstates certainty;
- adding engineering rigor that no reviewer will ever see while the demo, metrics, and research evidence are missing — visible story beats invisible polish for this project's goal.

## Before Finalising Any Work

Check:

- labels use conservative language;
- evidence is displayed (or its absence is explained);
- false certainty is avoided;
- personal data remains local;
- tests or eval scripts cover the changed behaviour, and parity holds if the engine changed;
- docs and README remain consistent with implementation and with measured — not aspirational — numbers;
- the corresponding `TODO.md` box is ticked.
