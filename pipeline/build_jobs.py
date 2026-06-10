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


def adapter_from_spec(spec: str, results: Optional[int] = None) -> SourceAdapter:
    """Create a source adapter from a compact CLI spec.

    Supported forms:
    - ``reed`` uses the default fixture mode.
    - ``reed:live`` asks the adapter to use live mode.
    - ``greenhouse:fixture:path/to/file.json`` uses a specific fixture.

    ``results`` sets how many listings to request from APIs that support it
    (Reed, Adzuna), capped to a polite per-source maximum.
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
        source_runs.append(source_run.to_dict())
    return jobs, source_runs


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
        help="How many listings to request from APIs that support it (Reed, Adzuna).",
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
    adapters = [
        adapter_from_spec(spec, results=args.results)
        for spec in (args.source_adapter or [])
    ]
    if not source_files and not adapters:
        source_files = [DEFAULT_SOURCE_FILE]
    output = build_public_jobs(
        source_files=source_files,
        sponsor_register_path=Path(args.sponsor_register),
        adapters=adapters,
        stale_after_days=args.stale_after_days,
        link_checker=check_url if args.check_links else None,
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
