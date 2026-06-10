"""Build deduplicated sponsor-register artifacts from a raw GOV.UK CSV.

Input: the raw "Worker and Temporary Worker" register downloaded from
https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers
(headers: Organisation Name, Town/City, County, Type & Rating, Route).

The raw export has one row per (organisation, route), so a sponsor licensed on
several routes appears several times. This script deduplicates by organisation
name, merges the routes, and writes two artifacts that the rest of the system
already knows how to read:

  * data/sponsor_register/sponsors.csv
      Deduplicated canonical register (one row per organisation) in the schema
      pipeline/sponsor_register/matcher.py reads. Use it with the pipeline:
        python -m pipeline.build_jobs --sponsor-register data/sponsor_register/sponsors.csv ...

  * frontend/public/sponsors.json
      The same register in the SponsorRegisterFile JSON shape the browser
      paste-checker fetches at /sponsors.json. Regenerated FROM the deduped CSV
      via SponsorRegister.from_csv, so the pipeline and the browser see byte-for
      -byte identical sponsor data (single source of truth).

Deliberately left untouched (small + deterministic, for tests/parity):
  * data/sponsor_register/sample_sponsors.csv
  * frontend/src/engine/__fixtures__/sponsors.json  (parity fixture)

Usage:
    python scripts/build_sponsor_register.py
    python scripts/build_sponsor_register.py --input path/to/register.csv \
        --published-date 2026-06-04
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Ensure the repo root is importable when run as a script from anywhere.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pipeline.sponsor_register.matcher import (  # noqa: E402
    DEFAULT_SOURCE_NAME,
    SponsorRegister,
    _parse_rating,
)

DATA_DIR = REPO_ROOT / "data" / "sponsor_register"
DEFAULT_INPUT = REPO_ROOT / "2026-06-04_-_Worker_and_Temporary_Worker.csv"
DEFAULT_CSV_OUTPUT = DATA_DIR / "sponsors.csv"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "frontend" / "public" / "sponsors.json"

# GOV.UK export header -> our internal key. Matched case-insensitively.
NAME_HEADERS = ("organisation name", "organisation", "name")
ROUTE_HEADERS = ("route", "routes")
RATING_HEADERS = ("type & rating", "type and rating", "rating")
TOWN_HEADERS = ("town/city", "town", "city")
COUNTY_HEADERS = ("county", "region")

_DATE_IN_NAME = re.compile(r"(\d{4})[-_](\d{2})[-_](\d{2})")


class _Org:
    __slots__ = ("name", "routes", "ratings", "location")

    def __init__(self, name: str) -> None:
        self.name = name
        self.routes: List[str] = []
        self.ratings: List[str] = []
        self.location: Optional[str] = None


def _pick(row: Dict[str, str], headers: tuple[str, ...]) -> str:
    for key, value in row.items():
        if key and key.strip().lower() in headers:
            cleaned = (value or "").strip()
            # GOV.UK exports use the literal "NULL" for empty Town/County cells.
            if cleaned.upper() == "NULL":
                return ""
            return cleaned
    return ""


def _published_date_from_name(path: Path) -> Optional[str]:
    match = _DATE_IN_NAME.search(path.name)
    if match:
        return "-".join(match.groups())
    return None


def _best_rating(ratings: List[str]) -> Optional[str]:
    """Parse the GOV.UK "Type & Rating" strings to a single A/B band.

    A rating beats B; an unparseable rating is ignored. Most organisations only
    ever carry one band, so this only matters for the rare multi-route mismatch.
    """

    parsed = {_parse_rating(text) for text in ratings if text}
    parsed.discard(None)
    if "A" in parsed:
        return "A"
    if "B" in parsed:
        return "B"
    # Fall back to whatever non-empty parse exists (e.g. provisional notes).
    for text in ratings:
        rating = _parse_rating(text)
        if rating:
            return rating
    return None


def deduplicate(input_path: Path) -> List[_Org]:
    orgs: Dict[str, _Org] = {}
    with input_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = _pick(row, NAME_HEADERS)
            if not name:
                continue
            org = orgs.get(name)
            if org is None:
                org = _Org(name)
                orgs[name] = org

            route = _pick(row, ROUTE_HEADERS)
            if route and route not in org.routes:
                org.routes.append(route)

            rating = _pick(row, RATING_HEADERS)
            if rating:
                org.ratings.append(rating)

            if org.location is None:
                town = _pick(row, TOWN_HEADERS)
                county = _pick(row, COUNTY_HEADERS)
                parts = [p for p in (town, county) if p]
                org.location = ", ".join(parts) or None

    # Stable, case-insensitive ordering keeps the output diff-friendly.
    return [orgs[name] for name in sorted(orgs, key=str.casefold)]


def write_csv(orgs: List[_Org], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["organisation_name", "sponsor_routes", "rating", "location", "aliases"]
        )
        for org in orgs:
            writer.writerow(
                [
                    org.name,
                    ";".join(org.routes),
                    _best_rating(org.ratings) or "",
                    org.location or "",
                    "",
                ]
            )


def write_json(csv_path: Path, json_path: Path, published_at: Optional[str]) -> int:
    downloaded_at = date.today().isoformat()
    register: SponsorRegister = SponsorRegister.from_csv(
        csv_path,
        source_name=DEFAULT_SOURCE_NAME,
        source_published_at=published_at,
        downloaded_at=downloaded_at,
    )
    payload = {
        "source": register.source.to_dict(),
        "records": [
            {
                "organisation_name": record.organisation_name,
                "sponsor_routes": list(record.sponsor_routes),
                "rating": record.rating,
                "location": record.location,
                "aliases": list(record.aliases),
            }
            for record in register.records
        ],
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    # Compact separators: the full register is large; this keeps it ~3 MB smaller
    # than indent=2 without hurting gzip transfer size.
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return len(register.records)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Raw GOV.UK Worker and Temporary Worker register CSV.",
    )
    parser.add_argument(
        "--published-date",
        default=None,
        help=(
            "Register publication date (YYYY-MM-DD) for provenance. Defaults to "
            "a date parsed from the input filename if present."
        ),
    )
    parser.add_argument(
        "--csv-output",
        default=str(DEFAULT_CSV_OUTPUT),
        help="Deduplicated canonical register CSV path.",
    )
    parser.add_argument(
        "--json-output",
        default=str(DEFAULT_JSON_OUTPUT),
        help="Frontend sponsors.json path (SponsorRegisterFile shape).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input register not found: {input_path}")

    published_at = args.published_date or _published_date_from_name(input_path)

    orgs = deduplicate(input_path)
    csv_path = Path(args.csv_output)
    json_path = Path(args.json_output)
    write_csv(orgs, csv_path)
    record_count = write_json(csv_path, json_path, published_at)

    multi_route = sum(1 for org in orgs if len(org.routes) > 1)
    print(
        f"Deduplicated {len(orgs)} organisation(s) "
        f"({multi_route} on multiple routes).\n"
        f"  CSV : {csv_path}\n"
        f"  JSON: {json_path} ({record_count} records, "
        f"published {published_at or 'unknown'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
