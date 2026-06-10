"""Transparent sponsor-register matching interface for Phase 1."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Mapping, Optional, Tuple

from pipeline.classifier.models import EmployerMatch
from pipeline.sponsor_register.normalise import normalise_employer_name


HIGH_CONFIDENCE = 0.92
MEDIUM_CONFIDENCE = 0.82
LOW_CANDIDATE = 0.60
DEFAULT_SOURCE_NAME = "GOV.UK Register of Licensed Sponsors"

# Generic sector/structure words that, when they are the *only* thing two names
# share, are not enough to assert a reliable sponsor match. A fuzzy match in the
# [MEDIUM, HIGH) band must rest on at least one shared DISTINCTIVE token;
# otherwise it is a character coincidence between different companies (e.g.
# "Bechtle" vs "Bechtel", "Academics" vs "Academicians", or two unrelated
# "... Education" firms) and is demoted to a low-confidence, verify-first
# candidate. Legal suffixes (ltd, plc, ...) are already removed by the
# normaliser, so they are not repeated here.
GENERIC_MATCH_TOKENS = frozenset(
    {
        "and",
        "the",
        "group",
        "holdings",
        "holding",
        "international",
        "global",
        "uk",
        "services",
        "service",
        "solutions",
        "solution",
        "consulting",
        "consultancy",
        "consultants",
        "recruitment",
        "staffing",
        "education",
        "care",
        "training",
        "management",
        "technologies",
        "technology",
        "systems",
        "partners",
        "associates",
        "agency",
        "trading",
        "enterprises",
        "enterprise",
        "ventures",
        "capital",
    }
)


def _shares_distinctive_token(query_norm: str, candidate_norm: str) -> bool:
    """True if the two normalised names share at least one non-generic token."""

    shared = set(query_norm.split()) & set(candidate_norm.split())
    return bool(shared - GENERIC_MATCH_TOKENS)


@dataclass(frozen=True)
class SponsorRecord:
    organisation_name: str
    sponsor_routes: List[str] = field(default_factory=list)
    rating: Optional[str] = None
    location: Optional[str] = None
    aliases: List[str] = field(default_factory=list)

    @property
    def searchable_names(self) -> List[Tuple[str, str]]:
        names = [(self.organisation_name, "organisation_name")]
        names.extend((alias, "alias") for alias in self.aliases)
        return names


@dataclass(frozen=True)
class SponsorRegisterSource:
    source_name: str = DEFAULT_SOURCE_NAME
    source_published_at: Optional[str] = None
    downloaded_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "source_name": self.source_name,
            "source_published_at": self.source_published_at,
            "downloaded_at": self.downloaded_at,
        }


@dataclass(frozen=True)
class SponsorRegister:
    records: List[SponsorRecord]
    source: SponsorRegisterSource = field(default_factory=SponsorRegisterSource)

    @classmethod
    def from_csv(
        cls,
        path: Path,
        source_name: str = DEFAULT_SOURCE_NAME,
        source_published_at: Optional[str] = None,
        downloaded_at: Optional[str] = None,
    ) -> "SponsorRegister":
        """Parse a GOV.UK-style sponsor-register CSV snapshot.

        The parser accepts the local fixture headers as well as common GOV.UK
        export headers such as "Organisation Name", "Route", "Type & Rating",
        "Town/City", and "County". Source metadata is explicit so downstream
        evidence can distinguish register freshness from match confidence.
        """

        with path.open(newline="", encoding="utf-8-sig") as handle:
            return cls.from_rows(
                csv.DictReader(handle),
                source_name=source_name,
                source_published_at=source_published_at,
                downloaded_at=downloaded_at,
            )

    @classmethod
    def from_rows(
        cls,
        rows: Iterable[Mapping[str, Optional[str]]],
        source_name: str = DEFAULT_SOURCE_NAME,
        source_published_at: Optional[str] = None,
        downloaded_at: Optional[str] = None,
    ) -> "SponsorRegister":
        return cls(
            records=_records_from_rows(rows),
            source=SponsorRegisterSource(
                source_name=source_name,
                source_published_at=source_published_at,
                downloaded_at=downloaded_at,
            ),
        )

    def __iter__(self) -> Iterator[SponsorRecord]:
        return iter(self.records)


def confidence_band(confidence: float, is_match: bool = True) -> str:
    if not is_match and confidence <= 0:
        return "none"
    if confidence >= HIGH_CONFIDENCE:
        return "high"
    if confidence >= MEDIUM_CONFIDENCE:
        return "medium"
    return "low"


def _trigrams(text: str) -> set:
    """Character trigrams of a normalised name; for names shorter than 3 chars
    the whole string is used as a single key (3-char trigrams never collide with
    these 1-2 char keys)."""

    if len(text) < 3:
        return {text} if text else set()
    return {text[i : i + 3] for i in range(len(text) - 2)}


def _split_multi_value(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in value.replace(",", ";").split(";") if part.strip()]


def _normalise_csv_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")


def _normalise_row(row: Mapping[str, Optional[str]]) -> Dict[str, str]:
    return {
        _normalise_csv_key(key): (value or "").strip()
        for key, value in row.items()
        if key is not None
    }


def _first_value(row: Mapping[str, str], keys: Iterable[str]) -> str:
    for key in keys:
        value = row.get(key)
        if value:
            return value
    return ""


def _parse_rating(value: str) -> Optional[str]:
    text = value.strip()
    if not text:
        return None
    match = re.search(r"\b([AB])\s+rating\b", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    if text.upper() in {"A", "B"}:
        return text.upper()
    return text


def _parse_location(row: Mapping[str, str]) -> Optional[str]:
    location = _first_value(row, ("location", "address"))
    if location:
        return location

    parts = [
        _first_value(row, ("town_city", "town", "city")),
        _first_value(row, ("county", "region")),
    ]
    unique_parts: List[str] = []
    for part in parts:
        if part and part not in unique_parts:
            unique_parts.append(part)
    return ", ".join(unique_parts) or None


def _records_from_rows(rows: Iterable[Mapping[str, Optional[str]]]) -> List[SponsorRecord]:
    records: List[SponsorRecord] = []
    for raw_row in rows:
        row = _normalise_row(raw_row)
        organisation_name = _first_value(
            row,
            (
                "organisation_name",
                "organisation",
                "organization_name",
                "sponsor_name",
                "name",
            ),
        )
        if not organisation_name:
            continue

        route_text = _first_value(
            row,
            (
                "sponsor_routes",
                "routes",
                "route",
                "visa_routes",
                "visa_route",
                "sponsor_route",
            ),
        )
        rating_text = _first_value(row, ("rating", "type_rating", "type_and_rating"))
        records.append(
            SponsorRecord(
                organisation_name=organisation_name,
                sponsor_routes=_split_multi_value(route_text),
                rating=_parse_rating(rating_text),
                location=_parse_location(row),
                aliases=_split_multi_value(_first_value(row, ("aliases", "alias"))),
            )
        )
    return records


def _token_similarity(left: str, right: str) -> float:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0

    intersection = left_tokens & right_tokens
    dice = (2 * len(intersection)) / (len(left_tokens) + len(right_tokens))
    sorted_left = " ".join(sorted(left_tokens))
    sorted_right = " ".join(sorted(right_tokens))
    sequence = SequenceMatcher(None, sorted_left, sorted_right).ratio()

    if left_tokens <= right_tokens or right_tokens <= left_tokens:
        if min(len(left_tokens), len(right_tokens)) >= 2:
            # A subset can be a real trading-name match, but it can also be a
            # different entity such as a recruiter, hospital, school, or agency.
            # Keep it below the high-confidence threshold unless another score
            # independently earns that confidence.
            return max(dice, sequence, 0.86)
        return max(dice, sequence, 0.78)

    return max(dice, sequence)


def _has_weak_token_alignment(left: str, right: str) -> bool:
    left_tokens = left.split()
    right_tokens = right.split()
    if not left_tokens or not right_tokens:
        return True
    if set(left_tokens) <= set(right_tokens) or set(right_tokens) <= set(left_tokens):
        return False

    for token in left_tokens:
        best = max(SequenceMatcher(None, token, candidate).ratio() for candidate in right_tokens)
        if best < 0.80:
            return True
    return False


def _substring_score(query: str, candidate: str) -> float:
    query_tokens = query.split()
    candidate_tokens = candidate.split()
    if len(query_tokens) < 2 or len(candidate_tokens) < 2:
        return 0.0
    if query in candidate or candidate in query:
        return 0.86
    return 0.0


def _score_names(raw_query: str, raw_candidate: str) -> Tuple[float, str]:
    query = normalise_employer_name(raw_query)
    candidate = normalise_employer_name(raw_candidate)
    if not query or not candidate:
        return 0.0, "token_set"
    if query == candidate:
        return 1.0, "exact"

    sequence = SequenceMatcher(None, query, candidate).ratio()
    token_score = _token_similarity(query, candidate)
    substring_score = _substring_score(query, candidate)
    score = max(sequence, token_score, substring_score)
    if _has_weak_token_alignment(query, candidate):
        score *= 0.95
    if score == substring_score and substring_score > 0:
        return score, "substring"
    return score, "token_set"


class SponsorMatcher:
    """Match employer names against loaded sponsor records.

    This interface is intentionally data-source agnostic. Phase 1 uses a sample
    CSV fixture; later pipeline stages can pass records parsed from GOV.UK.
    """

    def __init__(
        self,
        records: Iterable[SponsorRecord] | SponsorRegister,
        source_name: str = DEFAULT_SOURCE_NAME,
        source_published_at: Optional[str] = None,
        downloaded_at: Optional[str] = None,
    ) -> None:
        if isinstance(records, SponsorRegister):
            self.records = list(records.records)
            self.source_metadata = records.source
        else:
            self.records = list(records)
            self.source_metadata = SponsorRegisterSource(
                source_name=source_name,
                source_published_at=source_published_at,
                downloaded_at=downloaded_at,
            )
        self.source_name = self.source_metadata.source_name
        self.source_published_at = self.source_metadata.source_published_at
        self.source_downloaded_at = self.source_metadata.downloaded_at
        self._build_index()

    def _build_index(self) -> None:
        """Precompute blocking indexes so ``match`` scores only plausible
        candidates instead of every record.

        Scoring itself is unchanged (``_score_names``). The candidate set for a
        query is every searchable name that is an exact normalised match, shares
        a normalised token with the query, or shares a character trigram with it.
        The token index covers the token-overlap and substring scoring paths; the
        trigram index covers the character-sequence path (including typos and
        missing letters, e.g. "tradng" -> "trading"). A name that shares neither
        a token nor a trigram with the query cannot reach ``LOW_CANDIDATE`` and so
        cannot change the returned match. Equivalence to the brute-force scan is
        checked in tests/test_sponsor_matching.py.
        """

        # Each entry: (record, original_searchable_name, name_type). The list
        # index doubles as the original iteration order for tie-breaking.
        self._entries: List[Tuple[SponsorRecord, str, str]] = []
        self._exact_index: Dict[str, int] = {}
        self._token_index: Dict[str, List[int]] = {}
        self._trigram_index: Dict[str, List[int]] = {}
        for record in self.records:
            for name, name_type in record.searchable_names:
                idx = len(self._entries)
                self._entries.append((record, name, name_type))
                norm = normalise_employer_name(name)
                if not norm:
                    continue
                self._exact_index.setdefault(norm, idx)
                for token in set(norm.split()):
                    self._token_index.setdefault(token, []).append(idx)
                for gram in _trigrams(norm):
                    self._trigram_index.setdefault(gram, []).append(idx)

    def _no_match(self, raw: str) -> EmployerMatch:
        return EmployerMatch(
            raw=raw,
            matched_name=None,
            confidence=0.0,
            confidence_band="none",
            match_method=None,
            sponsor_routes=[],
            rating=None,
            location=None,
            is_match=False,
            source_name=self.source_name,
            source_published_at=self.source_published_at,
            source_downloaded_at=self.source_downloaded_at,
        )

    def _build_match(
        self,
        raw: str,
        record: SponsorRecord,
        score: float,
        method: Optional[str],
        is_match: bool,
    ) -> EmployerMatch:
        # A demoted match (reliable would be score>=MEDIUM, but it failed the
        # distinctive-token gate) is surfaced as a low-confidence candidate so
        # the user still sees the closest register entry and can verify it.
        band = confidence_band(score, is_match) if is_match else (
            "low" if score > 0 else "none"
        )
        return EmployerMatch(
            raw=raw,
            matched_name=record.organisation_name,
            confidence=score,
            confidence_band=band,
            match_method=method,
            sponsor_routes=record.sponsor_routes,
            rating=record.rating,
            location=record.location,
            is_match=is_match,
            source_name=self.source_name,
            source_published_at=self.source_published_at,
            source_downloaded_at=self.source_downloaded_at,
        )

    @classmethod
    def from_csv(
        cls,
        path: Path,
        source_name: str = DEFAULT_SOURCE_NAME,
        source_published_at: Optional[str] = None,
        downloaded_at: Optional[str] = None,
    ) -> "SponsorMatcher":
        register = SponsorRegister.from_csv(
            path,
            source_name=source_name,
            source_published_at=source_published_at,
            downloaded_at=downloaded_at,
        )
        return cls.from_register(register)

    @classmethod
    def from_register(cls, register: SponsorRegister) -> "SponsorMatcher":
        return cls(register)

    def match(self, employer_raw: str) -> EmployerMatch:
        raw = (employer_raw or "").strip()
        if not raw:
            return self._no_match(employer_raw or "")

        query = normalise_employer_name(raw)

        # Exact normalised match scores 1.0; nothing can beat it, so the first
        # such entry (by original order) is the answer.
        if query:
            exact_idx = self._exact_index.get(query)
            if exact_idx is not None:
                record, _name, name_type = self._entries[exact_idx]
                method = "exact" if name_type == "organisation_name" else "alias"
                return self._build_match(raw, record, 1.0, method, is_match=True)

        # Otherwise score candidates that share a token or a trigram with the
        # query (a superset of everything that can reach LOW_CANDIDATE).
        candidate_idxs: set[int] = set()
        if query:
            for token in set(query.split()):
                candidate_idxs.update(self._token_index.get(token, ()))
            for gram in _trigrams(query):
                candidate_idxs.update(self._trigram_index.get(gram, ()))

        best_idx: Optional[int] = None
        best_score = 0.0
        best_method: Optional[str] = None
        for idx in sorted(candidate_idxs):
            _record, searchable_name, name_type = self._entries[idx]
            score, method = _score_names(raw, searchable_name)
            if score > best_score:
                best_idx = idx
                best_score = score
                if score == 1.0:
                    best_method = "exact" if name_type == "organisation_name" else "alias"
                else:
                    best_method = "alias" if name_type == "alias" else method

        if best_idx is None or best_score < LOW_CANDIDATE:
            return self._no_match(raw)

        best_record, best_name, _name_type = self._entries[best_idx]
        # A non-exact match only counts as reliable if it is either very strong
        # (>= HIGH) or rests on a shared distinctive token. This rejects pure
        # character coincidences between different companies.
        reliable = best_score >= HIGH_CONFIDENCE or (
            best_score >= MEDIUM_CONFIDENCE
            and _shares_distinctive_token(query, normalise_employer_name(best_name))
        )
        return self._build_match(
            raw, best_record, best_score, best_method, is_match=reliable
        )
