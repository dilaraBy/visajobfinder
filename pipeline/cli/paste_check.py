"""CLI paste checker for Phase 1 visa-risk triage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from pipeline.classifier.engine import analyse_job
from pipeline.classifier.models import JobInput, UserContext
from pipeline.sponsor_register.matcher import SponsorMatcher


DEFAULT_SPONSOR_REGISTER = (
    Path(__file__).resolve().parents[2] / "data" / "sponsor_register" / "sample_sponsors.csv"
)


def _read_description(args: argparse.Namespace) -> str:
    if args.description:
        return args.description
    if args.description_file:
        return Path(args.description_file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Provide --description, --description-file, or pipe a description on stdin.")


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"Expected a whole number, got: {value}") from exc


def _format_match(match: Dict[str, Any]) -> str:
    if match.get("is_match"):
        confidence = match.get("confidence", 0)
        return (
            f"{match.get('matched_name')} "
            f"({match.get('confidence_band')} confidence, {confidence:.3g})"
        )
    if match.get("matched_name"):
        confidence = match.get("confidence", 0)
        return (
            f"No reliable match; closest candidate is {match.get('matched_name')} "
            f"({match.get('confidence_band')} confidence, {confidence:.3g})"
        )
    return "No reliable sponsor-register match in the loaded data."


def _format_bullets(values: list[Any], empty: str) -> list[str]:
    if not values:
        return [f"- {empty}"]
    return [f"- {value}" for value in values]


def build_summary(output: Dict[str, Any]) -> str:
    """Create a human-readable summary from the engine output contract."""

    job = output["job"]
    classification = output["classification"]
    evidence_lines = []
    for item in classification["evidence"]:
        category = item.get("category", "evidence")
        text = item.get("text", "")
        evidence_type = item.get("type", "evidence")
        evidence_lines.append(f"{evidence_type}/{category}: {text}")

    lines = [
        "Summary",
        f"Job: {job.get('title') or '(missing title)'} at {job.get('employer_raw') or '(missing employer)'}",
        f"Label: {classification['label']}",
        f"Reason: {classification['reason']}",
        f"Employer match: {_format_match(classification['employer_match'])}",
        "Evidence:",
        *(_format_bullets(evidence_lines, "No evidence returned by the engine.")),
        "What to verify:",
        *(_format_bullets(classification["what_to_verify"], "No verification prompts returned.")),
        "Limitations:",
        *(_format_bullets(classification["limitations"], "No limitations returned.")),
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify a pasted job description with conservative visa-risk labels."
    )
    parser.add_argument("--title", required=True, help="Job title.")
    parser.add_argument("--employer", required=True, help="Employer name from the job ad.")
    parser.add_argument("--description", help="Job description text. Can also be piped on stdin.")
    parser.add_argument("--description-file", help="Path to a text file containing the job description.")
    parser.add_argument("--location", help="Optional job location.")
    parser.add_argument("--salary", dest="salary_text", help="Optional salary text.")
    parser.add_argument("--salary-min", help="Optional numeric minimum salary.")
    parser.add_argument("--salary-max", help="Optional numeric maximum salary.")
    parser.add_argument("--url", help="Optional source URL.")
    parser.add_argument(
        "--visa-situation",
        required=True,
        choices=["graduate_route", "needs_sponsorship_before_start", "unknown"],
        help="Selected user visa situation.",
    )
    parser.add_argument("--visa-expiry-month", help="Optional expiry month, e.g. 2027-09.")
    parser.add_argument("--target-start-month", help="Optional target start month, e.g. 2026-09.")
    parser.add_argument(
        "--needs-sponsorship-before-start",
        action="store_true",
        help="Set when the user needs sponsorship before starting the role.",
    )
    parser.add_argument(
        "--needs-future-sponsorship",
        action="store_true",
        help="Set when the user may need sponsorship after current permission ends.",
    )
    parser.add_argument(
        "--sponsor-register",
        default=str(DEFAULT_SPONSOR_REGISTER),
        help="CSV sponsor-register fixture or parsed GOV.UK register.",
    )
    parser.add_argument(
        "--output",
        choices=["both", "json", "summary"],
        default="both",
        help="Output readable JSON, a human summary, or both.",
    )
    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    sponsor_path = Path(args.sponsor_register)
    if not sponsor_path.exists():
        raise SystemExit(f"Sponsor-register file not found: {sponsor_path}")

    needs_before_start = (
        args.needs_sponsorship_before_start
        or args.visa_situation == "needs_sponsorship_before_start"
    )
    job = JobInput(
        title=args.title,
        employer_raw=args.employer,
        description_text=_read_description(args),
        location=args.location,
        salary_text=args.salary_text,
        salary_min=_parse_int(args.salary_min),
        salary_max=_parse_int(args.salary_max),
        url=args.url,
    )
    user = UserContext(
        visa_situation=args.visa_situation,
        visa_expiry_month=args.visa_expiry_month,
        needs_sponsorship_before_start=needs_before_start,
        needs_future_sponsorship=args.needs_future_sponsorship,
        target_start_month=args.target_start_month,
    )
    matcher = SponsorMatcher.from_csv(sponsor_path)
    output = analyse_job(job=job, user=user, matcher=matcher)
    if args.output in {"both", "json"}:
        json.dump(output, sys.stdout, indent=2)
        sys.stdout.write("\n")
    if args.output == "both":
        sys.stdout.write("\n")
    if args.output in {"both", "summary"}:
        sys.stdout.write(build_summary(output))
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
