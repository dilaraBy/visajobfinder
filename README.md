# VisaJobFinder: Evidence-Backed Visa-Risk Triage

**Live dashboard:** <https://dilarabayram.com/visajobfinder/> — set a visa profile, browse labelled jobs, or paste any job ad at [`/check`](https://dilarabayram.com/visajobfinder/check).

VisaJobFinder is an evidence-backed visa-risk triage project for international students in the UK.

It is not a legal eligibility checker. It is a decision-support tool that highlights sponsor-register matches, right-to-work wording, sponsorship wording, missing evidence, and status-aware risks so users can decide whether to apply, verify first, or move on.

## Current Status

Implemented:

- deterministic Python visa-risk engine;
- sponsor-register CSV parsing, name normalisation, provenance metadata, and fuzzy matching;
- job-description phrase scanner with evidence spans;
- status-aware rules for Graduate Route and sponsorship-before-start users;
- CLI paste checker;
- static sample `jobs.json` builder;
- fixture-first source adapters for Reed, Adzuna, Greenhouse, and Lever;
- evaluation runner for both synthetic sample data and the real public-ad seed schema;
- browser paste-checker UI (`frontend/`, React + TypeScript + Vite) that runs a
  TypeScript port of the deterministic engine fully client-side, with an
  evidence panel, sponsor-register match, what-to-verify, and limitations;
- a Python↔TypeScript parity harness so the in-browser engine cannot silently
  drift from the Python source of truth;
- live Reed and Adzuna fetching (credential-gated via a local `.env`), with
  per-job freshness/staleness tracking and optional dead-link checking;
  individual source failures are recorded but do not break the build;
- the **real GOV.UK Register of Licensed Sponsors** wired into both the pipeline
  and the browser paste-checker: 126,350 deduplicated organisations from the
  2026-06-04 snapshot. See [docs/SPONSOR_REGISTER.md](./docs/SPONSOR_REGISTER.md)
  for provenance and the build step.

- a **dashboard** (Phase 5 thin slice): two-pane job list + evidence detail at
  `/`, reusing the parity-locked engine to classify each `jobs.json` listing for
  the browser-local visa profile, with a `/check` paste-checker route, light/dark
  theme, and React Router. Built with Tailwind CSS + shadcn-style components.

Not yet implemented:

- dashboard **filters/sort, local tracking, and export/import** (next Phase 5
  pass — the current slice is list + detail + profile);
- automated/scheduled GOV.UK sponsor-register download (the current snapshot is
  refreshed manually by re-running `scripts/build_sponsor_register.py`);
- live Greenhouse/Lever board fetching (still fixture-only) and the scheduled
  GitHub Actions automation for daily refresh;
- the full 150-200 item labelled dataset (a 20-record real seed exists; see
  [docs/DATASET_COLLECTION_CHECKLIST.md](./docs/DATASET_COLLECTION_CHECKLIST.md)
  for the collection plan).

The UI keeps all personal data (visa situation, toggles, expiry month, theme) in
browser `localStorage` only; it makes no network calls other than loading the
static `sponsors.json` and `jobs.json` snapshots. Run it with:

```powershell
# The dashboard serves frontend/public/jobs.json. Build the data, then copy it:
python -m pipeline.build_jobs --source-adapter reed:live --source-adapter adzuna:live --results 50 --sponsor-register .\data\sponsor_register\sponsors.csv --output .\frontend\public\jobs.json
python scripts\build_sponsor_register.py   # writes frontend/public/sponsors.json
cd frontend; npm install; npm run dev
```

(Or build to `data/public/jobs.json` and copy it into `frontend/public/`.) The
register vulnerabilities reported by `npm audit` are all in the dev/test
toolchain (vite/vitest/esbuild, dev-server only) and do not ship in the static
production build.

The current public jobs file is a manually-run snapshot of live Reed and Adzuna
listings (94 jobs, built 2026-06-10). It is refreshed manually until the
scheduled daily refresh lands, so listings can be stale — each job shows its
measured age or an explicit "no posting date".

