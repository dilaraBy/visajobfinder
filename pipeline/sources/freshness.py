"""Deterministic job freshness/staleness signals for the public pipeline.

Phase 4 requires that stale listings are tracked so the dashboard can show
honest freshness. This module is pure (no network) and easy to test: it derives
an age in days from a job's posted date and the pipeline run timestamp, and a
boolean ``is_stale`` against a configurable threshold. A missing or unparseable
posted date is reported explicitly rather than silently treated as fresh.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Iterable, Optional


DEFAULT_STALE_AFTER_DAYS = 30


def _parse_date(value: Any) -> Optional[date]:
    text = str(value or "").strip()
    if len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def compute_age_days(posted_at: Any, generated_at: Any) -> Optional[int]:
    """Return whole days between ``posted_at`` and ``generated_at``.

    Returns None when either date is missing/unparseable. Negative ages (a
    posted date after the run) are clamped to 0 because they indicate clock or
    source-data skew rather than a genuinely future posting.
    """

    posted = _parse_date(posted_at)
    generated = _parse_date(generated_at)
    if posted is None or generated is None:
        return None
    return max((generated - posted).days, 0)


def freshness_for(
    posted_at: Any,
    generated_at: Any,
    stale_after_days: int = DEFAULT_STALE_AFTER_DAYS,
) -> Dict[str, Any]:
    """Build a freshness block for a single job record."""

    age_days = compute_age_days(posted_at, generated_at)
    has_posted_date = age_days is not None
    return {
        "posted_at": str(posted_at) if posted_at else None,
        "age_days": age_days,
        "has_posted_date": has_posted_date,
        "stale_after_days": stale_after_days,
        # Unknown dates are flagged as needs_review, not stale and not fresh.
        "is_stale": bool(has_posted_date and age_days > stale_after_days),
        "needs_review": not has_posted_date,
    }


def summarise_freshness(jobs: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    """Aggregate per-job freshness blocks into pipeline-level counts."""

    total = stale = missing_date = fresh = 0
    for job in jobs:
        freshness = job.get("freshness") or {}
        total += 1
        if not freshness.get("has_posted_date"):
            missing_date += 1
        elif freshness.get("is_stale"):
            stale += 1
        else:
            fresh += 1
    return {
        "total": total,
        "fresh": fresh,
        "stale": stale,
        "missing_date": missing_date,
    }
