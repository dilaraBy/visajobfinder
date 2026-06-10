"""Fixture-first job source adapters."""

from __future__ import annotations

import base64
import html
import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from pipeline.classifier.models import JobInput
from pipeline.sources.models import SourceNormalisationError, SourceRun
from pipeline.sources.normalise import normalise_raw_job


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_DIR = ROOT / "data" / "sources"
EXCERPT_CHARS = 700
HTML_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _plain_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = HTML_TAG_RE.sub(" ", text)
    return _clean_text(text)


def _excerpt(value: Any, max_chars: int = EXCERPT_CHARS) -> str:
    text = _plain_text(value)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(".,;:") + "..."


def _first_text(*values: Any) -> str:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return ""


ISO_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
UK_DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}")


def _iso_date(value: Any) -> Optional[str]:
    """Normalise a source date to YYYY-MM-DD, or None when unparseable.

    The live Reed API returns day-first DD/MM/YYYY dates; other sources use
    ISO timestamps. Anything else becomes None so downstream freshness reports
    "date unknown" honestly instead of carrying unparseable text through.
    """
    text = _clean_text(value)
    if not text:
        return None
    iso = ISO_DATE_RE.match(text)
    if iso:
        try:
            date.fromisoformat(iso.group(1))
        except ValueError:
            return None
        return iso.group(1)
    if UK_DATE_RE.match(text):
        try:
            return datetime.strptime(text[:10], "%d/%m/%Y").date().isoformat()
        except ValueError:
            return None
    return None


def _date_from_epoch_ms(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        timestamp = int(value) / 1000
    except (TypeError, ValueError):
        return _iso_date(value)
    return datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()


def _salary_text(minimum: Any, maximum: Any, fallback: Any = None) -> Optional[str]:
    text = _clean_text(fallback)
    if text:
        return text
    if minimum in (None, "") and maximum in (None, ""):
        return None
    if minimum not in (None, "") and maximum not in (None, ""):
        return f"GBP {minimum} - {maximum} per year"
    if minimum not in (None, ""):
        return f"GBP {minimum}+ per year"
    return f"Up to GBP {maximum} per year"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _records_from_payload(payload: Any, keys: Iterable[str]) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = None
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                records = value
                break
        if records is None:
            raise ValueError(f"Fixture payload must contain one of: {', '.join(keys)}.")
    else:
        raise ValueError("Fixture payload must be a JSON object or list.")

    if not all(isinstance(record, dict) for record in records):
        raise ValueError("Fixture records must be JSON objects.")
    return records


def _normalise_records(
    source: str,
    raw_records: List[Dict[str, Any]],
    fetched_at: str,
) -> Tuple[List[JobInput], SourceRun]:
    jobs: List[JobInput] = []
    errors: List[str] = []
    for raw in raw_records:
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
        source=source,
        status=status,
        fetched_count=len(raw_records),
        normalised_count=len(jobs),
        error=error,
    )


def _source_error(source: str, message: str) -> Tuple[List[JobInput], SourceRun]:
    return [], SourceRun(
        source=source,
        status="error",
        fetched_count=0,
        normalised_count=0,
        error=message,
    )


def _missing_env_error(source: str, env_names: Iterable[str]) -> Tuple[List[JobInput], SourceRun]:
    names = ", ".join(env_names)
    return _source_error(
        source,
        (
            f"Missing required environment variable(s) for live {source} fetch: {names}. "
            "Set credentials for live mode or run the adapter in fixture mode."
        ),
    )


def _fetch_json(url: str, headers: Optional[Mapping[str, str]] = None) -> Any:
    request = urllib.request.Request(url, headers=dict(headers or {}))
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


