# Graduate Route Rule Tuning — June 2026

## Problem Statement

The engine was over-conservative for Graduate Route users on the 20-record real-seed evaluation set. The headline numbers before tuning:

| Metric | Before |
|---|---|
| graduate_route exact-label | 14/20 (70.0%) |
| graduate_route false-red | 1/20 (5.0%) |
| graduate_route false-green | 0/20 (0.0%) |
| graduate_route verify_first rate | 18/20 (90.0%) |
| needs_sponsorship_before_start exact-label | 20/20 (100.0%) |
| needs_sponsorship_before_start false-green | 0/20 (0.0%) |

Acceptance constraint: false-green must remain 0, needs_sponsorship_before_start must not regress.

---

## Diagnosis of the 6 Misses

### Miss 1 — real-003 (expected: worth_applying, predicted: verify_first)

**Employer:** Octopus Energy Group (confirmed sponsor-register match)  
**Phrases:** `sponsorship_positive` ("registered visa sponsor"), `ambiguous` (case-by-case)  
**Rule path:** Graduate Route section, `user.needs_future_sponsorship and not job.salary_text` → verify_first  
**Root cause:** The salary check fired for graduate_route users with `needs_future_sponsorship=True`. Graduate Route users have current right to work; salary matters for Skilled Worker thresholds (future path), not current employment. Salary absence is already noted in limitations. Forcing verify_first on salary alone is over-conservative.

### Miss 2 — real-004 (expected: worth_applying, predicted: verify_first)

**Employer:** Octopus Energy Group (confirmed sponsor-register match)  
**Phrases:** `future_sponsorship_risk` (temporary RTW + might need sponsorship in future), `sponsorship_positive` (case-by-case)  
**Rule path:** Early exit `if "future_sponsorship_risk" in categories` → verify_first, fires before the Graduate Route section is reached  
**Root cause:** The `future_sponsorship_risk` early check was a blanket exit for ALL visa situations. For Graduate Route, a future-sponsorship question in the JD is meaningfully offset when the employer is on the sponsor register AND the JD has sponsorship-positive wording. The early exit prevented this from being evaluated.

### Miss 3 — real-007 (expected: worth_applying, predicted: verify_first)

**Employer:** Moonpig (not on fixture sponsor register)  
**Phrases:** Only `ambiguous` (right-to-work dropdown including "I require sponsorship" option)  
**Rule path:** Graduate Route section, `user.needs_future_sponsorship and not match.is_match` → verify_first  
**Root cause:** For Graduate Route, the absence of a sponsor-register match was treated as a blocking signal regardless of what the JD says. The JD here contained no explicit future-sponsorship question — only a generic form option. A Graduate Route user has current right to work; the sponsor-register absence is only a concern if the JD itself raises a future sponsorship question.

### Miss 4 — real-008 (expected: worth_applying, predicted: verify_first)

Same as miss 3, different role at Moonpig.

### Miss 5 — real-018 (expected: verify_first, predicted: likely_blocked) — FALSE RED

**Employer:** Ebury (not on fixture sponsor register)  
**Phrases:** `permanent_right_to_work` ("right to work in the UK without restriction"), `future_sponsorship_risk`  
**Rule path:** `DECISIVE_BLOCKERS & categories` where `permanent_right_to_work` is in `DECISIVE_BLOCKERS` → likely_blocked for ALL visa situations  
**Root cause:** The engine treated "right to work in the UK without restriction" as a decisive blocker (equivalent to citizenship requirement) for Graduate Route users too. This phrase appears as a form question about current RTW status. A Graduate Route visa is a valid right to work (just restricted). The phrase is a signal to verify, not a hard citizenship mandate.

### Miss 6 — real-019 (expected: worth_applying, predicted: verify_first)

**Employer:** Jensen Hughes (not on fixture sponsor register)  
**Phrases:** Only `ambiguous` ("right to work in the UK" — generic)  
**Rule path:** Graduate Route section, `user.needs_future_sponsorship and not match.is_match` → verify_first  
**Root cause:** Same as misses 3 and 4. The "no sponsor match" rule was too aggressive when the JD itself contains no explicit future-sponsorship question.

---

## Rule Changes Made

All changes are in `pipeline/classifier/engine.py`. No changes to `pipeline/classifier/phrase_scanner.py`.

### Change 1: Split DECISIVE_BLOCKERS by visa situation

**File:** `pipeline/classifier/engine.py`  
**What changed:** Added `GRADUATE_ROUTE_DECISIVE_BLOCKERS = {"citizenship_required"}`. The `DECISIVE_BLOCKERS` check now uses `GRADUATE_ROUTE_DECISIVE_BLOCKERS` when `visa_situation == "graduate_route"`, meaning `permanent_right_to_work` is no longer a hard block for GR users.  
**Why:** Graduate Route holders have current legal right to work in the UK. "Unrestricted" or "permanent" RTW phrases are form questions about immigration status, not citizenship mandates. Only `citizenship_required` (e.g. "UK nationals only") is a hard block for GR. The distinction is: citizenship requirement excludes everyone on a visa; permanent RTW requirement asks about status that GR users may partially satisfy.

### Change 2: Add explicit permanent_right_to_work → verify_first inside the Graduate Route section

