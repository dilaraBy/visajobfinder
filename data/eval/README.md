# Labelled Evaluation Data

Phase 2 evaluation datasets use JSON so records can be reviewed and versioned
without a database.

Top-level shape:

```json
{
  "schema_version": 1,
  "name": "sample labelled evaluation set",
  "records": []
}
```

Each record stores the public job evidence plus optional human sponsor-match
labelling:

```json
{
  "eval_id": "sample:001",
  "source": "manual",
  "url": "https://example.com/job",
  "title": "Graduate Analyst",
  "employer_raw": "Example Ltd",
  "description_text": "Short source-permitted excerpt or evidence snippet...",
  "location": "London",
  "salary_text": "GBP 35,000 per year",
  "sponsor_match_expected": {
    "available": true,
    "is_match": true,
    "matched_name": "Example UK Limited",
    "notes": "Human checked against the loaded sponsor data."
  },
  "cases": []
}
```

Each case stores the selected user situation, expected conservative label, and
the phrase evidence the engine should extract:

```json
{
  "case_id": "sample:001:graduate",
  "user_context": {
    "visa_situation": "graduate_route",
    "needs_sponsorship_before_start": false,
    "needs_future_sponsorship": true
  },
  "expected_label": "worth_applying",
  "expected_evidence": [
    {
      "category": "sponsorship_positive",
      "text_contains": "Visa sponsorship available"
    }
  ],
  "notes": "No detected blocker in the job text."
}
```

Human labels should be based only on public evidence in the job ad and sponsor
register. Use `unknown` when public evidence is not enough to judge.
For fixture-based eval sets, `sponsor_match_expected.is_match: false` means the
loaded sponsor fixture is expected not to match the stored employer name. It is
not a claim that the employer lacks a live GOV.UK sponsor licence.
Fixture-backed positive labels should only be used when the stored excerpt or a
separate reviewed source supports sponsor-register presence, and they still do
not prove that the specific role will be sponsored.

## Real Seed Schema

The evaluator also supports the real seed format used by
`labelled_jobs.real.json`:

- `record_id` instead of `eval_id`;
- `source_url` instead of `url`;
- `expected_labels` keyed by visa situation;
- `evidence_phrases` at record level.
- `review_status`, using `confirmed`, `needs_review`,
  `change_recommended`, or `remove_from_eval`;
- `default_dashboard_fit`, a boolean for whether the role level belongs in the
  default v1 dashboard;
- `eval_use`, usually `classification_and_evidence`; use `exclude` for records
  retained for audit but not counted in metrics.

At runtime, those records are expanded into one case per expected visa
situation. Some human evidence categories are canonicalised to the engine's
current vocabulary:

- `right_to_work` -> `ambiguous`;
- `sponsorship_needed_option` -> `ambiguous`;
- `graduate_signal` and `temporary_work_window` are ignored for phrase
  extraction metrics because they are role/timing notes, not current
  visa-phrase categories.

If an expected evidence phrase is not literally present in the stored
`description_text` excerpt, the evaluator checks category only. This keeps the
metric aligned with the text available to the engine.

When a generic right-to-work phrase overlaps a stricter extracted signal such
as `no_sponsorship`, `permanent_right_to_work`, or `future_sponsorship_risk`,
the stricter signal is counted as covering the generic phrase. The scanner
does not need to emit duplicate overlapping evidence to satisfy that case.

The evaluator validates the dataset before running. Records with
`review_status: "remove_from_eval"` or `eval_use: "exclude"` are skipped and
reported as excluded rather than silently counted.

## Classifier API Expected by the Evaluator

`pipeline.eval.run_eval` imports the deterministic classifier through:

```python
from pipeline.classifier.engine import analyse_job
```

Expected callable shape:

```python
analyse_job(job: JobInput, user: UserContext, matcher: SponsorMatcher) -> dict
```

The returned dictionary must contain:

```json
{
  "classification": {
    "label": "worth_applying | verify_first | likely_blocked | unknown",
    "reason": "Plain-language reason",
    "evidence": []
  }
}
```

Additional fields are allowed and currently used elsewhere, but the evaluator
only depends on `classification.label`, `classification.reason`, and
`classification.evidence` for classification and evidence metrics.

## Sponsor Match Failure Examples

The report preserves the existing high-confidence sponsor precision metric and
also prints labelled sponsor precision when sponsor labels are available. The
labelled metric checks whether the matcher made the same match/no-match decision
as the human fixture label.

When a labelled sponsor decision fails, the report includes up to five examples:

```text
Sponsor label failure examples:
  real-001: Fresha -> Example UK Limited [high] (expected is_match=False, matched_name=None)
```

These examples are diagnostic matcher failures only. They should not be
described as legal eligibility decisions or as claims about a specific job being
sponsored.
