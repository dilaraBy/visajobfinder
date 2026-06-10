# TODO.md — VisaJobFinder Completion Plan

Last updated: 2026-06-10.

## Why this file exists

The project goal is **not** technical perfection. The goal is a portfolio artefact that proves to recruiters:

1. I identified a real problem (international students waste applications because visa signals are unclear and Graduate Route nuance is missed by sponsor-only tools).
2. I worked out what a solution needs (evidence-backed triage, official data, status-aware rules, honest measurement).
3. I implemented it end-to-end and measured it honestly.

**Current state, brutally:** the engineering is ~70% done and good; the *story* is ~20% done. The engine, register matching, parity harness, paste checker, and a thin dashboard exist and work. But there is no git history, no public URL, no user research evidence, and an eval set of only 20 records scoring 100% (which reads as overfitting, not quality). The remaining work is mostly **shipping and narrative, not code**.

Priority order below is deliberate: visibility first, credibility second, features third, polish last. Do not reorder.

---

## Phase A — Make the project exist publicly (highest priority)

A portfolio project that is not on GitHub with a live URL does not exist.

### A1. Initialise git and publish to GitHub
- [x] `git init`, add a proper `.gitignore` (node_modules, dist, __pycache__, .pytest_cache, .env, the 11 MB raw GOV.UK CSV — keep only the build script + derived `sponsors.csv` if size allows, or document the download step).
- [x] First commit: current state, with a clear message. Then commit **in meaningful units** going forward (one feature/fix per commit) so the history shows process.
- [x] Create GitHub repo `visajobfinder` and push — created **private** for now at github.com/dilaraBy/visajobfinder (Dilara's choice); must flip to public before the portfolio launch (Phase E) for the acceptance criterion to hold.
- [x] Verify `.env` and any API keys are NOT in history before pushing.
- **Acceptance:** repo is public, README renders, no secrets, no >50 MB files.
- **Effort:** 1–2 hours. **Agent:** release-engineer.

### A2. Deploy the frontend
- [ ] Build the frontend (`npm run build`) and deploy `frontend/dist` to GitHub Pages or Cloudflare Pages.
- [ ] Ensure `jobs.json` and `sponsors.json` are served and the dashboard + `/check` route work on the public URL (configure SPA fallback / base path for the router).
- [ ] Add the public URL to the README top section.
- **Acceptance:** a stranger can open one URL, set a visa profile, see labelled jobs, and paste a job at `/check`.
- **Effort:** half a day (router base-path issues are the usual trap). **Agent:** frontend-engineer.

### A3. Scheduled daily refresh (GitHub Actions)
- [ ] Workflow: daily cron → run `pipeline.build_jobs` with live Reed + Adzuna (keys as repo secrets) → write `frontend/public/jobs.json` → commit or upload as Pages artefact → redeploy.
- [ ] Source failure must not break the deploy (the pipeline already isolates failures — keep it that way).
- [ ] Show "data updated <date>" visibly in the dashboard UI.
- **Acceptance:** dashboard shows yesterday-or-newer data without manual action for 7 consecutive days.
- **Effort:** half a day. **Agent:** release-engineer.

### A4. Fix the freshness dead-end
Current live data: 49 Reed jobs, **all** `missing_date`, so the freshness feature displays nothing.
- [x] Check the Reed adapter's date field mapping (Reed returns `date` as posted date — verify parsing). Root cause: Reed returns `DD/MM/YYYY`, the adapter passed it through unconverted and freshness only parses ISO. Fixed with `_iso_date()` (ISO + UK day-first, junk → None); Reed fixture now mirrors the real API format so the suite catches format regressions.
- [x] Add Adzuna live to the default build (it provides `created` timestamps). Also fixed: `where="United Kingdom"` failed Adzuna geocoding and silently returned 0 results — country-wide search now omits `where`.
- [x] If a source genuinely lacks dates, show "date unknown" honestly rather than an empty freshness block. (Frontend already did this; unparseable dates now become `null` at the adapter instead of junk text.)
- **Acceptance:** majority of dashboard jobs show real age; `freshness_summary.missing_date` is a minority. **Measured 2026-06-10:** 94 live jobs (Reed 50 + Adzuna 50, deduped) → 59 fresh, 35 stale, 0 missing_date.
- **Effort:** 2–4 hours. **Agent:** pipeline-engineer.

---

## Phase B — Credibility lockdown (the metrics must survive scrutiny)

A 20-record seed at 100% is a liability. Your own EVALUATION_PLAN.md says 150–200. Anyone technical will check.

### B1. Grow the labelled dataset to 150–200 real records
- [ ] Follow `docs/DATASET_COLLECTION_CHECKLIST.md` exactly (target mix: ~40 sponsor-positive, ~40 hard blockers, ~40 ambiguous, ~30 graduate schemes/internships; sources spread across Reed, Adzuna, Greenhouse, Lever, direct pages).
- [ ] Collect in batches of 25; run the eval after each batch and log results per batch in `docs/EVAL_LOG.md` (date, batch size, metrics). This produces an honest "metrics over time" story and shows the rules were NOT tuned on the test set after collection started — that is the credibility claim.
- [ ] Freeze rules per batch: tune rules only on already-seen batches, never on the newest unseen batch before its first scored run.
- [ ] Label per `docs/LABELLING_GUIDE.md`; both visa situations per record; evidence spans labelled.
- **Acceptance:** ≥150 records; eval runs clean; metrics reported per EVALUATION_PLAN targets (sponsor precision ≥95%, GR false-red <5%, false-green <10%, evidence ≥85%) — and **if a target is missed, publish the miss**. A published 88% with failure analysis is worth more than a suspicious 100%.
- **Effort:** the single biggest time block — roughly 10–15 min/record ≈ 25–35 hours. Split across sessions; batches make it tractable. **Agent:** eval-curator (collection can be assisted, labels are human-confirmed by Dilara).

### B2. Failure-case gallery
- [ ] Add `docs/FAILURE_CASES.md`: 8–12 real examples where the engine is wrong, over-conservative, or misses evidence — with the exact phrase, what the engine said, what a human says, and why.
- [ ] Link it from the README. This is counterintuitive but it is the strongest trust signal in the whole project.
- **Effort:** 2–3 hours once B1 batches exist. **Agent:** eval-curator.

### B3. Run eval against the real register, not the sample
- [ ] README eval commands currently use `sample_sponsors.csv`. Re-run and report against the full 126,350-org `sponsors.csv`; report both if results differ.
- [ ] Re-check sponsor-precision examples against the real register (false-match risk goes up with 126k names).
- **Effort:** 1–2 hours. **Agent:** eval-curator.

---

## Phase C — User research (the "problem identification" evidence)

The plan has always said this is the portfolio story. Zero interviews have happened. Without this, "I identified a problem" is an assertion, not a finding.

### C1. Interview 5 international students
- [ ] Use `docs/USER_RESEARCH_PLAN.md` questions as written. Recruit from your own university network / international-student societies / group chats — 20–30 min each, notes are fine, recordings unnecessary.
- [ ] Collect 3 real job ads each person was unsure about (these also feed B1).
- [ ] Write `docs/USER_RESEARCH_FINDINGS.md`: per-interview summary, recurring confusing phrases, quotes (anonymised), and what changed in the product because of them.
- **Acceptance:** 5 documented interviews; at least 2 concrete product changes traced to findings (e.g. label wording, a new phrase rule from a real ad).
- **Effort:** ~1 week elapsed, ~6 hours active. **Agent:** Dilara does the interviews; research-story agent structures notes into findings.

### C2. Usability pass with the live URL
- [ ] After A2: have 3–5 of the same students use the deployed dashboard + paste checker. Tasks from EVALUATION_PLAN.md §User Testing.
- [ ] Log confusion points, fix the top 3 (copy and evidence-visibility fixes only — no new features).
- **Effort:** 1 week elapsed, ~4 hours active. **Agent:** Dilara + frontend-engineer for fixes.

---

## Phase D — Finish the dashboard v1 slice (features users actually need)

Only the missing Definition-of-Done items. Nothing else.

### D1. Filters and sorting
- [ ] Filter by label, source, location text, freshness; sort by date and label severity. Client-side, plain controls, dense layout per CLAUDE.md UI principles.
- **Effort:** half a day. **Agent:** frontend-engineer.

### D2. Local tracking + export/import
- [ ] Per-job status (interested / applied / rejected / offer), note, deadline — `localStorage` only.
- [ ] Export all local data as one JSON file; import restores it. No network calls.
- **Effort:** 1 day. **Agent:** frontend-engineer.

### D3. Evidence highlighting in dashboard detail
- [ ] Reuse `HighlightedDescription` from the paste checker in the dashboard `JobDetail` so matched phrases are visibly highlighted in context (if not already wired).
- **Effort:** 1–2 hours. **Agent:** frontend-engineer.

### D4. Editorial design identity pass (after A2 deploy)
Current look is the default shadcn/Tailwind starter aesthetic — instantly recognisable as AI-generated. Replace with an **editorial / print-inspired identity**: serif display headings, strong typographic hierarchy, hairline rules instead of rounded cards, restrained ink-on-paper palette with one accent colour. Keep the existing token architecture (`index.css`) — this is a restyle, not a rebuild.
- [ ] New type pairing (serif display + readable sans/serif body) via self-hosted fonts; no default font stack.
- [ ] Retoken palette: paper/ink neutrals, one accent; keep label colours colour-blind safe and text-paired.
- [ ] Replace card-grid feel with rule-separated list rows; sharpen or remove radii; rework `LabelChip` away from generic pills.
- [ ] Keep density, evidence visibility, and accessibility (contrast, focus states) — verify against CLAUDE.md UI principles.
- [ ] Use the repo's `.claude/skills/ui-ux-pro-max` skill for typography/palette selection.
- **Acceptance:** side-by-side screenshot no longer reads as a shadcn starter; all frontend tests still pass.
- **Effort:** 1–1.5 days. **Agent:** frontend-engineer.

### Explicitly NOT in scope (resist the urge)
- No accounts, CV upload, auto-apply, email digests, LinkedIn/Indeed scraping, LLM judge, employer portal. The LLM-judge layer stays deferred — the deterministic story is stronger and cheaper to defend in an interview.

---

## Phase E — Portfolio packaging (this is what recruiters actually see)

### E1. Rewrite README as a case study
Structure: Problem (with user-research evidence) → What I decided a solution needs → Architecture (one diagram) → The engine (evidence example screenshot) → Evaluation (real metrics incl. misses, link to failure cases) → Limitations → What I'd do next.
- [ ] Replace 100%-on-20-records claims with the B1 metrics and per-batch log.
- [ ] Add 2–3 screenshots and the architecture diagram (simple: sources → pipeline → static JSON → browser engine; personal data never leaves the browser).
- **Effort:** half a day. **Agent:** research-story.

### E2. 60–90 second demo
- [ ] Screen recording: set profile → see labels → open evidence → paste an external ad → show a *conservative* result and explain why conservative is correct. Link or GIF in README.
- **Effort:** 2 hours. **Agent:** Dilara records; research-story scripts it.

### E3. LinkedIn / CV bullet
- [ ] One post + one CV bullet using the PROJECT_DECISIONS.md narrative, with the real measured numbers. (Use the cv-tailoring skill for the CV bullet.)
- **Effort:** 1 hour. **Agent:** research-story.

---

## Sequencing and dependency notes

```
A1 → A2 → A3          (exist → deploy → automate)
A4 anytime            (small, do early)
B1 starts immediately, runs in background batches throughout
C1 starts immediately (calendar time dominates) ── feeds ads into B1
C2 needs A2
D1–D3 after A2, parallel with B1 batches
B2, B3 after B1 ≥ 100 records
E1–E3 last, need B + C results
```

Realistic total: **4–6 part-time weeks**, dominated by B1 labelling and C1/C2 calendar time. Everything else is ~5–6 focused days of work.

## Definition of Done (v1, final)

- [ ] Public GitHub repo with meaningful commit history.
- [ ] Public URL, daily-refreshed data, visible update timestamp.
- [ ] ≥150-record labelled eval set; metrics published honestly, including misses and a failure-case gallery.
- [ ] 5 user interviews + usability findings documented, with traced product changes.
- [ ] Dashboard: filters, sorting, tracking, export/import, evidence highlighting.
- [ ] README reads as a case study; demo video exists.
- [ ] Every label everywhere still uses conservative signal language (see CLAUDE.md) — final sweep before calling it done.
