"""Deduplicate normalised source jobs before public output."""

from __future__ import annotations

import hashlib
from typing import Iterable, List, Set

from pipeline.classifier.models import JobInput
from pipeline.sponsor_register.normalise import normalise_employer_name


def description_hash(description_text: str) -> str:
    return hashlib.sha256(description_text.encode("utf-8")).hexdigest()


def dedupe_key(job: JobInput) -> str:
    employer = normalise_employer_name(job.employer_raw)
    title = " ".join(job.title.lower().split())
    return "|".join([employer, title, description_hash(job.description_text)])


def dedupe_jobs(jobs: Iterable[JobInput]) -> List[JobInput]:
    seen: Set[str] = set()
    deduped: List[JobInput] = []
    for job in jobs:
        key = dedupe_key(job)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(job)
    return deduped

