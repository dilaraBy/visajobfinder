"""Build the static public jobs file for the dashboard."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pipeline.classifier.engine import build_job_record
from pipeline.classifier.phrase_scanner import scan_description
from pipeline.sources.dedupe import dedupe_jobs
from pipeline.sources import AdzunaAdapter, GreenhouseAdapter, LeverAdapter, ReedAdapter
from pipeline.sources.env_file import load_env_file
from pipeline.sources.freshness import (
    DEFAULT_STALE_AFTER_DAYS,
    compute_age_days,
    freshness_for,
    summarise_freshness,
)
from pipeline.sources.link_check import LinkChecker, check_url, summarise_links
from pipeline.sources.models import SourceAdapter, SourceNormalisationError, SourceRun
from pipeline.sources.normalise import normalise_raw_job
from pipeline.sponsor_register.matcher import SponsorMatcher


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_FILE = ROOT / "data" / "sources" / "sample_jobs.json"
DEFAULT_SPONSOR_REGISTER = ROOT / "data" / "sponsor_register" / "sample_sponsors.csv"
DEFAULT_OUTPUT = ROOT / "data" / "public" / "jobs.json"
DEFAULT_ENV_FILE = ROOT / ".env"
# Single-page result caps the upstream APIs accept; keeps live runs polite.
RESULTS_CAP = {"reed": 100, "adzuna": 50}
ADAPTERS = {
    "reed": ReedAdapter,
    "adzuna": AdzunaAdapter,
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
}
# Sources whose live search keyword can be set per run.
SEARCH_TERM_SOURCES = {"reed", "adzuna"}
# Curated UK graduate-relevant fields fetched daily when --search-term is not
# given. Ordered specific -> generic so a field-specific category wins the
# first-wins dedupe (the generic "graduate" sweep is last).
DEFAULT_SEARCH_TERMS = [
    "psychology graduate",
    "economics graduate",
    "finance graduate",
    "data analyst graduate",
    "marketing graduate",
    "engineering graduate",
    "software developer graduate",
    "business analyst graduate",
    "human resources graduate",
    "graduate",
]
# Per (term x source) request size and the overall cap on jobs written, so a
# many-term run stays polite upstream and keeps jobs.json a reasonable static
# asset (~3 KB/job).
DEFAULT_PER_TERM_RESULTS = 20
DEFAULT_MAX_JOBS = 400
# Drop listings whose posted date is older than this; sources sometimes return
# stale ads (months/years old) that aren't worth showing. Undated jobs are kept
# (their age can't be judged) and stay flagged as needs_review.
DEFAULT_MAX_AGE_DAYS = 120


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_raw_jobs(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        records = data.get("jobs") or data.get("records")
    else:
        records = data
    if not isinstance(records, list):
        raise ValueError(f"{path} must contain a JSON list or an object with jobs/records.")
    return records


def _source_name(path: Path, raw_jobs: List[Dict[str, Any]]) -> str:
    sources = {
        str(record.get("source", "")).strip()
        for record in raw_jobs
        if str(record.get("source", "")).strip()
    }
    if len(sources) == 1:
        return next(iter(sources))
    if len(sources) > 1:
        return "mixed"
    return path.stem


def normalise_source_file(path: Path, fetched_at: str) -> Tuple[List[Any], SourceRun]:
    try:
        raw_jobs = load_raw_jobs(path)
    except Exception as exc:
        return [], SourceRun(
            source=path.stem,
            status="error",
            fetched_count=0,
            normalised_count=0,
            error=str(exc),
        )

    jobs = []
    errors = []
    for raw in raw_jobs:
        try:
            jobs.append(normalise_raw_job(raw, fetched_at=fetched_at))
        except SourceNormalisationError as exc:
            errors.append(str(exc))

    status = "ok" if not errors else "partial"
    error = None
    if errors:
        preview = "; ".join(errors[:3])
        suffix = "" if len(errors) <= 3 else f"; {len(errors) - 3} more"
        error = f"Skipped {len(errors)} invalid record(s): {preview}{suffix}"

    return jobs, SourceRun(
        source=_source_name(path, raw_jobs),
        status=status,
        fetched_count=len(raw_jobs),
        normalised_count=len(jobs),
        error=error,
    )


def adapter_from_spec(
    spec: str,
    results: Optional[int] = None,
    search_term: Optional[str] = None,
) -> SourceAdapter:
    """Create a source adapter from a compact CLI spec.

    Supported forms:
    - ``reed`` uses the default fixture mode.
    - ``reed:live`` asks the adapter to use live mode.
    - ``greenhouse:fixture:path/to/file.json`` uses a specific fixture.

    ``results`` sets how many listings to request from APIs that support it
    (Reed, Adzuna), capped to a polite per-source maximum. ``search_term`` sets
    the keyword those same sources search for (ignored by sources that do not
    support a search term).
    """

    parts = spec.split(":", 2)
    source = parts[0].strip().lower()
    if source not in ADAPTERS:
        raise ValueError(f"Unsupported source adapter '{source}'. Expected one of: {', '.join(sorted(ADAPTERS))}.")

    mode = parts[1].strip().lower() if len(parts) >= 2 and parts[1].strip() else "fixture"
    fixture_path = Path(parts[2]) if len(parts) == 3 and parts[2].strip() else None
    adapter_cls = ADAPTERS[source]
    kwargs: Dict[str, Any] = {"mode": mode}
    if fixture_path is not None:
        kwargs["fixture_path"] = fixture_path
    if results is not None and source in RESULTS_CAP:
        capped = max(1, min(results, RESULTS_CAP[source]))
        if source == "reed":
            kwargs["results_to_take"] = capped
        elif source == "adzuna":
            kwargs["results_per_page"] = capped
    if search_term is not None and source in SEARCH_TERM_SOURCES:
        if source == "reed":
            kwargs["keywords"] = search_term
        elif source == "adzuna":
            kwargs["what"] = search_term
    return adapter_cls(**kwargs)


def fetch_adapters(
    adapters: Iterable[SourceAdapter],
    fetched_at: str,
) -> Tuple[List[Any], List[Dict[str, Any]]]:
    jobs = []
    source_runs = []
    for adapter in adapters:
        adapter_jobs, source_run = adapter.fetch_jobs(fetched_at)
        jobs.extend(adapter_jobs)
        run_dict = source_run.to_dict()
        # Surface which search term this run fetched so multi-term failures are
        # legible in source_runs. Adapters don't know their own term, so read it
        # off the adapter (reed: keywords, adzuna: what).
        term = getattr(adapter, "keywords", None) or getattr(adapter, "what", None)
        if term and run_dict.get("search_term") is None:
            run_dict["search_term"] = term
        source_runs.append(run_dict)
    return jobs, source_runs


def _within_max_age(posted_at: Any, generated_at: str, max_age_days: int) -> bool:
    """True if a listing is recent enough to keep. Undated jobs are kept."""
    age = compute_age_days(posted_at, generated_at)
    if age is None:
        return True
    return age <= max_age_days


def enrich_jobs(
    jobs: Iterable[Any],
    matcher: SponsorMatcher,
    generated_at: str,
    stale_after_days: int = DEFAULT_STALE_AFTER_DAYS,
    link_checker: Optional[LinkChecker] = None,
) -> List[Dict[str, Any]]:
    output = []
    for job in jobs:
        employer_match = matcher.match(job.employer_raw)
        phrase_signals = scan_description(job.description_text)
        description_scope = "excerpt" if job.description_text else "missing"
        record = build_job_record(
            job,
            employer_match,
            phrase_signals,
            description_scope=description_scope,
        )
        record["freshness"] = freshness_for(
            job.posted_at, generated_at, stale_after_days=stale_after_days
        )
        if link_checker is not None:
            record["link_status"] = link_checker(job.url)
        output.append(record)
    return output


def build_public_jobs(
    source_files: Iterable[Path],
    sponsor_register_path: Path,
    generated_at: Optional[str] = None,
    adapters: Optional[Iterable[SourceAdapter]] = None,
    stale_after_days: int = DEFAULT_STALE_AFTER_DAYS,
    link_checker: Optional[LinkChecker] = None,
    max_jobs: Optional[int] = None,
    max_age_days: Optional[int] = None,
) -> Dict[str, Any]:
    timestamp = generated_at or utc_now()
    matcher = SponsorMatcher.from_csv(sponsor_register_path)

    all_jobs = []
    source_runs = []
    if adapters:
        adapter_jobs, adapter_source_runs = fetch_adapters(adapters, timestamp)
        all_jobs.extend(adapter_jobs)
        source_runs.extend(adapter_source_runs)

    for source_file in source_files:
        jobs, source_run = normalise_source_file(source_file, fetched_at=timestamp)
        all_jobs.extend(jobs)
        source_runs.append(source_run.to_dict())

    deduped_jobs = dedupe_jobs(all_jobs)
    if max_age_days is not None:
        # Drop listings older than the cutoff (keep undated ones — their age is
        # unknown and they're flagged separately as needs_review).
        deduped_jobs = [
            job
            for job in deduped_jobs
            if _within_max_age(job.posted_at, timestamp, max_age_days)
        ]
    if max_jobs is not None:
        # Cap after dedupe (and before the --min-jobs guard counts them) so a
        # many-term run keeps jobs.json a reasonable size.
        deduped_jobs = deduped_jobs[:max_jobs]
    job_records = enrich_jobs(
        deduped_jobs,
        matcher,
        generated_at=timestamp,
        stale_after_days=stale_after_days,
        link_checker=link_checker,
    )
    output = {
        "generated_at": timestamp,
        "source_runs": source_runs,
        "freshness_summary": summarise_freshness(job_records),
        "jobs": job_records,
    }
    if link_checker is not None:
        output["link_summary"] = summarise_links(job_records)
    return output


def write_public_jobs(output: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build static data/public/jobs.json.")
    parser.add_argument(
        "--source-file",
        action="append",
        default=None,
        help="Raw source JSON file. Can be supplied multiple times. Omitted when --source-adapter is used.",
    )
    parser.add_argument(
        "--source-adapter",
        action="append",
        default=None,
        help=(
            "Source adapter spec such as reed, adzuna:live, greenhouse:fixture:.\\data\\sources\\greenhouse_fixture.json. "
            "Can be supplied multiple times."
        ),
    )
    parser.add_argument(
        "--sponsor-register",
        default=str(DEFAULT_SPONSOR_REGISTER),
        help="Sponsor-register CSV used for employer matching.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output path for the public jobs JSON file.",
    )
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_ENV_FILE),
        help=(
            "Path to a .env file holding API credentials for live adapters "
            "(REED_API_KEY, ADZUNA_APP_ID, ADZUNA_APP_KEY). Loaded if present; "
            "real environment variables always take precedence."
        ),
    )
    parser.add_argument(
        "--results",
        type=int,
        default=None,
        help=(
            "How many listings to request per (search term x source) from APIs "
            "that support it (Reed, Adzuna). Defaults to "
            f"{DEFAULT_PER_TERM_RESULTS}."
        ),
    )
    parser.add_argument(
        "--search-term",
        action="append",
        default=None,
        help=(
            "Field/keyword to fetch from live Reed/Adzuna (repeatable). Each term "
            "is fetched separately and tagged onto its jobs as `category`. "
            "Defaults to a curated UK graduate-field list when omitted."
        ),
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=DEFAULT_MAX_JOBS,
        help="Cap on total jobs written after dedupe across all search terms.",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=DEFAULT_MAX_AGE_DAYS,
        help=(
            "Drop listings whose posted date is older than this many days "
            f"(default {DEFAULT_MAX_AGE_DAYS}). Undated listings are kept. "
            "Pass a large number to disable."
        ),
    )
    parser.add_argument(
        "--min-jobs",
        type=int,
        default=0,
        help=(
            "Fail (exit 1) without writing output if fewer than this many jobs "
            "were built. Lets scheduled refreshes keep the last good snapshot "
            "instead of publishing an empty dataset when every source fails."
        ),
    )
    parser.add_argument(
        "--stale-after-days",
        type=int,
        default=DEFAULT_STALE_AFTER_DAYS,
        help="A listing older than this many days is flagged as stale.",
    )
    parser.add_argument(
        "--check-links",
        action="store_true",
        help="Check each job URL and record link status (makes one request per job).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    # Load local credentials before constructing live adapters; existing env wins.
    load_env_file(Path(args.env_file))
    source_files = [Path(path) for path in (args.source_file or [])]
    search_terms = args.search_term or list(DEFAULT_SEARCH_TERMS)
    per_term_results = args.results if args.results is not None else DEFAULT_PER_TERM_RESULTS
    # Fan out (search term x spec) for term-aware sources; other sources stay a
    # single instance so we don't reload the same fixture once per term.
    adapters = []
    for spec in (args.source_adapter or []):
        source = spec.split(":", 2)[0].strip().lower()
        if source in SEARCH_TERM_SOURCES:
            for term in search_terms:
                adapters.append(
                    adapter_from_spec(spec, results=per_term_results, search_term=term)
                )
        else:
            adapters.append(adapter_from_spec(spec, results=per_term_results))
    if not source_files and not adapters:
        source_files = [DEFAULT_SOURCE_FILE]
    output = build_public_jobs(
        source_files=source_files,
        sponsor_register_path=Path(args.sponsor_register),
        adapters=adapters,
        stale_after_days=args.stale_after_days,
        link_checker=check_url if args.check_links else None,
        max_jobs=args.max_jobs,
        max_age_days=args.max_age_days,
    )
    if len(output["jobs"]) < args.min_jobs:
        print(
            f"Refusing to write {args.output}: built {len(output['jobs'])} job(s), "
            f"below --min-jobs {args.min_jobs}. Source runs:"
        )
        for run in output["source_runs"]:
            detail = run.get("error") or "ok"
            print(f"  - {run['source']}: {run['status']} ({detail})")
        return 1
    write_public_jobs(output, Path(args.output))
    freshness = output["freshness_summary"]
    link_note = ""
    if "link_summary" in output:
        link_note = f", {output['link_summary']['dead']} dead link(s)"
    print(
        f"Wrote {len(output['jobs'])} deduplicated job(s) to {args.output} "
        f"from {len(output['source_runs'])} source run(s). "
        f"Freshness: {freshness['fresh']} fresh, {freshness['stale']} stale, "
        f"{freshness['missing_date']} undated{link_note}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
