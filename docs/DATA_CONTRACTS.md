# Data Contracts

This document defines the expected data shapes for v1. Keep these stable unless there is a documented migration.

## Public Jobs File

Path suggestion:

```text
data/public/jobs.json
```

Top-level shape:

```json
{
  "generated_at": "2026-06-04T09:00:00Z",
  "source_runs": [
    {
      "source": "reed",
      "status": "ok",
      "fetched_count": 120,
      "normalised_count": 115,
      "error": null
    }
  ],
  "jobs": []
}
```

## Job Record

For public deployments, `description_text` should be a source-permitted excerpt rather than a full copied job description unless the source explicitly permits full-text republication. If only an excerpt is stored, the UI must not imply the full job description was scanned. Keep `description_hash` when full fetched text is available locally for dedupe/evaluation.

```json
{
  "job_id": "reed:123456",
  "source": "reed",
  "source_job_id": "123456",
  "title": "Graduate Marketing Analyst",
  "employer_raw": "Example Ltd",
  "description_text": "Short source-permitted excerpt or evidence snippet...",
  "description_hash": "sha256-hash",
  "location": {
    "raw": "London",
    "city": "London",
    "country": "UK",
    "remote_type": "unknown"
  },
  "salary": {
    "raw": "GBP 32,000 per year",
    "min": 32000,
    "max": 32000,
    "currency": "GBP",
    "period": "year",
    "is_missing": false
  },
  "dates": {
    "posted_at": "2026-06-04",
    "closing_at": null,
    "fetched_at": "2026-06-04T09:00:00Z"
  },
  "url": "https://example.com/job",
  "description_scope": "excerpt",
  "normalised": {
    "title_tokens": ["graduate", "marketing", "analyst"],
    "employer_normalised": "example"
  },
  "visa_signals": {
    "employer_match": {},
    "phrase_signals": [],
    "base_limitations": []
  }
}
```

## Employer Match

```json
{
  "raw": "Example Ltd",
  "matched_name": "Example UK Limited",
  "confidence": 0.94,
  "confidence_band": "high",
  "match_method": "token_set",
  "sponsor_routes": ["Skilled Worker"],
  "rating": "A",
  "location": "London",
  "is_match": true,
  "source_name": "GOV.UK Register of Licensed Sponsors",
  "source_published_at": "2026-06-04"
}
```

If no reliable match exists:

```json
{
  "raw": "Example Ltd",
  "matched_name": null,
  "confidence": 0.0,
  "confidence_band": "none",
  "match_method": null,
  "sponsor_routes": [],
  "rating": null,
  "location": null,
  "is_match": false,
  "source_name": "GOV.UK Register of Licensed Sponsors",
  "source_published_at": "2026-06-04"
}
```

## Phrase Signal

```json
{
  "category": "future_sponsorship_risk",
  "severity": "amber",
  "text": "must have the right to work in the UK now and in the future",
  "start_index": 245,
  "end_index": 309,
  "rule_id": "rtw_now_or_future_001"
}
```

Allowed categories:

- `sponsorship_positive`
- `no_sponsorship`
- `future_sponsorship_risk`
- `permanent_right_to_work`
- `citizenship_required`
- `security_clearance`
- `salary_signal`
- `ambiguous`

Human-labelled eval records may also use auxiliary categories that are not
currently emitted as first-class engine phrase signals:

- `right_to_work`
- `temporary_work_window`
- `sponsorship_needed_option`
- `graduate_signal`

The evaluator canonicalises or ignores these where appropriate. For example,
generic `right_to_work` and `sponsorship_needed_option` labels are treated as
ambiguous visa wording, while `temporary_work_window` and `graduate_signal`
are review notes rather than visa-risk phrases.

## User Profile

Stored in browser local storage only.

Suggested key:

```text
visaJobFinder.profile.v1
```

Shape:

```json
{
  "visa_situation": "graduate_route",
  "visa_expiry_month": "2027-09",
  "needs_sponsorship_before_start": false,
  "needs_future_sponsorship": true,
  "target_start_month": "2026-09",
  "target_locations": ["London", "Manchester"],
  "target_keywords": ["graduate", "analyst", "marketing"],
  "updated_at": "2026-06-04T09:00:00Z"
}
```

## Classification Result

Classification is computed from job record plus user profile.

```json
{
  "job_id": "reed:123456",
  "label": "verify_first",
  "reason": "Employer appears on the sponsor register, but future sponsorship wording is ambiguous.",
  "evidence": [
    {
      "type": "phrase_signal",
      "category": "future_sponsorship_risk",
      "text": "right to work in the UK now and in the future"
    }
  ],
  "employer_match": {
    "matched_name": "Example UK Limited",
    "confidence": 0.94,
    "confidence_band": "high"
  },
  "what_to_verify": [
    "Ask whether this specific role can be sponsored before your current visa expires.",
    "Check whether salary and occupation code meet Skilled Worker requirements."
  ],
  "limitations": [
    "Sponsor-register presence does not prove this specific role will be sponsored."
  ]
}
```

Allowed labels:

- `worth_applying`
- `verify_first`
- `likely_blocked`
- `unknown`

## Tracking Data

Stored in browser local storage only.

Suggested key:

```text
visaJobFinder.tracking.v1
```

Shape:

```json
{
  "items": [
    {
      "job_id": "reed:123456",
      "status": "applied",
      "note": "Ask recruiter about Skilled Worker sponsorship.",
      "deadline": "2026-07-01",
      "saved_at": "2026-06-04T09:00:00Z",
      "updated_at": "2026-06-05T12:00:00Z"
    }
  ]
}
```

Allowed tracking statuses:

- `interested`
- `applied`
- `interview`
- `rejected`
- `offer`
- `archived`

## Migration Rule

If any local storage schema changes, create a new key suffix such as `.v2` or write an explicit migration. Do not silently reinterpret old user data.