@dataclass(frozen=True)
class ReedAdapter:
    source: str = "reed"
    mode: str = "fixture"
    fixture_path: Path = DEFAULT_FIXTURE_DIR / "reed_fixture.json"
    env: Mapping[str, str] = field(default_factory=lambda: os.environ)
    keywords: str = "graduate"
    location_name: str = "United Kingdom"
    results_to_take: int = 25

    def fetch_jobs(self, fetched_at: str) -> Tuple[List[JobInput], SourceRun]:
        if self.mode == "fixture":
            return self._fetch_fixture(fetched_at)
        if self.mode == "live":
            return self._fetch_live(fetched_at)
        return _source_error(self.source, f"Unsupported adapter mode '{self.mode}'.")

    def _fetch_fixture(self, fetched_at: str) -> Tuple[List[JobInput], SourceRun]:
        try:
            payload = _load_json(self.fixture_path)
            records = _records_from_payload(payload, ("results", "jobs", "records"))
            return _normalise_records(self.source, [self._map_record(record) for record in records], fetched_at)
        except Exception as exc:
            return _source_error(self.source, f"Failed to load Reed fixture {self.fixture_path}: {exc}")

    def _fetch_live(self, fetched_at: str) -> Tuple[List[JobInput], SourceRun]:
        api_key = _clean_text(self.env.get("REED_API_KEY"))
        if not api_key:
            return _missing_env_error(self.source, ("REED_API_KEY",))

        query = urllib.parse.urlencode(
            {
                "keywords": self.keywords,
                "locationName": self.location_name,
                "resultsToTake": self.results_to_take,
            }
        )
        token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
        try:
            payload = _fetch_json(
                f"https://www.reed.co.uk/api/1.0/search?{query}",
                headers={"Authorization": f"Basic {token}"},
            )
            records = _records_from_payload(payload, ("results",))
            return _normalise_records(self.source, [self._map_record(record) for record in records], fetched_at)
        except Exception as exc:
            return _source_error(self.source, f"Live Reed fetch failed: {exc}")

    def _map_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        minimum = record.get("minimumSalary") or record.get("salary_min")
        maximum = record.get("maximumSalary") or record.get("salary_max")
        return {
            "source": self.source,
            "source_job_id": _first_text(record.get("jobId"), record.get("id")),
            "title": _first_text(record.get("jobTitle"), record.get("title")),
            "employer_raw": _first_text(record.get("employerName"), record.get("employer")),
            "description_text": _excerpt(
                _first_text(record.get("descriptionSnippet"), record.get("jobDescription"), record.get("description"))
            ),
            "location": _first_text(record.get("locationName"), record.get("location")),
            "salary_text": _salary_text(minimum, maximum, record.get("salary")),
            "salary_min": minimum,
            "salary_max": maximum,
            "posted_at": _iso_date(record.get("date") or record.get("datePosted") or record.get("posted_at")),
            "closing_at": _iso_date(record.get("expirationDate") or record.get("closing_at")),
            "url": _first_text(record.get("jobUrl"), record.get("externalUrl"), record.get("url")),
            "category": self.keywords,
        }


@dataclass(frozen=True)
class AdzunaAdapter:
    source: str = "adzuna"
    mode: str = "fixture"
    fixture_path: Path = DEFAULT_FIXTURE_DIR / "adzuna_fixture.json"
    env: Mapping[str, str] = field(default_factory=lambda: os.environ)
    country: str = "gb"
    what: str = "graduate"
    # Country-wide search comes from the /jobs/{country}/ URL path. A `where`
    # of "United Kingdom" fails Adzuna's geocoding and silently returns zero
    # results, so only pass `where` for a real place name (city/region).
    where: str = ""
    results_per_page: int = 25

    def fetch_jobs(self, fetched_at: str) -> Tuple[List[JobInput], SourceRun]:
        if self.mode == "fixture":
            return self._fetch_fixture(fetched_at)
        if self.mode == "live":
            return self._fetch_live(fetched_at)
        return _source_error(self.source, f"Unsupported adapter mode '{self.mode}'.")

    def _fetch_fixture(self, fetched_at: str) -> Tuple[List[JobInput], SourceRun]:
        try:
            payload = _load_json(self.fixture_path)
            records = _records_from_payload(payload, ("results", "jobs", "records"))
            return _normalise_records(self.source, [self._map_record(record) for record in records], fetched_at)
        except Exception as exc:
            return _source_error(self.source, f"Failed to load Adzuna fixture {self.fixture_path}: {exc}")

    def _fetch_live(self, fetched_at: str) -> Tuple[List[JobInput], SourceRun]:
        app_id = _clean_text(self.env.get("ADZUNA_APP_ID"))
        app_key = _clean_text(self.env.get("ADZUNA_APP_KEY"))
        missing = [name for name, value in (("ADZUNA_APP_ID", app_id), ("ADZUNA_APP_KEY", app_key)) if not value]
        if missing:
            return _missing_env_error(self.source, missing)

        params = {
            "app_id": app_id,
            "app_key": app_key,
            "what": self.what,
            "results_per_page": self.results_per_page,
        }
        if _clean_text(self.where):
            params["where"] = _clean_text(self.where)
        query = urllib.parse.urlencode(params)
        try:
            payload = _fetch_json(f"https://api.adzuna.com/v1/api/jobs/{self.country}/search/1?{query}")
            records = _records_from_payload(payload, ("results",))
            return _normalise_records(self.source, [self._map_record(record) for record in records], fetched_at)
        except Exception as exc:
            return _source_error(self.source, f"Live Adzuna fetch failed: {exc}")

    def _map_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        company = record.get("company") if isinstance(record.get("company"), dict) else {}
        location = record.get("location") if isinstance(record.get("location"), dict) else {}
        area = location.get("area")
        location_text = location.get("display_name") or (", ".join(area) if isinstance(area, list) else area)
        minimum = record.get("salary_min")
        maximum = record.get("salary_max")
        return {
            "source": self.source,
            "source_job_id": _first_text(record.get("id")),
            "title": _first_text(record.get("title")),
            "employer_raw": _first_text(company.get("display_name"), record.get("employer")),
            "description_text": _excerpt(record.get("description")),
            "location": location_text,
            "salary_text": _salary_text(minimum, maximum, record.get("salary_text")),
            "salary_min": minimum,
            "salary_max": maximum,
            "posted_at": _iso_date(record.get("created")),
            "closing_at": _iso_date(record.get("closing_at")),
            "url": _first_text(record.get("redirect_url"), record.get("adref"), record.get("url")),
            "category": self.what,
        }