## Problem

International students often waste time applying to UK jobs where visa constraints only become clear late in the process. Existing sponsor-focused tools help, but they can miss a key nuance: Graduate Route holders can usually work now without sponsorship, while still needing to think about future Skilled Worker conversion.

## v1 Scope

- Fresh graduate and junior job listings from maintainable sources.
- Official GOV.UK sponsor-register matching with visible source provenance.
- Job-description phrase scanning for right-to-work, sponsorship, citizenship, and security-clearance signals.
- Status-aware labels for Graduate Route users and users who need sponsorship before starting.
- Evidence panel for every label.
- Local-only profile and tracking data.
- Paste-a-job checker for listings not covered by the dashboard.
- Public evaluation metrics from a labelled job-description set.

## Usage Commands

Run commands from the repository root in PowerShell.

Sponsor-register load smoke check:

```powershell
python -c "from pathlib import Path; from pipeline.sponsor_register.matcher import SponsorMatcher; path=Path('data/sponsor_register/sample_sponsors.csv'); assert path.exists(), 'Missing sponsor-register CSV: ' + str(path); matcher=SponsorMatcher.from_csv(path); match=matcher.match('Example Ltd').to_dict(); print('Loaded', len(matcher.records), 'sponsor record(s). Example Ltd ->', match['matched_name'], '(' + match['confidence_band'] + ')')"
```

Build the real sponsor-register artifacts from a GOV.UK snapshot (deduplicated
CSV for the pipeline + `sponsors.json` for the browser):

```powershell
python scripts/build_sponsor_register.py
```

Build the static dashboard source file from sample source data (uses the small
sample register for a fast, offline smoke build):

```powershell
python -m pipeline.build_jobs --source-file .\data\sources\sample_jobs.json --sponsor-register .\data\sponsor_register\sample_sponsors.csv --output .\data\public\jobs.json
```

Build from fixture-backed source adapters:

```powershell
python -m pipeline.build_jobs --source-adapter reed --source-adapter adzuna --source-adapter greenhouse --source-adapter lever --sponsor-register .\data\sponsor_register\sample_sponsors.csv --output .\data\public\jobs.json
```

Build from **live** Reed + Adzuna (requires credentials). Copy `.env.example`
to `.env` and fill in `REED_API_KEY`, `ADZUNA_APP_ID`, and `ADZUNA_APP_KEY`
(the `.env` file is gitignored; real shell/CI environment variables take
precedence). Then:

```powershell
python -m pipeline.build_jobs --source-adapter reed:live --source-adapter adzuna:live --results 50 --check-links --sponsor-register .\data\sponsor_register\sponsors.csv --output .\data\public\jobs.json
```

- `--results N` sets how many listings to request (capped per source: Reed 100,
  Adzuna 50).
- Each job record gets a `freshness` block (`age_days`, `is_stale`,
  `has_posted_date`) against `--stale-after-days` (default 30), and the output
  includes a `freshness_summary`.
- `--check-links` makes one request per job URL and records `link_status` plus a
  `link_summary` (omit it to skip network link checks).
- A failing source is reported as an error `source_run` and skipped; the build
  still completes with the remaining sources.

Run the synthetic sample eval:

```powershell
python -m pipeline.eval.run_eval --dataset .\data\eval\labelled_jobs.sample.json --sponsor-register .\data\sponsor_register\sample_sponsors.csv
```

Run the real public-ad seed eval:

```powershell
python -m pipeline.eval.run_eval --dataset .\data\eval\labelled_jobs.real.json --sponsor-register .\data\sponsor_register\sample_sponsors.csv
```

Run the paste checker:

```powershell
python -m pipeline.cli.paste_check --title "Graduate Analyst" --employer "Example Ltd" --location "London" --salary "GBP 35,000 per year" --visa-situation graduate_route --needs-future-sponsorship --description "Graduate analyst role. Candidates must have the right to work in the UK." --sponsor-register .\data\sponsor_register\sample_sponsors.csv
```

For longer descriptions, pipe text into the command:

