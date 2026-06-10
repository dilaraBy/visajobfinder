# Phase 5 — Dashboard Frontend Plan

Status: **In progress.** Thin vertical slice shipped; filters/tracking/export next.

## Implementation status

Done (thin slice):
- Tailwind CSS v4 + shadcn-style primitives (`src/components/ui/`), `@` path alias.
- App shell with top bar, Dashboard/Paste-Checker nav, profile chip, light/dark
  theme toggle (persisted in `localStorage`). React Router (`/`, `/check`).
- Data layer (`src/lib/jobs.ts`): loads `jobs.json`, maps records to the engine,
  and classifies each job for the local profile via the **precomputed**
  `employer_match` + `phrase_signals` (no in-browser matching). Memoised on
  profile change. Tested in `src/lib/jobs.test.ts`.
- Two-pane layout: left = profile + job list (cards with label chip, reason,
  freshness, key evidence); right = evidence detail reusing `ResultPanel`.
  Selection is deep-linkable via `?job=<id>`. Honest freshness (undated/
  unverified listings clearly marked).
- `frontend/src/engine/` untouched; all 305 frontend tests + parity green.

Not yet (next pass): search box, filters (label/source/city/stale/sponsor-only),
sort, local tracking + `/tracked` view, export/import, full mobile polish.

> Deploy note: `BrowserRouter` needs the host to rewrite unknown paths to
> `index.html` (SPA fallback). On GitHub Pages add a `404.html` copy or switch to
> `HashRouter`.

---


## Decisions locked

- **Stack:** React + TypeScript + Vite (existing `frontend/`). Vite compiles to
  static HTML/CSS/JS → deploys to any static host (GitHub Pages / Netlify /
  Vercel / Cloudflare Pages). No server. Reuses the parity-tested TS engine.
- **Layout:** two-pane split view (list left, evidence detail right).
- **Visual tone:** friendly & calm — soft neutrals, generous spacing, rounded
  cards, clear type. Approachable for non-technical users, still evidence-first.
- **Styling toolkit:** Tailwind CSS + shadcn/ui (we own the component code).
- **Theme:** light default with a dark-mode toggle.

## Product guardrails (from CLAUDE.md / AGENTS.md)

- Conservative labels only — never "eligible", "safe", "can apply", "will
  sponsor". We use: **Worth applying** (no detected blocker; verify), **Verify
  first**, **Likely blocked**, **Unknown**.
- Every label shows evidence or a missing-evidence explanation.
- Personal data (profile, saved jobs, notes, deadlines) stays in the browser.
  No accounts, no telemetry.
- Freshness shown honestly; stale/undated listings clearly marked.
- Differentiator vs competitors (e.g. Hunt UK Visa Sponsors, which gates jobs
  behind login and labels jobs binary "Ineligible"): no login, local-only,
  evidence-backed conservative labels.

## Architecture / data flow

The pipeline already does the expensive work and writes it into `jobs.json`:
each job carries `visa_signals.employer_match` and `visa_signals.phrase_signals`
plus `freshness`, `dates`, `salary`, `location`, `url`.

Browser flow:
1. Fetch static `jobs.json`.
2. Read the browser-local visa profile (reuse paste-checker `VisaProfileForm` +
   `useLocalStorage`).
3. For each job, run the **existing TS `classifyJob`** using the precomputed
   `employer_match` + `phrase_signals` from `jobs.json` and the local profile →
   produces the per-user label/reason/evidence. (Matching is NOT re-run in the
   browser.)
4. Re-classify (memoised) whenever the profile changes.

The engine in `frontend/src/engine/` is the parity-locked source of truth and
**must not be modified** — only consumed.

## Screens & components

### App shell
- Top bar: product name, **profile chip** (current visa situation, click to
  edit), **data freshness** ("Updated 4 Jun 2026"), theme toggle, link to the
  Paste Checker.