@dataclass(frozen=True)
class GreenhouseAdapter:
    source: str = "greenhouse"
    mode: str = "fixture"
    fixture_path: Path = DEFAULT_FIXTURE_DIR / "greenhouse_fixture.json"
    employer_name: str = "Unknown Greenhouse Employer"

    def fetch_jobs(self, fetched_at: str) -> Tuple[List[JobInput], SourceRun]:
        if self.mode != "fixture":
            return _source_error(self.source, "Greenhouse adapter currently supports fixture mode only.")
        try:
            payload = _load_json(self.fixture_path)
            records = _records_from_payload(payload, ("jobs", "records"))
            return _normalise_records(self.source, [self._map_record(record) for record in records], fetched_at)
        except Exception as exc:
            return _source_error(self.source, f"Failed to load Greenhouse fixture {self.fixture_path}: {exc}")

    def _map_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        location = record.get("location") if isinstance(record.get("location"), dict) else {}
        return {
            "source": self.source,
            "source_job_id": _first_text(record.get("id")),
            "title": _first_text(record.get("title")),
            "employer_raw": _first_text(record.get("company_name"), self.employer_name),
            "description_text": _excerpt(_first_text(record.get("content"), record.get("description"))),
            "location": _first_text(location.get("name"), record.get("location")),
            "salary_text": _first_text(record.get("salary_text")) or None,
            "posted_at": _iso_date(record.get("updated_at") or record.get("created_at")),
            "closing_at": _iso_date(record.get("closing_at")),
            "url": _first_text(record.get("absolute_url"), record.get("url")),
        }


@dataclass(frozen=True)
class LeverAdapter:
    source: str = "lever"
    mode: str = "fixture"
    fixture_path: Path = DEFAULT_FIXTURE_DIR / "lever_fixture.json"
    employer_name: str = "Unknown Lever Employer"

    def fetch_jobs(self, fetched_at: str) -> Tuple[List[JobInput], SourceRun]:
        if self.mode != "fixture":
            return _source_error(self.source, "Lever adapter currently supports fixture mode only.")
        try:
            payload = _load_json(self.fixture_path)
            records = _records_from_payload(payload, ("postings", "jobs", "records"))
            return _normalise_records(self.source, [self._map_record(record) for record in records], fetched_at)
        except Exception as exc:
            return _source_error(self.source, f"Failed to load Lever fixture {self.fixture_path}: {exc}")

    def _map_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        categories = record.get("categories") if isinstance(record.get("categories"), dict) else {}
        description = " ".join(
            part
            for part in (
                _plain_text(record.get("descriptionPlain") or record.get("description")),
                _plain_text(record.get("additionalPlain") or record.get("additional")),
            )
            if part
        )
        return {
            "source": self.source,
            "source_job_id": _first_text(record.get("id")),
            "title": _first_text(record.get("text"), record.get("title")),
            "employer_raw": _first_text(record.get("company_name"), self.employer_name),
            "description_text": _excerpt(description),
            "location": _first_text(categories.get("location"), record.get("location")),
            "salary_text": _first_text(record.get("salaryDescription"), record.get("salary_text")) or None,
            "posted_at": _date_from_epoch_ms(record.get("createdAt") or record.get("created_at")),
            "closing_at": _iso_date(record.get("closing_at")),
            "url": _first_text(record.get("hostedUrl"), record.get("applyUrl"), record.get("url")),
        }
