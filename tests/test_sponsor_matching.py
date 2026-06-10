from pathlib import Path
import unittest

from pipeline.sponsor_register.matcher import (
    LOW_CANDIDATE,
    SponsorMatcher,
    SponsorRecord,
    SponsorRegister,
    _score_names,
)
from pipeline.sponsor_register.normalise import normalise_employer_name


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "data" / "sponsor_register" / "sample_sponsors.csv"


def _brute_force_match(matcher: SponsorMatcher, raw: str):
    """Reference implementation: the exhaustive scan the index replaces.

    Returns (matched_name, confidence, match_method) so the indexed matcher can
    be asserted equivalent to scanning every record.
    """

    text = (raw or "").strip()
    if not text:
        return (None, 0.0, None)
    best_name = None
    best_score = 0.0
    best_method = None
    for record in matcher.records:
        for name, name_type in record.searchable_names:
            score, method = _score_names(text, name)
            if score > best_score:
                best_score = score
                best_name = record.organisation_name
                if score == 1.0:
                    best_method = "exact" if name_type == "organisation_name" else "alias"
                else:
                    best_method = "alias" if name_type == "alias" else method
    if best_name is None or best_score < LOW_CANDIDATE:
        return (None, 0.0, None)
    return (best_name, best_score, best_method)


class SponsorMatchingTest(unittest.TestCase):
    def setUp(self):
        self.matcher = SponsorMatcher.from_csv(
            FIXTURE_PATH,
            source_published_at="2026-06-04",
        )

    def test_normalise_employer_name_strips_legal_suffixes(self):
        self.assertEqual(normalise_employer_name("Example UK Limited"), "example")
        self.assertEqual(normalise_employer_name("Acme Digital Ltd."), "acme digital")
        self.assertEqual(normalise_employer_name("Bright Future University"), "bright future university")

    def test_exact_match(self):
        match = self.matcher.match("Northbridge Analytics Ltd")
        self.assertTrue(match.is_match)
        self.assertEqual(match.confidence_band, "high")
        self.assertEqual(match.matched_name, "Northbridge Analytics Ltd")
        self.assertEqual(match.match_method, "exact")

    def test_alias_match(self):
        match = self.matcher.match("BFU")
        self.assertTrue(match.is_match)
        self.assertEqual(match.confidence_band, "high")
        self.assertEqual(match.matched_name, "Bright Future University")
        self.assertEqual(match.match_method, "alias")

    def test_fixture_mode_preserves_source_metadata(self):
        match = self.matcher.match("Example Ltd")
        self.assertTrue(match.is_match)
        self.assertEqual(match.matched_name, "Example UK Limited")
        self.assertEqual(match.source_name, "GOV.UK Register of Licensed Sponsors")
        self.assertEqual(match.source_published_at, "2026-06-04")

    def test_medium_or_high_fuzzy_match_for_minor_typo(self):
        match = self.matcher.match("Northbridge Analytcs")
        self.assertTrue(match.is_match)
        self.assertIn(match.confidence_band, {"medium", "high"})
        self.assertEqual(match.matched_name, "Northbridge Analytics Ltd")

    def test_low_confidence_candidate_is_not_reliable_match(self):
        match = self.matcher.match("North Analytics")
        self.assertFalse(match.is_match)
        self.assertEqual(match.confidence_band, "low")
        self.assertEqual(match.matched_name, "Northbridge Analytics Ltd")

    def test_subset_with_extra_entity_context_is_not_high_confidence(self):
        match = self.matcher.match("Bright Future University Hospital")
        self.assertTrue(match.is_match)
        self.assertEqual(match.confidence_band, "medium")
        self.assertEqual(match.match_method, "substring")
        self.assertEqual(match.matched_name, "Bright Future University")

    def test_missing_employer_returns_contract_none_match(self):
        match = self.matcher.match("")
        self.assertFalse(match.is_match)
        self.assertEqual(match.confidence_band, "none")
        self.assertIsNone(match.matched_name)
        self.assertEqual(match.source_name, "GOV.UK Register of Licensed Sponsors")

    def test_no_match_for_unrelated_employer(self):
        match = self.matcher.match("Completely Unrelated Employer")
        self.assertFalse(match.is_match)
        self.assertEqual(match.confidence_band, "none")
        self.assertIsNone(match.matched_name)


