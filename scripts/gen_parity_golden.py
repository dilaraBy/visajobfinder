"""Generate the parity golden fixture for the TypeScript engine port.

This script runs the LIVE Python visa engine (analyse_job) over every case in
both eval datasets (expanding records into per-visa-situation cases exactly as
pipeline/eval/run_eval.py does, by reusing its helpers) and writes:

  * frontend/src/engine/__fixtures__/parity_golden.json
      The inputs (job + user_context) plus the Python outputs the TS port must
      reproduce: label, the SET of evidence categories, and the sponsor match
      (matched_name, confidence_band, is_match).

  * frontend/src/engine/__fixtures__/sponsors.json
      The SAMPLE sponsor register dumped from sample_sponsors.csv, in the shape
      the TS sponsorData loader expects. This stays small + deterministic so the
      parity test is fast and stable.

The browser-served frontend/public/sponsors.json is the REAL GOV.UK register and
is generated separately by scripts/build_sponsor_register.py — this script must
NOT overwrite it, or the deployed app would silently fall back to sample data.

Re-run this whenever the Python rules or sponsor data change:

    python scripts/gen_parity_golden.py

The golden file is the source of truth for the Vitest parity test. Do NOT
hand-edit it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure the repo root is importable when run as a script from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Reuse the exact eval-harness helpers so case expansion stays identical.
from pipeline.eval.run_eval import (
    _cases_from_record,
    _job_from_record,
    _record_id,
    _records_for_eval,
    _user_from_case,
    load_dataset,
)
from pipeline.classifier.engine import analyse_job
from pipeline.sponsor_register.matcher import SponsorMatcher, SponsorRegister


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
SPONSOR_CSV = DATA_DIR / "sponsor_register" / "sample_sponsors.csv"
DATASETS = [
    DATA_DIR / "eval" / "labelled_jobs.real.json",
    DATA_DIR / "eval" / "labelled_jobs.sample.json",
]
FRONTEND = REPO_ROOT / "frontend"
FIXTURES_DIR = FRONTEND / "src" / "engine" / "__fixtures__"
GOLDEN_PATH = FIXTURES_DIR / "parity_golden.json"
# NOTE: the real browser register (frontend/public/sponsors.json) is owned by
# scripts/build_sponsor_register.py and intentionally NOT written here.
SPONSORS_FIXTURE = FIXTURES_DIR / "sponsors.json"


def _job_input_payload(job: Any) -> Dict[str, Any]:
    """Serialise the JobInput fields the TS engine consumes (mirrors models.py)."""

    return {
        "job_id": job.job_id,
        "source": job.source,
        "source_job_id": job.source_job_id,
        "title": job.title,
        "employer_raw": job.employer_raw,
        "description_text": job.description_text,
        "location": job.location,
        "salary_text": job.salary_text,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "posted_at": job.posted_at,
        "closing_at": job.closing_at,
        "fetched_at": job.fetched_at,
        "url": job.url,
    }


def _user_context_payload(user: Any) -> Dict[str, Any]:
    return {
        "visa_situation": user.visa_situation,
        "visa_expiry_month": user.visa_expiry_month,
        "needs_sponsorship_before_start": user.needs_sponsorship_before_start,
        "needs_future_sponsorship": user.needs_future_sponsorship,
        "target_start_month": user.target_start_month,
    }


def _evidence_categories(evidence: List[Dict[str, Any]]) -> List[str]:
    """Sorted unique evidence categories (order-independent comparison)."""

    return sorted({str(item.get("category")) for item in evidence})


def build_golden(matcher: SponsorMatcher) -> Dict[str, Any]:
    cases: List[Dict[str, Any]] = []
    for dataset_path in DATASETS:
        dataset = load_dataset(dataset_path)
        for record in _records_for_eval(dataset["records"]):
            job = _job_from_record(record)
            for case in _cases_from_record(record):
                user = _user_from_case(case)
                output = analyse_job(job, user, matcher)
                classification = output["classification"]
                employer_match = output["job"]["visa_signals"]["employer_match"]
                cases.append(
                    {
                        "dataset": dataset_path.name,
                        "case_id": case.get("case_id") or _record_id(record),
                        "eval_id": _record_id(record),
                        "job": _job_input_payload(job),
                        "user_context": _user_context_payload(user),
                        "expected": {
                            "label": classification["label"],
                            "evidence_categories": _evidence_categories(
                                classification["evidence"]
                            ),
                            "sponsor": {
                                "matched_name": employer_match["matched_name"],
                                "confidence_band": employer_match["confidence_band"],
                                "is_match": employer_match["is_match"],
                                "confidence": employer_match["confidence"],
                            },
                        },
                    }
                )

    return {
        "generated_by": "scripts/gen_parity_golden.py",
        "note": (
            "Golden outputs from the live Python visa engine. The TS port must "
            "reproduce label, evidence_categories, and sponsor match. Do not "
            "hand-edit; regenerate with python scripts/gen_parity_golden.py."
        ),
        "sponsor_register_csv": str(SPONSOR_CSV.relative_to(REPO_ROOT)),
        "cases": cases,
    }


def build_sponsors_payload() -> Dict[str, Any]:
    register: SponsorRegister = SponsorRegister.from_csv(SPONSOR_CSV)
    records = [
        {
            "organisation_name": record.organisation_name,
            "sponsor_routes": list(record.sponsor_routes),
            "rating": record.rating,
            "location": record.location,
            "aliases": list(record.aliases),
        }
        for record in register.records
    ]
    return {
        "source": register.source.to_dict(),
        "records": records,
    }


def main() -> int:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    sponsors_payload = build_sponsors_payload()
    sponsors_json = json.dumps(sponsors_payload, indent=2, ensure_ascii=False) + "\n"
    SPONSORS_FIXTURE.write_text(sponsors_json, encoding="utf-8")

    matcher = SponsorMatcher.from_csv(SPONSOR_CSV)
    golden = build_golden(matcher)
    GOLDEN_PATH.write_text(
        json.dumps(golden, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"Wrote {len(golden['cases'])} parity cases to {GOLDEN_PATH}")
    print(f"Wrote sample sponsor fixture to {SPONSORS_FIXTURE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
