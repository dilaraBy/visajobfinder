"""Shared data models for the Phase 1 visa engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


ALLOWED_LABELS = {"worth_applying", "verify_first", "likely_blocked", "unknown"}
ALLOWED_VISA_SITUATIONS = {
    "graduate_route",
    "needs_sponsorship_before_start",
    "unknown",
}


@dataclass(frozen=True)
class JobInput:
    """Minimal job shape accepted by the prototype engine and paste checker."""

    job_id: str = "paste:manual"
    source: str = "paste"
    source_job_id: Optional[str] = None
    title: str = ""
    employer_raw: str = ""
    description_text: str = ""
    location: Optional[str] = None
    salary_text: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    posted_at: Optional[str] = None
    closing_at: Optional[str] = None
    fetched_at: Optional[str] = None
    url: Optional[str] = None


@dataclass(frozen=True)
class UserContext:
    """The v1 visa context used for status-aware decision rules."""

    visa_situation: str = "unknown"
    visa_expiry_month: Optional[str] = None
    needs_sponsorship_before_start: bool = False
    needs_future_sponsorship: bool = False
    target_start_month: Optional[str] = None

    def __post_init__(self) -> None:
        if self.visa_situation not in ALLOWED_VISA_SITUATIONS:
            raise ValueError(
                f"Unsupported visa_situation '{self.visa_situation}'. "
                f"Expected one of {sorted(ALLOWED_VISA_SITUATIONS)}."
            )


@dataclass(frozen=True)
class PhraseSignal:
    category: str
    severity: str
    text: str
    start_index: int
    end_index: int
    rule_id: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EmployerMatch:
    raw: str
    matched_name: Optional[str]
    confidence: float
    confidence_band: str
    match_method: Optional[str]
    sponsor_routes: List[str] = field(default_factory=list)
    rating: Optional[str] = None
    location: Optional[str] = None
    is_match: bool = False
    source_name: Optional[str] = None
    source_published_at: Optional[str] = None
    source_downloaded_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["confidence"] = round(self.confidence, 3)
        return data


@dataclass(frozen=True)
class ClassificationResult:
    job_id: str
    label: str
    reason: str
    evidence: List[Dict[str, Any]]
    employer_match: Dict[str, Any]
    what_to_verify: List[str]
    limitations: List[str]

    def __post_init__(self) -> None:
        if self.label not in ALLOWED_LABELS:
            raise ValueError(f"Unsupported label '{self.label}'.")
        if not self.evidence:
            raise ValueError("Classification results must include evidence.")
        if not self.limitations:
            raise ValueError("Classification results must include limitations.")
        if not self.what_to_verify:
            raise ValueError("Classification results must include verification prompts.")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
