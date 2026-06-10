"""Normalise raw source records into the shared job input shape."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Optional

from pipeline.classifier.models import JobInput
from pipeline.sources.models import SourceNormalisationError


TOKEN_RE = re.compile(r"[a-z0-9]+")
PUBLIC_DESCRIPTION_EXCERPT_CHARS = 700


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _optional_text(value: Any) -> Optional[str]:
    cleaned = _clean_text(value)
    return cleaned or None


def _optional_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    digits = re.sub(r"[^0-9]", "", str(value))
    return int(digits) if digits else None


def _public_description_excerpt(value: Any) -> str:
    text = _clean_text(value)
    if len(text) <= PUBLIC_DESCRIPTION_EXCERPT_CHARS:
        return text
    return text[:PUBLIC_DESCRIPTION_EXCERPT_CHARS].rsplit(" ", 1)[0].rstrip(".,;:") + "..."


def _fallback_source_job_id(raw: Dict[str, Any]) -> str:
    seed = "|".join(
        [
            _clean_text(raw.get("title")),
            _clean_text(raw.get("employer_raw") or raw.get("employer")),
            _clean_text(raw.get("url")),
        ]
    )
    if not seed.strip("|"):
        seed = _clean_text(raw)
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]


def _title_tokens(title: str) -> list[str]:
    return TOKEN_RE.findall(title.lower())


def normalise_raw_job(raw: Dict[str, Any], fetched_at: str) -> JobInput:
    source = _clean_text(raw.get("source")) or "unknown"
    source_job_id = _clean_text(raw.get("source_job_id") or raw.get("id"))
    if not source_job_id:
        source_job_id = _fallback_source_job_id(raw)

    title = _clean_text(raw.get("title"))
    employer_raw = _clean_text(raw.get("employer_raw") or raw.get("employer"))
    description_text = _public_description_excerpt(
        raw.get("description_text") or raw.get("description") or raw.get("body")
    )

    missing = []
    if not title:
        missing.append("title")
    if not employer_raw:
        missing.append("employer_raw")
    if not description_text:
        missing.append("description_text")
    if missing:
        raise SourceNormalisationError(
            f"Missing required field(s) for {source}:{source_job_id}: {', '.join(missing)}"
        )

    return JobInput(
        job_id=f"{source}:{source_job_id}",
        source=source,
        source_job_id=source_job_id,
        title=title,
        employer_raw=employer_raw,
        description_text=description_text,
        location=_optional_text(raw.get("location") or raw.get("location_raw")),
        salary_text=_optional_text(raw.get("salary_text") or raw.get("salary")),
        salary_min=_optional_int(raw.get("salary_min")),
        salary_max=_optional_int(raw.get("salary_max")),
        posted_at=_optional_text(raw.get("posted_at")),
        closing_at=_optional_text(raw.get("closing_at")),
        fetched_at=fetched_at,
        url=_optional_text(raw.get("url")),
        category=_optional_text(raw.get("category") or raw.get("query")),
    )


def normalised_title_tokens(title: str) -> list[str]:
    return _title_tokens(title)