class DistinctiveTokenGateTest(unittest.TestCase):
    """Fuzzy matches in the medium band must rest on a shared distinctive token,
    not a character coincidence between different companies."""

    def _matcher(self) -> SponsorMatcher:
        names = [
            "Bechtel Limited",
            "Academicians Ltd",
            "Eyesto Education Limited",
            "Reeson Recruitment Group",
            "Christie Owen & Davies Limited",
        ]
        records = [
            SponsorRecord(name, ["Skilled Worker"], "A", "London", [])
            for name in names
        ]
        return SponsorMatcher(records)

    def test_character_coincidence_is_demoted(self):
        matcher = self._matcher()
        # Different companies that only look alike: keep the closest entry visible
        # for transparency, but do NOT assert a reliable sponsor match.
        for query, closest in [
            ("Bechtle UK", "Bechtel Limited"),
            ("Academics", "Academicians Ltd"),
        ]:
            with self.subTest(query=query):
                match = matcher.match(query)
                self.assertEqual(match.matched_name, closest)
                self.assertFalse(match.is_match)
                self.assertEqual(match.confidence_band, "low")

    def test_only_generic_shared_token_is_demoted(self):
        # "Reeson Education" vs "Eyesto Education" share only the generic word
        # "education" -> not a reliable match.
        match = self._matcher().match("Reeson Education")
        self.assertEqual(match.matched_name, "Eyesto Education Limited")
        self.assertFalse(match.is_match)

    def test_distinctive_shared_token_keeps_match(self):
        # "Christie & Co" shares the distinctive token "christie".
        match = self._matcher().match("Christie & Co")
        self.assertEqual(match.matched_name, "Christie Owen & Davies Limited")
        self.assertTrue(match.is_match)
        self.assertEqual(match.confidence_band, "medium")

    def test_parsed_govuk_rows_carry_source_metadata(self):
        register = SponsorRegister.from_rows(
            [
                {
                    "Organisation Name": "GOV.UK Parsed Sponsor Ltd",
                    "Route": "Skilled Worker",
                    "Type & Rating": "Worker (A rating)",
                    "Town/City": "Leeds",
                    "County": "West Yorkshire",
                    "Aliases": "Parsed Sponsor",
                }
            ],
            source_name="GOV.UK test CSV snapshot",
            downloaded_at="2026-06-04T09:30:00Z",
        )

        matcher = SponsorMatcher.from_register(register)
        match = matcher.match("Parsed Sponsor")

        self.assertTrue(match.is_match)
        self.assertEqual(match.match_method, "alias")
        self.assertEqual(match.matched_name, "GOV.UK Parsed Sponsor Ltd")
        self.assertEqual(match.sponsor_routes, ["Skilled Worker"])
        self.assertEqual(match.rating, "A")
        self.assertEqual(match.location, "Leeds, West Yorkshire")
        self.assertEqual(match.source_name, "GOV.UK test CSV snapshot")
        self.assertIsNone(match.source_published_at)
        self.assertEqual(match.source_downloaded_at, "2026-06-04T09:30:00Z")
        self.assertEqual(matcher.source_downloaded_at, "2026-06-04T09:30:00Z")
        self.assertEqual(
            matcher.source_metadata.to_dict(),
            {
                "source_name": "GOV.UK test CSV snapshot",
                "source_published_at": None,
                "downloaded_at": "2026-06-04T09:30:00Z",
            },
        )


class IndexedMatcherEquivalenceTest(unittest.TestCase):
    """The blocking index must return the same match as the brute-force scan."""

    def _register(self) -> SponsorMatcher:
        # A register large and varied enough that the index actually prunes:
        # shared tokens, overlapping substrings, and near-duplicates.
        bases = [
            "Northbridge Analytics Ltd",
            "Northbridge Consulting Group",
            "North Star Trading Limited",
            "Bright Future University",
            "Bright Future Recruitment Ltd",
            "CareWorks Group Limited",
            "Care Solutions UK",
            "Octopus Energy Group",
            "Acme Digital Ltd",
            "Acme Engineering Services",
            "Global Tech Solutions Ltd",
            "Greenfield Trading Company",
            "Riverside Care Homes",
            "Meridian Financial Partners",
            "Summit Consulting Limited",
            "Apex Engineering Group",
            "Bluewave Technologies",
            "Crown Recruitment Agency",
            "Delta Logistics UK",
            "Evergreen Holdings Ltd",
        ]
        records = [
            SponsorRecord(
                organisation_name=name,
                sponsor_routes=["Skilled Worker"],
                rating="A",
                location="London",
                aliases=[],
            )
            for name in bases
        ]
        return SponsorMatcher(records)

    def test_indexed_equals_brute_force(self):
        matcher = self._register()
        probes = [
            # exact + case + legal-suffix variants
            "Northbridge Analytics Ltd",
            "NORTHBRIDGE ANALYTICS LTD",
            "Northbridge Analytics",
            "Octopus Energy",
            "CareWorks Group",
            # typos / missing letters (character-sequence path)
            "Northbrige Analytcs",
            "Globl Tech Solutions",
            "Conslting Limited",
            "Recruitement Agency",
            # token subsets and unrelated
            "Care Homes",
            "Trading Company",
            "Engineering Group",
            "Completely Unrelated Employer",
            "zzqq nonexistent xyz",
            "",
            "   ",
        ]
        for probe in probes:
            with self.subTest(probe=probe):
                expected = _brute_force_match(matcher, probe)
                match = matcher.match(probe)
                self.assertEqual(
                    (match.matched_name, match.confidence, match.match_method),
                    expected,
                )

    def test_sample_register_matches_brute_force(self):
        matcher = SponsorMatcher.from_csv(FIXTURE_PATH)
        for probe in [
            "Example Ltd",
            "Northbridge Analytics Ltd",
            "Northbridge Analytcs",
            "BFU",
            "Bright Future University Hospital",
            "North Analytics",
            "Completely Unrelated Employer",
        ]:
            with self.subTest(probe=probe):
                expected = _brute_force_match(matcher, probe)
                match = matcher.match(probe)
                self.assertEqual(
                    (match.matched_name, match.confidence, match.match_method),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