**File:** `pipeline/classifier/engine.py`  
**What changed:** Added a check inside the Graduate Route section: `if "permanent_right_to_work" in categories` → `verify_first` with a clear reason "verify whether the Graduate Route visa satisfies that requirement."  
**Why:** Ensures `permanent_right_to_work` produces `verify_first` (not `worth_applying`) for GR users. Without this, changing the DECISIVE_BLOCKERS check would have let permanent_right_to_work phrases fall through to `worth_applying`, which is incorrect.

### Change 3: Move future_sponsorship_risk early exit into visa-specific sections

**File:** `pipeline/classifier/engine.py`  
**What changed:** Removed the blanket early exit `if "future_sponsorship_risk" in categories → verify_first`. Added equivalent checks inside the NSS section and the Graduate Route section.  
- NSS: `future_sponsorship_risk` without `sponsorship_positive` → verify_first (as before)  
- GR: `future_sponsorship_risk` without (`sponsorship_positive` AND confirmed sponsor-register match) → verify_first. If both `sponsorship_positive` and `match.is_match` are present, fall through to `worth_applying`.  
**Why:** For Graduate Route users, a future-sponsorship question in the JD is meaningfully offset by confirmed sponsor-register presence and sponsorship-positive wording. The early exit was not visa-situation-aware and over-fired for GR.

### Change 4: Remove graduate route salary check

**File:** `pipeline/classifier/engine.py`  
**What changed:** Removed the rule `if user.needs_future_sponsorship and not job.salary_text → verify_first` from the Graduate Route section.  
**Why:** Salary matters for Skilled Worker visa thresholds, which are relevant to future sponsorship. But a Graduate Route user has current right to work regardless of salary. The salary limitation is already surfaced in the `limitations` field of every classification result. Blocking `worth_applying` on salary alone was not supported by the human labels on the seed set (real-003, real-007, real-008, real-019 all had no salary and were labelled `worth_applying`).

### Change 5: Graduate route "no sponsor match" only fires when JD has explicit future_sponsorship_risk

**File:** `pipeline/classifier/engine.py`  
**What changed:** The rule `if user.needs_future_sponsorship and not match.is_match → verify_first` now also requires `"future_sponsorship_risk" in categories`. Without an explicit future-sponsorship question in the JD, a missing sponsor-register match does not force `verify_first` for Graduate Route.  
**Why:** Graduate Route users have current right to work. If the JD contains no explicit signal about future sponsorship needs, the employer's absence from the sponsor-register fixture is not a relevant blocker. The fixture is incomplete (only a sample); the real register is a separate concern. When the JD itself asks "will you need sponsorship in the future?" then the absence of a sponsor-register match matters and verify_first is appropriate.

---

## After Metrics

After rule changes, on the same 20-record real seed set:

| Metric | Before | After |
|---|---|---|
| graduate_route exact-label | 14/20 (70.0%) | 20/20 (100.0%) |
| graduate_route false-red | 1/20 (5.0%) | 0/20 (0.0%) |
| graduate_route false-green | 0/20 (0.0%) | 0/20 (0.0%) |
| graduate_route verify_first rate | 18/20 (90.0%) | 14/20 (70.0%) |
| needs_sponsorship_before_start exact-label | 20/20 (100.0%) | 20/20 (100.0%) |
| needs_sponsorship_before_start false-green | 0/20 (0.0%) | 0/20 (0.0%) |
| evidence extraction accuracy | 40/40 (100.0%) | 40/40 (100.0%) |
| sponsor match precision (high-confidence) | 3/3 (100.0%) | 3/3 (100.0%) |

False-green is confirmed 0/20 for both visa situations. needs_sponsorship_before_start is unchanged at 20/20. The false-red was eliminated (real-018 is now correctly verify_first).

---

## What Was Not Changed

- `phrase_scanner.py` phrase rules are unchanged. The `permanent_right_to_work` category is still assigned to "without restriction" phrases — this is correct. The engine's visa-situation-aware handling of that category changed, not the phrase rules.
- The `no_sponsorship` rules are unchanged. They still block or warn as before for all visa situations.
- The `DECISIVE_BLOCKERS` set is unchanged for all non-Graduate-Route visa situations. NSS, unknown, and other situations still treat `permanent_right_to_work` as a decisive blocker.
- Evidence invariant is preserved: every classification still returns `evidence`, `limitations`, `what_to_verify`, and salary missing is still surfaced in `limitations` for GR users even though it no longer forces `verify_first`.

---

## Limitations and Uncertainty

These rule changes are validated on 20 real records. The patterns are defensible against the seed set, but:

1. The engine still treats `needs_future_sponsorship=True` as the default for all eval cases (set by the eval harness). Tuning that flag in user context would change results.
2. The Graduate Route "future_sponsorship_risk + sponsorship_positive + sponsor match → worth_applying" rule is based on 1 real case (real-004). It should be watched for false-greens as more data is collected.
3. The seed set has no examples of GR users with low-confidence sponsor-register matches and no JD future-sponsorship signals. That path is not well-tested.
4. The 100% exact-label on 20 records does not imply 100% real-world performance. Collect more records per the checklist in `docs/DATASET_COLLECTION_CHECKLIST.md`.
