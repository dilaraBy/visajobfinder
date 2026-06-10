"""Status-aware visa-risk classifier."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Iterable, List, Optional

from pipeline.classifier.models import (
    ClassificationResult,
    EmployerMatch,
    JobInput,
    PhraseSignal,
    UserContext,
)
from pipeline.classifier.phrase_scanner import scan_description
from pipeline.sponsor_register.matcher import SponsorMatcher
from pipeline.sponsor_register.normalise import normalise_employer_name


DECISIVE_BLOCKERS = {"citizenship_required", "permanent_right_to_work"}
# For Graduate Route users, only citizenship requirements are hard blockers.
# Permanent / unrestricted right-to-work phrases are form questions about RTW
# status, not citizenship mandates — they are verify_first for GR, not decisive.
GRADUATE_ROUTE_DECISIVE_BLOCKERS = {"citizenship_required"}
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _categories(signals: Iterable[PhraseSignal]) -> set:
    return {signal.category for signal in signals}


def _phrase_evidence(signals: Iterable[PhraseSignal]) -> List[Dict[str, Any]]:
    return [
        {
            "type": "phrase_signal",
            "category": signal.category,
            "severity": signal.severity,
            "text": signal.text,
            "start_index": signal.start_index,
            "end_index": signal.end_index,
            "rule_id": signal.rule_id,
        }
        for signal in signals
    ]


def _base_limitations(match: EmployerMatch) -> List[str]:
    limitations = [
        "This is a visa-risk triage label, not legal or immigration advice.",
        "The engine only uses loaded sponsor-register data and phrases found in the job text.",
    ]
    if match.is_match:
        limitations.append(
            "Sponsor-register presence does not prove this specific role will be sponsored."
        )
    else:
        limitations.append(
            "No reliable sponsor-register match in the loaded data does not prove the employer lacks a licence."
        )
    return limitations


def _base_verification(user: UserContext) -> List[str]:
    prompts = ["Verify the role-level right-to-work and sponsorship position with the employer."]
    if user.visa_situation == "graduate_route":
        prompts.append(
            "Ask whether this specific role can be sponsored before your current visa expires if you will need future sponsorship."
        )
    elif user.visa_situation == "needs_sponsorship_before_start":
        prompts.append(
            "Ask whether sponsorship is available before the job start date for this specific role."
        )
    else:
        prompts.append("Set the closest visa situation before relying on the label.")
    return prompts


def _parse_year_month(value: Optional[str]) -> Optional[tuple[int, int]]:
    if not value or not MONTH_RE.match(value):
        return None
    year, month = value.split("-")
    parsed = (int(year), int(month))
    if not 1 <= parsed[1] <= 12:
        return None
    return parsed


def _target_start_after_visa_expiry(user: UserContext) -> bool:
    expiry = _parse_year_month(user.visa_expiry_month)
    start = _parse_year_month(user.target_start_month)
    return bool(expiry and start and start > expiry)


def _has_numeric_salary(job: JobInput) -> bool:
    if job.salary_min is not None or job.salary_max is not None:
        return True
    return bool(re.search(r"\d", job.salary_text or ""))


def _employer_evidence(match: EmployerMatch) -> Dict[str, Any]:
    if match.is_match:
        return {
            "type": "sponsor_register",
            "category": "sponsor_match",
            "text": (
                f"Sponsor-register match found: {match.matched_name} "
                f"({match.confidence_band} confidence)."
            ),
        }
    if match.matched_name:
        return {
            "type": "sponsor_register",
            "category": "low_confidence_candidate",
            "text": (
                f"Low-confidence sponsor-register candidate: {match.matched_name} "
                f"({match.confidence:.2f})."
            ),
        }
    return {
        "type": "missing_evidence",
        "category": "sponsor_match",
        "text": "No reliable sponsor-register match found in the loaded sponsor data.",
    }


def _missing_phrase_evidence(description_text: str) -> Dict[str, Any]:
    if description_text:
        text = "No visa-risk phrase matched the current deterministic phrase rules."
    else:
        text = "Job description is missing, so phrase evidence could not be scanned."
    return {
        "type": "missing_evidence",
        "category": "jd_phrase",
        "text": text,
    }


def _has_future_no_sponsor(signals: Iterable[PhraseSignal]) -> bool:
    for signal in signals:
        if signal.category != "no_sponsorship":
            continue
        text = signal.text.lower()
        if "future" in text or "must not require sponsorship" in text:
            return True
    return False


def _result(
    job: JobInput,
    label: str,
    reason: str,
    evidence: List[Dict[str, Any]],
    match: EmployerMatch,
    what_to_verify: List[str],
    limitations: List[str],
) -> ClassificationResult:
    return ClassificationResult(
        job_id=job.job_id,
        label=label,
        reason=reason,
        evidence=evidence,
        employer_match=match.to_dict(),
        what_to_verify=what_to_verify,
        limitations=limitations,
    )


def classify_job(
    job: JobInput,
    user: UserContext,
    matcher: SponsorMatcher,
    phrase_signals: Optional[List[PhraseSignal]] = None,
    employer_match: Optional[EmployerMatch] = None,
) -> ClassificationResult:
    """Classify a job using deterministic status-aware rules."""

    match = employer_match or matcher.match(job.employer_raw)
    signals = phrase_signals if phrase_signals is not None else scan_description(job.description_text)
    categories = _categories(signals)

    evidence = _phrase_evidence(signals)
    if not evidence:
        evidence.append(_missing_phrase_evidence(job.description_text))
    evidence.append(_employer_evidence(match))

    limitations = _base_limitations(match)
    what_to_verify = _base_verification(user)

    if not job.employer_raw.strip():
        limitations.append("Employer name is missing, so sponsor-register matching could not run.")
    if not job.description_text.strip():
        limitations.append("Job description is missing, so phrase scanning could not run.")
    if not job.salary_text:
        limitations.append("Salary is missing; Skilled Worker salary and occupation requirements were not assessed.")
    elif not _has_numeric_salary(job):
        limitations.append("Salary text is present but no numeric salary could be assessed.")
    if _target_start_after_visa_expiry(user):
        limitations.append(
            "Target start month appears after the visa expiry month; sponsorship timing needs direct verification."
        )

    # Graduate Route users have current legal right to work; only citizenship
    # mandates are decisive for them.  All other visa situations treat
    # permanent / unrestricted RTW phrases as decisive blockers too.
    active_decisive_blockers = (
        GRADUATE_ROUTE_DECISIVE_BLOCKERS
        if user.visa_situation == "graduate_route"
        else DECISIVE_BLOCKERS
    )
    if active_decisive_blockers & categories:
        return _result(
            job,
            "likely_blocked",
            "The job ad contains a citizenship or permanent right-to-work requirement that is a strong blocker for the selected visa situation.",
            evidence,
            match,
            what_to_verify
            + ["Ask whether the requirement is mandatory and whether any visa route is accepted."],
            limitations,
        )

    if "no_sponsorship" in categories and "sponsorship_positive" in categories:
        return _result(
            job,
            "verify_first",
            "The job ad contains contradictory sponsorship wording, so the role-level position needs direct verification.",
            evidence,
            match,
            what_to_verify
            + ["Ask the employer to clarify whether the no-sponsorship wording or sponsorship-positive wording applies to this role."],
            limitations,
        )

    if "no_sponsorship" in categories:
        if user.visa_situation == "needs_sponsorship_before_start" or user.needs_sponsorship_before_start:
            return _result(
                job,
                "likely_blocked",
                "The job ad says sponsorship is not available, which is a strong blocker for someone needing sponsorship before starting.",
                evidence,
                match,
                what_to_verify,
                limitations,
            )
        if user.visa_situation == "graduate_route" and user.needs_future_sponsorship:
            label = "likely_blocked" if _has_future_no_sponsor(signals) else "verify_first"
            reason = (
                "The job ad says candidates must not require sponsorship now or in the future."
                if label == "likely_blocked"
                else "The job ad says sponsorship is not available; a Graduate Route user may be able to work now, but future sponsorship needs verification."
            )
            return _result(job, label, reason, evidence, match, what_to_verify, limitations)
        return _result(
            job,
            "verify_first",
            "The job ad says sponsorship is not available; verify whether that affects your selected visa situation.",
            evidence,
            match,
            what_to_verify,
            limitations,
        )

    if not job.description_text.strip():
        return _result(
            job,
            "unknown",
            "The job description is missing, so the engine cannot scan for visa-risk wording.",
            evidence,
            match,
            what_to_verify,
            limitations,
        )

    if not job.employer_raw.strip():
        return _result(
            job,
            "unknown",
            "Employer name is missing, so the sponsor-register signal cannot be assessed.",
            evidence,
            match,
            what_to_verify,
            limitations,
        )

    if "security_clearance" in categories:
        return _result(
            job,
            "verify_first",
            "The job ad mentions security clearance or residency requirements, but the exact visa impact is unclear.",
            evidence,
            match,
            what_to_verify
            + ["Ask whether clearance requires UK citizenship, indefinite leave to remain, or a fixed UK residency history."],
            limitations,
        )

    if user.visa_situation == "unknown":
        return _result(
            job,
            "unknown",
            "The selected visa situation is unknown, so status-aware rules cannot be applied reliably.",
            evidence,
            match,
            what_to_verify,
            limitations,
        )

    if user.visa_situation == "needs_sponsorship_before_start" or user.needs_sponsorship_before_start:
        # Ambiguous future-sponsorship question with no positive signal is a blocker
        # for someone who needs sponsorship before starting.
        if "future_sponsorship_risk" in categories and "sponsorship_positive" not in categories:
            return _result(
                job,
                "verify_first",
                "The job ad asks about right to work now and in the future, which is ambiguous for someone who needs sponsorship before starting.",
                evidence,
                match,
                what_to_verify
                + ["Ask whether needing Skilled Worker sponsorship before the start date would prevent progressing for this role."],
                limitations,
            )
        if match.confidence_band == "low":
            return _result(
                job,
                "unknown",
                "Only a low-confidence sponsor-register candidate was found, so the employer signal is not reliable enough.",
                evidence,
                match,
                what_to_verify,
                limitations,
            )
        if match.confidence_band == "medium":
            return _result(
                job,
                "verify_first",
                "Only a medium-confidence sponsor-register match was found, so sponsorship availability for this role needs direct verification.",
                evidence,
                match,
                what_to_verify
                + ["Confirm the exact hiring entity and whether it can sponsor this specific vacancy before the start date."],
                limitations,
            )
        if not match.is_match:
            return _result(
                job,
                "verify_first",
                "No reliable sponsor-register match was found in the loaded data for an applicant who needs sponsorship before starting.",
                evidence,
                match,
                what_to_verify,
                limitations,
            )
        if "sponsorship_positive" not in categories:
            return _result(
                job,
                "verify_first",
                "Employer appears on the sponsor register, but the job ad does not clearly say this role offers sponsorship.",
                evidence,
                match,
                what_to_verify
                + ["Ask whether sponsorship is available for this specific vacancy, not only whether the employer has a licence."],
                limitations,
            )
        if not job.salary_text:
            return _result(
                job,
                "verify_first",
                "The employer appears on the sponsor register and the ad mentions sponsorship, but salary is missing.",
                evidence,
                match,
                what_to_verify
                + ["Ask for the salary range and check it against current Skilled Worker salary and occupation rules."],
                limitations,
            )
        if not _has_numeric_salary(job):
            return _result(
                job,
                "verify_first",
                "The employer appears on the sponsor register and the ad mentions sponsorship, but the salary is not numeric enough to assess.",
                evidence,
                match,
                what_to_verify
                + ["Ask for the salary range and check it against current Skilled Worker salary and occupation rules."],
                limitations,
            )
        return _result(
            job,
            "worth_applying",
            "No detected blocker for the selected visa situation; sponsor-register and sponsorship-positive signals are present.",
            evidence,
            match,
            what_to_verify
            + ["Confirm the sponsor route, salary, occupation code, and start-date timing before treating the role as viable."],
            limitations,
        )

    if user.visa_situation == "graduate_route":
        if _target_start_after_visa_expiry(user):
            return _result(
                job,
                "verify_first",
                "The target start month appears after the visa expiry month, so timing must be checked before treating the role as viable.",
                evidence,
                match,
                what_to_verify
                + ["Confirm whether sponsorship would be needed before the role starts."],
                limitations,
            )
        # Permanent / unrestricted RTW phrasing is not a citizenship mandate, but it
        # does signal the employer expects unrestricted RTW; verify whether the
        # Graduate Route visa satisfies that requirement for this role.
        if "permanent_right_to_work" in categories:
            return _result(
                job,
                "verify_first",
                "The job ad mentions unrestricted or permanent right-to-work wording; verify whether the Graduate Route visa satisfies that requirement for this role.",
                evidence,
                match,
                what_to_verify
                + ["Ask the employer whether a Graduate Route visa is accepted for this role."],
                limitations,
            )
        # Graduate Route users have current right to work; a future-sponsorship
        # question in the JD is verify_first UNLESS the employer is on the
        # sponsor register AND the JD contains sponsorship-positive wording
        # (e.g. "considered case by case"), which together give sufficient
        # signal that the role may accommodate future sponsorship needs.
        if "future_sponsorship_risk" in categories:
            if "sponsorship_positive" in categories and match.is_match:
                pass  # fall through to worth_applying below
            else:
                return _result(
                    job,
                    "verify_first",
                    "The job ad asks about right to work now and in the future, which is ambiguous for visa-risk triage.",
                    evidence,
                    match,
                    what_to_verify
                    + ["Ask whether needing Skilled Worker sponsorship later would prevent progressing for this role."],
                    limitations,
                )
        if user.needs_future_sponsorship and match.confidence_band == "low":
            return _result(
                job,
                "unknown",
                "A low-confidence sponsor-register candidate was found, which is not enough to judge future sponsorship risk.",
                evidence,
                match,
                what_to_verify,
                limitations,
            )
        if user.needs_future_sponsorship and match.confidence_band == "medium":
            return _result(
                job,
                "verify_first",
                "A medium-confidence sponsor-register match was found, which needs verification before relying on future sponsorship prospects.",
                evidence,
                match,
                what_to_verify
                + ["Confirm the exact sponsoring entity and whether it maps to the employer named in the job ad."],
                limitations,
            )
        # No sponsor match is only a verify_first signal when the JD itself raises
        # a future-sponsorship question; if the JD has no explicit blocker the
        # Graduate Route user has current right to work and can apply.
        if user.needs_future_sponsorship and not match.is_match and "future_sponsorship_risk" in categories:
            return _result(
                job,
                "verify_first",
                "No reliable sponsor-register match was found, which matters if future Skilled Worker sponsorship may be needed.",
                evidence,
                match,
                what_to_verify,
                limitations,
            )
        return _result(
            job,
            "worth_applying",
            "No detected blocker for the selected Graduate Route situation based on the current job text and sponsor-register signal.",
            evidence,
            match,
            what_to_verify,
            limitations,
        )

    return _result(
        job,
        "unknown",
        "The engine did not have enough reliable evidence to classify this job for the selected visa situation.",
        evidence,
        match,
        what_to_verify,
        limitations,
    )


def build_job_record(
    job: JobInput,
    employer_match: EmployerMatch,
    phrase_signals: List[PhraseSignal],
    description_scope: str = "full",
) -> Dict[str, Any]:
    if description_scope not in {"full", "excerpt", "missing"}:
        raise ValueError("description_scope must be one of: full, excerpt, missing")

    description_hash = hashlib.sha256(job.description_text.encode("utf-8")).hexdigest()
    base_limitations = _base_limitations(employer_match)
    if description_scope == "excerpt":
        base_limitations.append(
            "Only a description excerpt was stored; phrase scanning may not cover the full job ad."
        )
    elif description_scope == "missing":
        base_limitations.append("No description text was stored; phrase scanning could not run.")

    return {
        "job_id": job.job_id,
        "source": job.source,
        "source_job_id": job.source_job_id,
        "title": job.title,
        "employer_raw": job.employer_raw,
        "description_text": job.description_text,
        "description_hash": description_hash,
        "description_scope": description_scope,
        "location": {
            "raw": job.location,
            "city": job.location,
            "country": "UK" if job.location else None,
            "remote_type": "unknown",
        },
        "salary": {
            "raw": job.salary_text,
            "min": job.salary_min,
            "max": job.salary_max,
            "currency": "GBP" if job.salary_text else None,
            "period": "year" if job.salary_text else None,
            "is_missing": not bool(job.salary_text),
        },
        "dates": {
            "posted_at": job.posted_at,
            "closing_at": job.closing_at,
            "fetched_at": job.fetched_at,
        },
        "url": job.url,
        "normalised": {
            "title_tokens": [token for token in job.title.lower().split() if token],
            "employer_normalised": normalise_employer_name(job.employer_raw),
        },
        "visa_signals": {
            "employer_match": employer_match.to_dict(),
            "phrase_signals": [signal.to_dict() for signal in phrase_signals],
            "base_limitations": base_limitations,
        },
    }


def analyse_job(
    job: JobInput,
    user: UserContext,
    matcher: SponsorMatcher,
) -> Dict[str, Any]:
    """Return a data-contract-shaped job record plus classification result."""

    employer_match = matcher.match(job.employer_raw)
    phrase_signals = scan_description(job.description_text)
    classification = classify_job(
        job=job,
        user=user,
        matcher=matcher,
        phrase_signals=phrase_signals,
        employer_match=employer_match,
    )
    return {
        "job": build_job_record(job, employer_match, phrase_signals),
        "classification": classification.to_dict(),
    }