- Routing (add `react-router`): `/` dashboard, `/check` paste checker,
  `/tracked` saved jobs. Selected job deep-linkable via `?job=<id>`.

### Left pane — list & filters
- Search box (title/employer).
- Filters: label (multi-select chips), source, city, "hide stale" toggle,
  "sponsor-register match only" toggle.
- Sort: freshness, label severity.
- Result count ("124 jobs").
- Scrollable **job cards**, each showing: title, employer, location, source,
  freshness badge, **label chip**, one-line reason, and a key-evidence snippet.

### Right pane — evidence detail (reuse paste-checker components)
- Title, employer, location, source, posted date + freshness, salary.
- Label chip + reason; low-confidence note when applicable.
- `EvidencePanel` (found + missing evidence) with phrase highlighting.
- `EmployerMatchPanel` (sponsor match + GOV.UK provenance).
- What to verify; limitations; disclaimer.
- Apply link (http/https-validated).
- **Track controls** (save, status, notes, deadline) — from the Tracking module.
- Empty state when nothing selected; nudge to set visa situation if unset.

### Label visual system (light / dark, accessible)
Colour **plus** text always (colour-blind safe), soft chip backgrounds:
- Worth applying → calm green (emerald)
- Verify first → amber
- Likely blocked → muted rose (clear, not aggressive)
- Unknown → slate/grey
Green means "no detected blocker", never "safe" — copy reinforces this.

### Local tracking & export
- Save a job: stores `job_id` + snapshot (title/employer/url/label-at-save) +
  status (interested / applied / interviewing / closed) + notes + optional
  deadline, in localStorage.
- `/tracked` view to review saved jobs.
- Export: download a JSON of `{ profile, tracked }`. Import: upload + validate
  shape + merge (graceful on malformed files; no code execution).

### Responsive
- Desktop: two panes. Mobile/narrow: list full-width; tapping a card opens the
  detail (back button). Light/dark respected throughout.

## Subagent team & waves (orchestrated; I gate each wave)

**Wave 1 (parallel, disjoint modules):**
- **Dashboard Worker** — Tailwind + shadcn + router setup; app shell; data layer
  (load `jobs.json` + per-profile classify); job cards; filters/sort; two-pane
  layout; detail panel (reusing evidence components); label component system;
  light/dark; responsive. Owns `App`/routing. Exposes a slot in the detail panel
  for tracking controls.
- **Local Tracking & Export Worker** — self-contained `useTracking` hook +
  `<TrackControls jobId/>` + `<TrackedJobsView/>` + export/import, against an
  agreed interface; **no edits to App/layout** (I wire it in).

**Wave 2 (parallel review):**
- **Product/Domain QA** — card/filter/label copy; freshness honesty; colour
  semantics; conservative-language audit.
- **QA/Security** — XSS from **live third-party job text** (now real data);
  export/import file-handling safety; local-only/no-telemetry; dependency review
  of Tailwind/shadcn/router additions.

**Final:** I integrate, run build + full test suite, confirm engine/parity
untouched, update README/docs.

## Sub-decisions to confirm during build
- **Paste-checker styling:** build the dashboard in Tailwind/shadcn now; do a
  light restyle of the existing paste-checker in the same effort so the app
  looks consistent (avoids two visual systems). Alternative: leave paste-checker
  on its current `app.css` for now.
- Whether to load `sponsors.json` at all (not needed for classify since matches
  are precomputed; may keep for a future "employer sponsor lookup").

## Acceptance gates
- `npm run build` clean; all existing 284 tests + new component tests green.
- `frontend/src/engine/` unchanged (parity intact).
- No forbidden copy; labels conservative; stale/undated clearly flagged.
- Local-only: profile + tracking in localStorage; no network beyond `jobs.json`
  (and optionally `sponsors.json`); no telemetry/analytics.
- Live third-party job text rendered safely (no XSS).
- Responsive; light/dark; keyboard-accessible; contrast AA; colour+text labels.
