"""Evaluate the deterministic visa-risk engine against labelled records."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from pipeline.classifier.engine import analyse_job
from pipeline.classifier.models import ALLOWED_LABELS, JobInput, UserContext
from pipeline.sponsor_register.matcher import SponsorMatcher


DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "data" / "eval" / "labelled_jobs.sample.json"
DEFAULT_SPONSOR_REGISTER = (
    Path(__file__).resolve().parents[2] / "data" / "sponsor_register" / "sample_sponsors.csv"
)
EXPECTED_CATEGORY_ALIASES = {
    "right_to_work": "ambiguous",
    "sponsorship_needed_option": "ambiguous",
}
AMBIGUOUS_RIGHT_TO_WORK_COVERING_CATEGORIES = {
    "no_sponsorship",
    "permanent_right_to_work",
    "future_sponsorship_risk",
}
IGNORED_EXPECTED_EVIDENCE_CATEGORIES = {
    "graduate_signal",
    "temporary_work_window",
}
ALLOWED_REVIEW_STATUSES = {
    "needs_review",
    "confirmed",
    "change_recommended",
    "remove_from_eval",
}
ALLOWED_EVAL_USE = {
    "classification_and_evidence",
    "classification_only",
    "evidence_only",
    "sponsor_matching",
    "exclude",
}
TARGET_DASHBOARD_ROLE_LEVELS = {
    "internship",
    "graduate",
    "graduate_scheme",
    "entry_level",
    "junior",
    "junior_or_mid",
    "associate",
    "graduate_to_senior",
}
MAX_PUBLIC_EXCERPT_CHARS = 1200


@dataclass
class SituationMetrics:
    total: int = 0
    false_red: int = 0
    false_green: int = 0
    unknown: int = 0
    verify_first: int = 0
    exact_label: int = 0


@dataclass
class EvidenceMetrics:
    total_cases: int = 0
    matched_cases: int = 0
    misses: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class SponsorMetrics:
    labelled_records: int = 0
    labelled_decision_correct: int = 0
    high_confidence_predictions: int = 0
    high_confidence_correct: int = 0
    false_positive_examples: List[Dict[str, str]] = field(default_factory=list)
    failure_case_examples: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ValidationReport:
    records_checked: int = 0
    records_in_eval: int = 0
    records_excluded: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def pct(numerator: int, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    return (numerator / denominator) * 100


def rate_dict(numerator: int, denominator: int) -> Dict[str, Any]:
    return {
        "count": numerator,
        "total": denominator,
        "rate": pct(numerator, denominator),
    }


def load_dataset(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {
            "schema_version": 0,
            "name": path.stem,
            "records": data,
        }
    if "records" not in data or not isinstance(data["records"], list):
        raise ValueError("Evaluation dataset must contain a top-level records array.")
    return data


def _record_eval_use(record: Dict[str, Any]) -> str:
    return str(record.get("eval_use") or "classification_and_evidence")


def _record_is_excluded(record: Dict[str, Any]) -> bool:
    return (
        record.get("review_status") == "remove_from_eval"
        or _record_eval_use(record) == "exclude"
    )


def _record_uses_evidence_metric(record: Dict[str, Any]) -> bool:
    return _record_eval_use(record) in {"classification_and_evidence", "evidence_only"}


def _records_for_eval(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [record for record in records if not _record_is_excluded(record)]


def validate_dataset(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """Validate labelled eval data without making legal/eligibility claims."""

    report = ValidationReport()
    seen_ids = set()
    for index, record in enumerate(dataset.get("records") or []):
        report.records_checked += 1
        record_id = _record_id(record)
        if record_id in seen_ids:
            report.errors.append(f"{record_id}: duplicate record id")
        seen_ids.add(record_id)

        review_status = record.get("review_status")
        if review_status is not None and review_status not in ALLOWED_REVIEW_STATUSES:
            report.errors.append(f"{record_id}: unsupported review_status {review_status!r}")

        eval_use = _record_eval_use(record)
        if eval_use not in ALLOWED_EVAL_USE:
            report.errors.append(f"{record_id}: unsupported eval_use {eval_use!r}")

        dashboard_fit = record.get("default_dashboard_fit")
        if dashboard_fit is not None and not isinstance(dashboard_fit, bool):
            report.errors.append(f"{record_id}: default_dashboard_fit must be boolean when present")

        if _record_is_excluded(record):
            report.records_excluded += 1
            continue

        report.records_in_eval += 1
        expected_cases = _cases_from_record(record)
        if not expected_cases:
            report.errors.append(f"{record_id}: no executable evaluation cases")

        if not str(record.get("title") or "").strip():
            report.errors.append(f"{record_id}: title is missing")
        if not str(record.get("employer_raw") or "").strip():
            report.warnings.append(f"{record_id}: employer_raw is missing")
        if not str(record.get("description_text") or "").strip():
            report.warnings.append(f"{record_id}: description_text excerpt is missing")
        elif len(str(record.get("description_text"))) > MAX_PUBLIC_EXCERPT_CHARS:
            report.warnings.append(
                f"{record_id}: description_text is longer than {MAX_PUBLIC_EXCERPT_CHARS} chars; "
                "confirm this is an excerpt, not a full copied job description"
            )

        role_level = record.get("role_level")
        if dashboard_fit is not None and role_level:
            expected_fit = role_level in TARGET_DASHBOARD_ROLE_LEVELS
            if dashboard_fit != expected_fit:
                report.warnings.append(
                    f"{record_id}: default_dashboard_fit={dashboard_fit} does not match "
                    f"role_level={role_level!r} default rule"
                )

        for case in expected_cases:
            expected_label = case.get("expected_label")
            if expected_label not in ALLOWED_LABELS:
                report.errors.append(
                    f"{case.get('case_id', record_id)}: unsupported expected_label {expected_label!r}"
                )

    return {
        "records_checked": report.records_checked,
        "records_in_eval": report.records_in_eval,
        "records_excluded": report.records_excluded,
        "warnings": report.warnings,
        "errors": report.errors,
    }


def _job_from_record(record: Dict[str, Any]) -> JobInput:
    return JobInput(
        job_id=record.get("eval_id") or record.get("record_id") or "eval:unknown",
        source=record.get("source", "eval"),
        title=record.get("title", ""),
        employer_raw=record.get("employer_raw", ""),
        description_text=record.get("description_text", ""),
        location=record.get("location"),
        salary_text=record.get("salary_text"),
        salary_min=record.get("salary_min"),
        salary_max=record.get("salary_max"),
        url=record.get("url") or record.get("source_url"),
    )


def _record_id(record: Dict[str, Any]) -> str:
    return str(record.get("eval_id") or record.get("record_id") or "eval:unknown")


def _expected_evidence_from_record(record: Dict[str, Any]) -> List[Dict[str, str]]:
    expected = []
    description = " ".join(str(record.get("description_text") or "").lower().split())
    for phrase in record.get("evidence_phrases") or []:
        item: Dict[str, str] = {}
        category = phrase.get("category")
        text = phrase.get("text")
        if category in IGNORED_EXPECTED_EVIDENCE_CATEGORIES:
            continue
        category = EXPECTED_CATEGORY_ALIASES.get(category, category)
        if category:
            item["category"] = str(category)
        if text and " ".join(str(text).lower().split()) in description:
            item["text_contains"] = str(text)
        if item:
            expected.append(item)
    return expected


def _cases_from_record(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    cases = record.get("cases")
    if isinstance(cases, list):
        return cases

    expected_labels = record.get("expected_labels")
    if not isinstance(expected_labels, dict):
        return []

    record_id = _record_id(record)
    expected_evidence = _expected_evidence_from_record(record)
    generated_cases = []
    for visa_situation, expected_label in expected_labels.items():
        generated_cases.append(
            {
                "case_id": f"{record_id}:{visa_situation}",
                "user_context": {
                    "visa_situation": visa_situation,
                    "needs_sponsorship_before_start": (
                        visa_situation == "needs_sponsorship_before_start"
                    ),
                    "needs_future_sponsorship": True,
                },
                "expected_label": expected_label,
                "expected_evidence": expected_evidence,
                "notes": record.get("human_notes"),
            }
        )
    return generated_cases


def _user_from_case(case: Dict[str, Any]) -> UserContext:
    context = case.get("user_context") or {}
    return UserContext(
        visa_situation=context.get("visa_situation", "unknown"),
        visa_expiry_month=context.get("visa_expiry_month"),
        needs_sponsorship_before_start=bool(
            context.get("needs_sponsorship_before_start", False)
        ),
        needs_future_sponsorship=bool(context.get("needs_future_sponsorship", False)),
        target_start_month=context.get("target_start_month"),
    )


def _normalised_text(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _evidence_item_matches(
    actual: Dict[str, Any],
    expected: Dict[str, Any],
) -> bool:
    expected_category = expected.get("category")
    actual_category = actual.get("category")
    category_matches = not expected_category or actual_category == expected_category
    if (
        not category_matches
        and expected_category == "ambiguous"
        and actual_category in AMBIGUOUS_RIGHT_TO_WORK_COVERING_CATEGORIES
    ):
        category_matches = True
    if not category_matches:
        return False

    expected_type = expected.get("type")
    if expected_type and actual.get("type") != expected_type:
        return False

    text_contains = expected.get("text_contains")
    if text_contains:
        actual_text = _normalised_text(actual.get("text"))
        expected_text = _normalised_text(text_contains)
        if expected_text not in actual_text:
            return False

    return True


def evidence_matches(
    actual_evidence: Iterable[Dict[str, Any]],
    expected_evidence: Iterable[Dict[str, Any]],
) -> bool:
    actual_items = list(actual_evidence)
    for expected in expected_evidence:
        if not any(_evidence_item_matches(actual, expected) for actual in actual_items):
            return False
    return True


def _expected_sponsor_match(
    predicted: Dict[str, Any],
    expected: Dict[str, Any],
) -> bool:
    if not expected.get("is_match", False):
        return False
    expected_name = expected.get("matched_name")
    if expected_name and predicted.get("matched_name") != expected_name:
        return False
    return True


def _sponsor_prediction_matches_expected(
    predicted: Dict[str, Any],
    expected: Dict[str, Any],
) -> bool:
    if not expected.get("is_match", False):
        return not predicted.get("is_match", False)
    return _expected_sponsor_match(predicted, expected)


def _update_sponsor_metrics(
    metrics: SponsorMetrics,
    record: Dict[str, Any],
    matcher: SponsorMatcher,
) -> None:
    expected = record.get("sponsor_match_expected") or {}
    if not expected.get("available", False):
        return

    metrics.labelled_records += 1
    predicted = matcher.match(record.get("employer_raw", "")).to_dict()
    if _sponsor_prediction_matches_expected(predicted, expected):
        metrics.labelled_decision_correct += 1
    else:
        metrics.failure_case_examples.append(
            {
                "eval_id": _record_id(record),
                "employer_raw": str(record.get("employer_raw", "")),
                "predicted": str(predicted.get("matched_name")),
                "predicted_band": str(predicted.get("confidence_band")),
                "expected": str(expected.get("matched_name")),
                "expected_is_match": str(expected.get("is_match", False)),
            }
        )

    if predicted.get("confidence_band") != "high" or not predicted.get("is_match"):
        return

    metrics.high_confidence_predictions += 1
    if _expected_sponsor_match(predicted, expected):
        metrics.high_confidence_correct += 1
        return

    metrics.false_positive_examples.append(
        {
            "eval_id": _record_id(record),
            "employer_raw": str(record.get("employer_raw", "")),
            "predicted": str(predicted.get("matched_name")),
            "expected": str(expected.get("matched_name")),
        }
    )


def evaluate_dataset(
    dataset: Dict[str, Any],
    matcher: SponsorMatcher,
) -> Dict[str, Any]:
    by_situation: Dict[str, SituationMetrics] = {}
    evidence_metrics = EvidenceMetrics()
    sponsor_metrics = SponsorMetrics()
    case_results: List[Dict[str, Any]] = []

    validation = validate_dataset(dataset)
    if validation["errors"]:
        raise ValueError("Evaluation dataset validation failed: " + "; ".join(validation["errors"]))

    records = _records_for_eval(dataset["records"])
    for record in records:
        _update_sponsor_metrics(sponsor_metrics, record, matcher)
        job = _job_from_record(record)
        for case in _cases_from_record(record):
            expected_label = case.get("expected_label")
            if expected_label not in ALLOWED_LABELS:
                raise ValueError(
                    f"{case.get('case_id', _record_id(record))} has unsupported expected_label: {expected_label}"
                )

            user = _user_from_case(case)
            output = analyse_job(job, user, matcher)
            classification = output["classification"]
            predicted_label = classification["label"]
            situation = user.visa_situation

            metrics = by_situation.setdefault(situation, SituationMetrics())
            metrics.total += 1
            metrics.false_red += int(
                predicted_label == "likely_blocked"
                and expected_label in {"worth_applying", "verify_first"}
            )
            metrics.false_green += int(
                predicted_label == "worth_applying" and expected_label == "likely_blocked"
            )
            metrics.unknown += int(predicted_label == "unknown")
            metrics.verify_first += int(predicted_label == "verify_first")
            metrics.exact_label += int(predicted_label == expected_label)

            expected_evidence = case.get("expected_evidence") or []
            evidence_ok = None
            if expected_evidence and _record_uses_evidence_metric(record):
                evidence_metrics.total_cases += 1
                evidence_ok = evidence_matches(classification["evidence"], expected_evidence)
                if evidence_ok:
                    evidence_metrics.matched_cases += 1
                else:
                    evidence_metrics.misses.append(
                        {
                            "case_id": str(case.get("case_id", _record_id(record))),
                            "expected": json.dumps(expected_evidence),
                        }
                    )

            case_results.append(
                {
                    "case_id": case.get("case_id"),
                    "eval_id": _record_id(record),
                    "visa_situation": situation,
                    "expected_label": expected_label,
                    "predicted_label": predicted_label,
                    "evidence_ok": evidence_ok,
                    "reason": classification["reason"],
                }
            )

    situation_report = {
        situation: {
            "cases": metrics.total,
            "exact_label": rate_dict(metrics.exact_label, metrics.total),
            "false_red": rate_dict(metrics.false_red, metrics.total),
            "false_green": rate_dict(metrics.false_green, metrics.total),
            "unknown": rate_dict(metrics.unknown, metrics.total),
            "verify_first": rate_dict(metrics.verify_first, metrics.total),
        }
        for situation, metrics in sorted(by_situation.items())
    }

    sponsor_precision = pct(
        sponsor_metrics.high_confidence_correct,
        sponsor_metrics.high_confidence_predictions,
    )
    sponsor_decision_precision = pct(
        sponsor_metrics.labelled_decision_correct,
        sponsor_metrics.labelled_records,
    )

    return {
        "dataset": {
            "name": dataset.get("name"),
            "schema_version": dataset.get("schema_version"),
            "records": len(records),
            "records_available": len(dataset["records"]),
            "records_excluded": validation["records_excluded"],
            "cases": len(case_results),
            "validation_warnings": validation["warnings"],
        },
        "by_visa_situation": situation_report,
        "sponsor_matching": {
            "labelled_records": sponsor_metrics.labelled_records,
            "labelled_decision_correct": sponsor_metrics.labelled_decision_correct,
            "labelled_decision_precision": sponsor_decision_precision,
            "labelled_sponsor_precision": sponsor_decision_precision,
            "high_confidence_predictions": sponsor_metrics.high_confidence_predictions,
            "high_confidence_correct": sponsor_metrics.high_confidence_correct,
            "high_confidence_precision": sponsor_precision,
            "false_positive_examples": sponsor_metrics.false_positive_examples[:5],
            "failure_case_examples": sponsor_metrics.failure_case_examples[:5],
        },
        "evidence_extraction": {
            "cases_with_expected_evidence": evidence_metrics.total_cases,
            "matched_cases": evidence_metrics.matched_cases,
            "accuracy": pct(evidence_metrics.matched_cases, evidence_metrics.total_cases),
            "misses": evidence_metrics.misses[:5],
        },
        "case_results": case_results,
    }


def _format_rate(rate: Dict[str, Any]) -> str:
    value = rate["rate"]
    if value is None:
        return f"{rate['count']}/{rate['total']} (n/a)"
    return f"{rate['count']}/{rate['total']} ({value:.1f}%)"


def _format_optional_percent(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}%"


def format_report(report: Dict[str, Any]) -> str:
    dataset = report["dataset"]
    lines = [
        "Visa Engine Evaluation",
        "======================",
        f"Dataset: {dataset.get('name') or 'unnamed'}",
        f"Records: {dataset['records']}",
        f"Records excluded: {dataset.get('records_excluded', 0)}",
        f"Classification cases: {dataset['cases']}",
    ]

    if dataset.get("validation_warnings"):
        lines.extend(["", "Dataset validation warnings", "---------------------------"])
        for warning in dataset["validation_warnings"][:5]:
            lines.append(f"  {warning}")

    lines.extend(
        [
            "",
            "Classification by visa situation",
            "---------------------------------",
        ]
    )

    for situation, metrics in report["by_visa_situation"].items():
        lines.extend(
            [
                f"{situation}:",
                f"  Exact label: {_format_rate(metrics['exact_label'])}",
                f"  False red rate: {_format_rate(metrics['false_red'])}",
                f"  False green rate: {_format_rate(metrics['false_green'])}",
                f"  Unknown rate: {_format_rate(metrics['unknown'])}",
                f"  Verify-first rate: {_format_rate(metrics['verify_first'])}",
            ]
        )

    sponsor = report["sponsor_matching"]
    lines.extend(
        [
            "",
            "Sponsor matching",
            "----------------",
            f"Labelled sponsor records: {sponsor['labelled_records']}",
            (
                "Labelled sponsor precision: "
                f"{sponsor['labelled_decision_correct']}/{sponsor['labelled_records']} "
                f"({_format_optional_percent(sponsor['labelled_sponsor_precision'])})"
            ),
            (
                "High-confidence precision: "
                f"{sponsor['high_confidence_correct']}/{sponsor['high_confidence_predictions']} "
                f"({_format_optional_percent(sponsor['high_confidence_precision'])})"
            ),
        ]
    )
    if sponsor["false_positive_examples"]:
        lines.append("High-confidence false positive examples:")
        for example in sponsor["false_positive_examples"]:
            lines.append(
                "  "
                f"{example['eval_id']}: {example['employer_raw']} -> "
                f"{example['predicted']} (expected {example['expected']})"
            )
    if sponsor["failure_case_examples"]:
        lines.append("Sponsor label failure examples:")
        for example in sponsor["failure_case_examples"]:
            lines.append(
                "  "
                f"{example['eval_id']}: {example['employer_raw']} -> "
                f"{example['predicted']} [{example['predicted_band']}] "
                f"(expected is_match={example['expected_is_match']}, "
                f"matched_name={example['expected']})"
            )

    evidence = report["evidence_extraction"]
    lines.extend(
        [
            "",
            "Evidence extraction",
            "-------------------",
            (
                "Accuracy on labelled evidence cases: "
                f"{evidence['matched_cases']}/{evidence['cases_with_expected_evidence']} "
                f"({_format_optional_percent(evidence['accuracy'])})"
            ),
        ]
    )
    if evidence["misses"]:
        lines.append("Evidence misses:")
        for miss in evidence["misses"]:
            lines.append(f"  {miss['case_id']}: expected {miss['expected']}")

    lines.extend(
        [
            "",
            "Definitions",
            "-----------",
            "False red: engine says likely_blocked when the human label is worth_applying or verify_first.",
            "False green: engine says worth_applying when the human label is likely_blocked.",
            "Sponsor precision here counts only high-confidence predicted matches with human sponsor labels.",
            "Labelled sponsor precision counts whether the sponsor-register match/no-match decision matches human labels.",
            "Labels are visa-risk triage signals, not legal or immigration advice.",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run visa engine evaluation metrics.")
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET),
        help="Path to labelled evaluation JSON.",
    )
    parser.add_argument(
        "--sponsor-register",
        default=str(DEFAULT_SPONSOR_REGISTER),
        help="Path to sponsor-register CSV used by the engine.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full metrics report as JSON instead of readable text.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    dataset = load_dataset(Path(args.dataset))
    matcher = SponsorMatcher.from_csv(Path(args.sponsor_register))
    report = evaluate_dataset(dataset, matcher)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