```powershell
Get-Content .\pipeline\fixtures\sample_job_description.txt | python -m pipeline.cli.paste_check --title "Graduate Analyst" --employer "Example Ltd" --visa-situation needs_sponsorship_before_start --salary "GBP 35,000 per year" --sponsor-register .\data\sponsor_register\sample_sponsors.csv
```

The CLI prints readable JSON plus a human-readable summary by default. Use `--output json` or `--output summary` when only one format is needed. See [pipeline/cli/USAGE.md](./pipeline/cli/USAGE.md) for more examples and failure-action notes.

## Evaluation Snapshot

Smoke-test suite:

- `pytest -q`
- synthetic sample eval: 7 records / 14 classification cases

Real seed eval:

- dataset: `data/eval/labelled_jobs.real.json`
- 20 public-ad excerpts / 40 status-specific classification cases
- fixture-backed sponsor labels are included; they are not live GOV.UK coverage claims
- intended as a seed set, not a final quality claim

Current measured results on this 20-record seed (not a general accuracy claim —
the sample is small and the 150-200 item set is still being collected):

- graduate_route: exact label 20/20, false-red 0/20, false-green 0/20;
- needs_sponsorship_before_start: exact label 20/20, false-red 0/20, false-green 0/20;
- evidence extraction: 40/40 on labelled evidence cases;
- high-confidence sponsor precision: 3/3 (fixture sponsor data).

See [docs/GRADUATE_RULE_TUNING.md](./docs/GRADUATE_RULE_TUNING.md) for the
before/after on the Graduate Route over-conservatism fix. A separate, clearly
flagged synthetic rule-coverage set lives at `data/eval/synthetic_edge_cases.json`
and must be reported separately from the real seed, never merged into it.

Run:

```powershell
python -m pipeline.eval.run_eval --dataset .\data\eval\labelled_jobs.real.json --sponsor-register .\data\sponsor_register\sample_sponsors.csv
```

The real seed metrics should be published honestly, including false red, false green, verify-first, unknown, and evidence extraction rates. Do not claim the engine is "accurate" without defining the metric and dataset.

## Labels

| Label | Meaning |
|---|---|
| Worth applying | No detected visa blocker for the selected user situation. Verify with the employer. |
| Verify first | Potentially viable, but important information is missing or ambiguous. |
| Likely blocked | Strong evidence suggests this user should not spend time applying. |
| Unknown | The system does not have enough reliable evidence. |

## Architecture

- A scheduled pipeline fetches public job data, deduplicates listings, matches employers to the sponsor register, scans visa phrases, and writes a static `jobs.json`.
- The planned frontend fetches `jobs.json` and keeps the user's profile, notes, and tracking data in browser storage.
- No CV upload, no auto-apply, no account system in v1.

## Portfolio Story

This project is intended to show end-to-end product judgment:

- identify a specific international-student job-search pain point;
- turn it into conservative, evidence-backed decision support;
- avoid legal-certainty claims and broad scraping;
- measure real failure modes instead of hiding behind AI labels;
- ship a thin usable slice first: paste checker, evidence panel, and honest metrics.

## Documentation

- [Product Plan](./Visa_Aware_Job_Dashboard_Plan.md)
- [Project Decisions](./docs/PROJECT_DECISIONS.md)
- [Product Spec](./docs/PRODUCT_SPEC.md)
- [Visa Engine Spec](./docs/VISA_ENGINE_SPEC.md)
- [Data Contracts](./docs/DATA_CONTRACTS.md)
- [Labelling Guide](./docs/LABELLING_GUIDE.md)
- [Evaluation Plan](./docs/EVALUATION_PLAN.md)
- [User Research Plan](./docs/USER_RESEARCH_PLAN.md)
- [Roadmap](./docs/ROADMAP.md)
- [Claude Instructions](./CLAUDE.md)
- [Agent Instructions](./AGENTS.md)

## Portfolio Angle

This project should demonstrate problem discovery, domain understanding, data engineering, applied AI restraint, user-centred product design, and measurable evaluation.
