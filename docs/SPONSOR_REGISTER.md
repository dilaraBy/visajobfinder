# Sponsor Register Provenance & Build

This documents how the **real** GOV.UK sponsor register is wired into the
pipeline and the browser app. It is separate from the small sample fixtures used
by tests and the parity harness.

## Source

- **Dataset:** Register of Licensed Sponsors (Workers and Temporary Workers).
- **Publisher:** UK Home Office, via GOV.UK.
- **URL:** https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers
- **Snapshot used:** `2026-06-04_-_Worker_and_Temporary_Worker.csv`
  (published 2026-06-04).
- **Raw headers:** `Organisation Name, Town/City, County, Type & Rating, Route`.
- **Raw rows:** 141,697 (one row per organisation × route).

The register lists employers **licensed** to sponsor. A licence does **not** mean
a specific job will be sponsored — the UI must keep saying so.

## Build

```powershell
python scripts/build_sponsor_register.py
```

This deduplicates by organisation name (merging routes), strips the literal
`NULL` placeholders GOV.UK uses for empty Town/County cells, and writes:

| Artifact | Consumer | Notes |
|---|---|---|
| `data/sponsor_register/sponsors.csv` | Pipeline (`--sponsor-register`) | 126,350 deduped orgs, canonical schema |
| `frontend/public/sponsors.json` | Browser paste-checker (`/sponsors.json`) | Same data, regenerated **from** the CSV so both sides are identical |

Current snapshot: **126,350 unique organisations** (12,848 licensed on more than
one route). Skilled Worker — the route that matters for Graduate Route → Skilled
Worker conversion — covers ~121k of them.

Provenance (`source_published_at`, `downloaded_at`) is embedded in the JSON
`source` block and flows into every match's evidence.

## What is intentionally NOT regenerated here

These stay small and deterministic for fast, stable tests:

- `data/sponsor_register/sample_sponsors.csv` — used by `pytest`, the CLI, and
  the eval scripts.
- `frontend/src/engine/__fixtures__/sponsors.json` — the parity fixture, written
  by `scripts/gen_parity_golden.py`. That script no longer touches
  `frontend/public/sponsors.json` (a previous version did; it would have silently
  reverted the deployed app to sample data).

## Matching at scale (blocking index)

A linear fuzzy scan over 126k records took **~12 s per employer lookup** — fine
for nothing. Both matchers (`pipeline/sponsor_register/matcher.py` and the
parity-locked `frontend/src/engine/sponsorMatcher.ts`) now build a **blocking
index** at construction:

- **exact** normalised-name index (O(1) for identical names → score 1.0);
- **token** index (any shared normalised word);
- **character-trigram** index (catches typos / missing letters, e.g.
  `tradng` → `trading`, that share no whole token).

`match()` scores only candidates from those indexes, using the **unchanged**
scoring function. Result: **~0.02–0.23 s per lookup (50–600× faster)** while
returning the same match as the exhaustive scan.

Equivalence is enforced by tests on both sides
(`tests/test_sponsor_matching.py::IndexedMatcherEquivalenceTest`,
`frontend/src/engine/sponsorMatcher.test.ts`) and the Python↔TS parity harness.
The indexing is **identical** on both sides, so parity is preserved.

**One documented limitation:** an adversarial query whose only overlap with a
real name is a single 2-character run (e.g. `etfn` for `EATFAN`, internal letters
deleted) shares no trigram and may not match, where the old exhaustive scan would
have returned a low-confidence hit. This does not occur for realistic employer
names or ordinary typos; broadening to a bigram index was rejected because it
collapses the speedup.

## Match reliability (distinctive-token gate)

Running the real register exposed a precision problem the small sample register
hid: short, single-token names land in the 0.82–0.92 "medium" band by pure
character similarity between **different** companies — e.g. `Bechtle UK` →
`Bechtel Limited`, `Academics` → `ACADEMICIANS LTD`, or two unrelated
`… Education` firms. The eval seeds confirmed the band was unsafe: **every true
match in both datasets scores 1.0 (exact); there are no legitimate matches in the
medium band.**

Both engines now apply a **distinctive-token gate**: a non-exact match counts as
reliable (`is_match`, shown as a sponsor match) only if it scores ≥ 0.92 **or**
shares at least one non-generic token with the query. Generic sector/structure
words (`group`, `services`, `education`, `recruitment`, `trading`, …) don't
count. A demoted match is still returned as a **low-confidence, verify-first**
candidate so the closest register entry stays visible — it is just no longer
asserted as a match.

Effect on the live `jobs.json` seed: reliable matches dropped from 47/49 (mostly
false) to 2/49 (`Christie & Co`, `Diamond & Co` — both share a distinctive brand
token). The gate is identical on both sides (parity preserved) and locked by
`DistinctiveTokenGateTest` / the TS tests. It does not change which record is the
closest candidate or its score — only the reliability verdict.

> Product note: most graduate listings on Reed/Adzuna are posted by recruitment
> agencies that are not themselves licensed sponsors, so a low direct-match rate
> is expected and honest — that triage is the point of the tool.

## Known tradeoffs / follow-ups

- **Payload:** `frontend/public/sponsors.json` is ~18 MB raw / ~2.1 MB gzipped.
  Static hosts serve it gzipped; it is a one-time fetch. Acceptable for v1.
- **Storage:** the raw CSV, deduped CSV, and `sponsors.json` are large generated
  artifacts. Consider regenerating them in CI rather than committing, or moving
  the raw download under the already-gitignored `data/raw/`.
