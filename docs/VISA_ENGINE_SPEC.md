# Visa Engine Spec

## Purpose

The visa engine produces conservative, evidence-backed visa-risk labels for UK graduate and junior job listings.

It does not determine legal eligibility.

## Inputs

### Job Input

```json
{
  "job_id": "source:123",
  "source": "reed",
  "title": "Graduate Marketing Analyst",
  "employer_raw": "Example Ltd",
  "description_text": "...",
  "location": "London",
  "salary_text": "GBP 32,000",
  "salary_min": 32000,
  "salary_max": 32000,
  "posted_at": "2026-06-04",
  "closing_at": null,
  "url": "https://example.com/job"
}
```

### User Context

```json
{
  "visa_situation": "graduate_route",
  "visa_expiry_month": "2027-09",
  "needs_sponsorship_before_start": false,
  "needs_future_sponsorship": true,
  "target_start_month": "2026-09"
}
```

Supported `visa_situation` values for v1:

- `graduate_route`
- `needs_sponsorship_before_start`
- `unknown`

## Outputs

```json
{
  "label": "verify_first",
  "reason": "Employer appears on the sponsor register, but the job ad asks candidates to confirm right to work now and in the future.",
  "evidence": [
    {
      "type": "jd_phrase",
      "category": "future_sponsorship_risk",
      "text": "must have the right to work in the UK now and in the future"
    }
  ],
  "employer_match": {
    "raw": "Example",
    "matched_name": "Example UK Limited",
    "confidence": 0.94,
    "route": "Skilled Worker",
    "rating": "A"
  },
  "what_to_verify": [
    "Ask whether the employer can sponsor this specific role before your Graduate visa expires.",
    "Check whether the salary and occupation code can meet Skilled Worker requirements."
  ],
  "limitations": [
    "Sponsor-register presence does not prove this specific role will be sponsored."
  ]
}
```

## Label Definitions

### Worth Applying

Use only when no strong blocker is detected for the selected user situation.

For Graduate Route users:

- no citizenship-only phrase;
- no clear permanent/unrestricted right-to-work blocker;
- no explicit "cannot sponsor now or in future" if future sponsorship is needed soon;
- start date appears inside current work permission if known.

For users needing sponsorship before start:

- high-confidence sponsor-register match;
- no explicit no-sponsorship phrase;
- job text is not obviously below skilled/salary threshold;
- explicit sponsorship-positive phrase for the specific role.

If salary or sponsorship commitment is missing, prefer Verify first.

### Verify First

Use when the role may be viable but uncertainty is material.

Examples:

- sponsor-register match but no role-level sponsorship evidence;
- salary missing;
- "right to work now and in the future";
- low or medium sponsor match confidence;
- security clearance mentioned but requirement is unclear;
- employer is sponsor-licensed but route/category is unclear.

### Likely Blocked

Use when strong evidence suggests the user should not spend time applying.

Examples:

- "UK nationals only";
- "British citizenship required";
- "must already have indefinite leave to remain";
- "permanent right to work required";
- "we cannot provide visa sponsorship";
- "we cannot sponsor now or in the future";
- "must not require sponsorship now or in the future" for users who need sponsorship.

### Unknown

Use when reliable classification is not possible.

Examples:

- employer missing;
- description missing;
- sponsor match confidence too low;
- source data incomplete;
- contradictory signals with no decisive evidence.

## Sponsor-Register Matching

Source:

- GOV.UK Register of Licensed Sponsors.

Normalisation:

- lowercase;
- strip punctuation;
- strip legal suffixes such as ltd, limited, plc, llp, inc, uk, group where appropriate;
- normalise ampersand and "and";
- collapse whitespace;
- preserve raw names for display.

Candidate matching:

1. exact normalised match;
2. token-set fuzzy match;
3. substring match with safeguards;
4. alias table for known employers;
5. manual overrides for eval-discovered errors.

Confidence bands:

- high: `>= 0.92`
- medium: `0.82-0.91`
- low: `< 0.82`

Never hide confidence from the user.

Common risks:

- parent company vs UK hiring entity;
- recruiter posting on behalf of employer;
- trading names;
- subsidiaries;
- universities and NHS trusts with similar names;
- generic names like "Compass", "The Works", "Next".

## Phrase Categories

### Strong Blockers

- "UK nationals only"
- "British citizens only"
- "British citizenship required"
- "permanent right to work"
- "unrestricted right to work"
- "indefinite leave to remain"
- "cannot sponsor"
- "unable to sponsor"
- "will not sponsor"
- "must not require sponsorship"
- "now or in the future"

### Sponsorship-Positive

- "visa sponsorship available"
- "Skilled Worker sponsorship available"
- "Certificate of Sponsorship"
- "we can sponsor"
- "sponsorship considered"

### Security/Citizenship Risk

- "SC clearance"
- "DV clearance"
- "security cleared"
- "UK eyes only"
- "5 years UK residency"

Security phrases should usually be Verify first unless citizenship-only language is explicit.

## LLM Judge

The LLM is optional and only for ambiguous cases.

Rules:

- deterministic blockers win;
- prompt must require exact phrase citation;
- no evidence means no confident label;
- output must be parsed into the same schema;
- ambiguous output becomes Verify first or Unknown;
- never send user profile data beyond coarse visa situation.

## Testing Requirements

Unit tests:

- sponsor name normalisation;
- high/medium/low matching examples;
- phrase scanner categories;
- status branch rules;
- contradictory evidence handling.

Eval tests:

- labelled real job descriptions;
- sponsor match precision;
- false red and false green rates by visa situation;
- evidence extraction accuracy.
