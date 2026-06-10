"""Source pipeline models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple

from pipeline.classifier.models import JobInput


@dataclass(frozen=True)
class SourceRun:
    source: str
    status: str
    fetched_count: int
    normalised_count: int
    error: Optional[str] = None
    # Search term this run fetched (multi-term live runs); None for single-term
    # sources and file sources.
    search_term: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SourceNormalisationError(ValueError):
    """Raised when a raw source record cannot become a public job record."""


class SourceAdapter(Protocol):
    """Common interface for source adapters that produce normalised job inputs."""

    source: str

    def fetch_jobs(self, fetched_at: str) -> Tuple[List[JobInput], SourceRun]:
        """Fetch and normalise source jobs for a single source run."""
