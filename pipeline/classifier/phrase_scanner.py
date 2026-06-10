"""Deterministic job-description phrase scanner."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List

from pipeline.classifier.models import PhraseSignal


@dataclass(frozen=True)
class PhraseRule:
    rule_id: str
    category: str
    severity: str
    pattern: str
    priority: int


PHRASE_RULES: List[PhraseRule] = [
    PhraseRule(
        "citizenship_uk_nationals_only_001",
        "citizenship_required",
        "red",
        r"\b(?:uk|british)\s+national[s]?\s+only\b",
        40,
    ),
    PhraseRule(
        "citizenship_british_required_001",
        "citizenship_required",
        "red",
        r"\b(?:british|uk)\s+citizenship\s+(?:is\s+)?required\b",
        40,
    ),
    PhraseRule(
        "citizenship_british_citizen_001",
        "citizenship_required",
        "red",
        r"\bmust\s+be\s+(?:a\s+)?british\s+citizen\b",
        40,
    ),
    PhraseRule(
        "rtw_permanent_001",
        "permanent_right_to_work",
        "red",
        r"\bpermanent\s+right\s+to\s+work\b",
        40,
    ),
    PhraseRule(
        "rtw_unrestricted_001",
        "permanent_right_to_work",
        "red",
        r"\bunrestricted\s+right\s+to\s+work\b",
        40,
    ),
    PhraseRule(
        "rtw_without_restriction_001",
        "permanent_right_to_work",
        "red",
        r"\bright\s+to\s+work\s+in\s+the\s+uk\s+without\s+restriction\b",
        40,
    ),
    PhraseRule(
        "rtw_ilr_001",
        "permanent_right_to_work",
        "red",
        r"\bindefinite\s+leave\s+to\s+remain\b",
        40,
    ),
    PhraseRule(
        "no_sponsor_now_future_001",
        "no_sponsorship",
        "red",
        r"\bmust\s+not\s+require\s+(?:visa\s+)?sponsorship(?:\s+now)?(?:\s+(?:or|and)\s+in\s+the\s+future)?\b",
        40,
    ),
    PhraseRule(
        "no_sponsor_unable_001",
        "no_sponsorship",
        "red",
        r"\b(?:we\s+)?(?:cannot|can't|unable\s+to|will\s+not|won't|do\s+not|don't)\s+(?:provide\s+|offer\s+)?(?:visa\s+)?sponsorship\b",
        40,
    ),
    PhraseRule(
        "no_sponsor_available_001",
        "no_sponsorship",
        "red",
        r"\bno\s+(?:visa\s+)?sponsorship\s+(?:is\s+)?(?:available|provided|offered)\b",
        40,
    ),
    PhraseRule(
        "no_sponsor_select_no_001",
        "no_sponsorship",
        "red",
        r"\b(?:please\s+)?select\s+['\"]?no['\"]?\s+if[^.]{0,80}\b(?:require|requires|required)\s+(?:visa\s+)?sponsorship\b",
        40,
    ),
    PhraseRule(
        "no_sponsor_select_no_passive_001",
        "no_sponsorship",
        "red",
        r"\b(?:please\s+)?select\s+['\"]?no['\"]?\s+if[^.]{0,80}\b(?:visa\s+)?sponsorship\s+would\s+be\s+required\b",
        40,
    ),
    PhraseRule(
        "no_sponsor_without_001",
        "no_sponsorship",
        "red",
        r"\b(?:full\s+|legal\s+)?right\s+to\s+(?:work(?:\s+and\s+live)?|live\s+and\s+work)[^.]{0,80}\bwithout\s+(?:requiring\s+)?(?:visa\s+)?sponsorship\b",
        40,
    ),
    PhraseRule(
        "no_sponsor_without_requiring_001",
        "no_sponsorship",
        "red",
        r"\bwithout\s+requiring\s+(?:visa\s+)?sponsorship\b",
        40,
    ),
    PhraseRule(
        "no_sponsor_unable_to_sponsor_001",
        "no_sponsorship",
        "red",
        r"\b(?:we\s+|the\s+employer\s+)?(?:cannot|can't|unable\s+to|will\s+not|won't|do\s+not|don't)\s+sponsor\b[^.]{0,80}",
        40,
    ),
    PhraseRule(
        "no_sponsor_unable_employees_future_001",
        "no_sponsorship",
        "red",
        r"\bunable\s+to\s+sponsor\s+employees(?:,)?\s+either\s+now\s+or\s+in\s+the\s+future\b",
        41,
    ),
    PhraseRule(
        "rtw_now_or_future_001",
        "future_sponsorship_risk",
        "amber",
        r"\b(?:right\s+to\s+work|work\s+authori[sz]ation)[^.]{0,80}\bnow\s+(?:and|or)\s+in\s+the\s+future\b",
        30,
    ),
    PhraseRule(
        "sponsorship_future_unclear_001",
        "future_sponsorship_risk",
        "amber",
        r"\b(?:require|need|needing|might\s+need)[^.]{0,30}(?:visa\s+)?sponsorship[^.]{0,40}\b(?:now|soon|future)\b",
        30,
    ),
    PhraseRule(
        "sponsorship_temporary_future_001",
        "future_sponsorship_risk",
        "amber",
        r"\btemporary\s+right\s+to\s+work\s+in\s+the\s+uk[^.]{0,80}\b(?:need|require)[^.]{0,30}(?:visa\s+)?sponsorship\s+in\s+the\s+future\b",
        32,
    ),
    PhraseRule(
        "sponsorship_temporary_status_needs_001",
        "future_sponsorship_risk",
        "amber",
        r"\btemporary\s+right[-\s]+to[-\s]+work\s+status[^.]{0,100}\bsponsorship\s+needs\b",
        32,
    ),
    PhraseRule(
        "sponsorship_temporary_work_needs_001",
        "future_sponsorship_risk",
        "amber",
        r"\btemporary\s+right\s+to\s+work[^.]{0,100}\bsponsorship\s+needs\b",
        32,
    ),
    PhraseRule(
        "sponsorship_future_question_001",
        "future_sponsorship_risk",
        "amber",
        r"\b(?:will\s+(?:you\s+)?(?:now\s+or\s+in\s+the\s+future\s+)?require|(?:visa\s+)?sponsorship\s+will\s+be\s+required)(?:\s+(?:visa\s+)?sponsorship)?(?:\s+at\s+any\s+point)?\b",
        32,
    ),
    PhraseRule(
        "sponsorship_future_before_require_001",
        "future_sponsorship_risk",
        "amber",
        r"\b(?:now\s+or\s+in\s+the\s+future|at\s+any\s+point)[^.]{0,80}\brequire\s+(?:visa\s+)?sponsorship\b",
        32,
    ),
    PhraseRule(
        "sponsor_positive_visa_available_001",
        "sponsorship_positive",
        "green",
        r"\b(?:skilled\s+worker\s+)?visa\s+sponsorship\s+(?:is\s+)?available\b",
        25,
    ),
    PhraseRule(
        "sponsor_positive_registered_001",
        "sponsorship_positive",
        "green",
        r"\bregistered\s+visa\s+sponsor\b",
        25,
    ),
    PhraseRule(
        "sponsor_positive_cos_001",
        "sponsorship_positive",
        "green",
        r"\bcertificate\s+of\s+sponsorship\b",
        25,
    ),
    PhraseRule(
        "sponsor_positive_can_sponsor_001",
        "sponsorship_positive",
        "green",
        r"\bwe\s+(?:can|are\s+able\s+to)\s+sponsor\b",
        25,
    ),
    PhraseRule(
        "sponsor_positive_considered_001",
        "sponsorship_positive",
        "green",
        r"\bsponsorship\s+(?:(?:is|may\s+be)\s+)?considered\b",
        25,
    ),
    PhraseRule(
        "sponsor_positive_case_by_case_001",
        "sponsorship_positive",
        "green",
        r"\bconsider[s]?\s+sponsorship\s+(?:on\s+a\s+)?case\s+by\s+case(?:\s+basis)?\b",
        25,
    ),
    PhraseRule(
        "sponsorship_case_by_case_ambiguous_001",
        "ambiguous",
        "amber",
        r"\bcase\s+by\s+case(?:\s+basis)?\b",
        24,
    ),
    PhraseRule(
        "sponsorship_not_every_role_001",
        "ambiguous",
        "amber",
        r"\b(?:not\s+able\s+to|cannot)\s+offer\s+(?:it|sponsorship)\s+for\s+every\s+role\b",
        25,
    ),
    PhraseRule(
        "security_sc_001",
        "security_clearance",
        "amber",
        r"\b(?:sc|dv)\s+clearance\b",
        20,
    ),
    PhraseRule(
        "security_cleared_001",
        "security_clearance",
        "amber",
        r"\bsecurity\s+cleared\b",
        20,
    ),
    PhraseRule(
        "security_uk_eyes_001",
        "security_clearance",
        "amber",
        r"\buk\s+eyes\s+only\b",
        20,
    ),
    PhraseRule(
        "security_residency_001",
        "security_clearance",
        "amber",
        r"\b(?:5|five)\s+years?\s+uk\s+residency\b",
        20,
    ),
    PhraseRule(
        "rtw_ambiguous_001",
        "ambiguous",
        "amber",
        r"\bmust\s+have\s+(?:the\s+)?right\s+to\s+work\s+in\s+the\s+uk\b",
        10,
    ),
    PhraseRule(
        "rtw_all_applicants_001",
        "ambiguous",
        "amber",
        r"\ball\s+applicants\s+must\s+have\s+(?:the\s+)?right\s+to\s+work\s+in\s+the\s+uk\b",
        11,
    ),
    PhraseRule(
        "rtw_legal_question_001",
        "ambiguous",
        "amber",
        r"\b(?:do\s+you\s+have\s+(?:the\s+)?)?legal\s+right\s+to\s+work\s+in\s+(?:the\s+uk|uk|london|england|scotland|wales|northern\s+ireland)(?:\?)?",
        10,
    ),
    PhraseRule(
        "sponsorship_needed_option_001",
        "ambiguous",
        "amber",
        r"\b(?:i\s+)?(?:will\s+)?(?:need|require)\s+(?:visa\s+)?sponsorship(?:\s+soon|\s+to\s+start\s+this\s+role)?\b",
        10,
    ),
    PhraseRule(
        "rtw_generic_001",
        "ambiguous",
        "amber",
        r"\bright\s+to\s+work\s+in\s+(?:the\s+uk|uk|london|england|scotland|wales|northern\s+ireland)\b",
        5,
    ),
    PhraseRule(
        "rtw_eligible_generic_001",
        "ambiguous",
        "amber",
        r"\b(?:eligible|eligibility)\s+to\s+work\s+in\s+(?:the\s+uk|uk|london|england|scotland|wales|northern\s+ireland)\b",
        5,
    ),
    PhraseRule(
        "rtw_must_be_eligible_001",
        "ambiguous",
        "amber",
        r"\bmust\s+be\s+eligible\s+to\s+work\s+in\s+(?:the\s+uk|uk|london|england|scotland|wales|northern\s+ireland)\b",
        6,
    ),
]


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _overlaps(left: PhraseSignal, right_start: int, right_end: int) -> bool:
    return left.start_index < right_end and right_start < left.end_index


def _keep_signal(existing: PhraseSignal, candidate: PhraseSignal) -> PhraseSignal:
    existing_rule = next(rule for rule in PHRASE_RULES if rule.rule_id == existing.rule_id)
    candidate_rule = next(rule for rule in PHRASE_RULES if rule.rule_id == candidate.rule_id)
    if candidate_rule.priority > existing_rule.priority:
        return candidate
    if candidate_rule.priority == existing_rule.priority:
        existing_len = existing.end_index - existing.start_index
        candidate_len = candidate.end_index - candidate.start_index
        if candidate_len > existing_len:
            return candidate
    return existing


def scan_description(description_text: str) -> List[PhraseSignal]:
    """Scan a job description and return explainable phrase signals."""

    if not description_text:
        return []

    signals: List[PhraseSignal] = []
    for rule in PHRASE_RULES:
        for match in re.finditer(rule.pattern, description_text, flags=re.IGNORECASE):
            candidate = PhraseSignal(
                category=rule.category,
                severity=rule.severity,
                text=_clean_text(match.group(0)),
                start_index=match.start(),
                end_index=match.end(),
                rule_id=rule.rule_id,
            )

            overlap_index = None
            for index, existing in enumerate(signals):
                if _overlaps(existing, candidate.start_index, candidate.end_index):
                    overlap_index = index
                    break

            if overlap_index is None:
                signals.append(candidate)
            else:
                signals[overlap_index] = _keep_signal(signals[overlap_index], candidate)

    return sorted(signals, key=lambda signal: (signal.start_index, signal.end_index))


def has_category(signals: Iterable[PhraseSignal], category: str) -> bool:
    return any(signal.category == category for signal in signals)
