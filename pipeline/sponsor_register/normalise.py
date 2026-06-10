"""Employer-name normalisation for sponsor-register matching."""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, List


LEGAL_SUFFIXES = {
    "ltd",
    "limited",
    "plc",
    "llp",
    "llc",
    "inc",
    "incorporated",
    "co",
    "company",
    "corp",
    "corporation",
    "cic",
    "gmbh",
    "sa",
    "bv",
}

TRAILING_CONTEXT_SUFFIXES = {
    "uk",
    "group",
    "holdings",
    "holding",
    "international",
}

PUNCTUATION_RE = re.compile(r"[^a-z0-9]+")


def _ascii_fold(value: str) -> str:
    return (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def _strip_suffixes(tokens: Iterable[str]) -> List[str]:
    filtered = [token for token in tokens if token not in LEGAL_SUFFIXES]
    while len(filtered) > 1 and filtered[-1] in TRAILING_CONTEXT_SUFFIXES:
        filtered.pop()
    return filtered


def normalise_employer_name(name: str) -> str:
    """Return a conservative normalised employer name.

    The normaliser removes legal suffixes and trailing context words, but keeps
    core tokens such as a leading "UK" because those can be part of a real
    organisation name.
    """

    if not name:
        return ""

    text = _ascii_fold(name).lower()
    text = text.replace("&", " and ")
    text = text.replace("'", "")
    text = PUNCTUATION_RE.sub(" ", text)
    tokens = _strip_suffixes(text.split())
    return " ".join(tokens)

