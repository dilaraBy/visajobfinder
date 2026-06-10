from pathlib import Path
import unittest

from pipeline.classifier.engine import analyse_job, classify_job
from pipeline.classifier.models import JobInput, UserContext
from pipeline.sponsor_register.matcher import SponsorMatcher


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "data" / "sponsor_register" / "sample_sponsors.csv"


class ClassificationTest(unittest.TestCase):
    def setUp(self):
        self.matcher = SponsorMatcher.from_csv(
            FIXTURE_PATH,
            source_published_at="2026-06-04",
        )

    def classify(self, description, employer="Example Ltd", user=None, salary_text=None):
        job = JobInput(
            title="Graduate Analyst",
            employer_raw=employer,
            description_text=description,
            salary_text=salary_text,
        )
        return classify_job(
            job,
            user or UserContext(visa_situation="graduate_route", needs_future_sponsorship=True),
            self.matcher,
        ).to_dict()

    def test_obvious_citizenship_blocker_is_likely_blocked(self):
        result = self.classify(
            "Applicants must be a British citizen and able to obtain clearance.",
            user=UserContext(visa_situation="needs_sponsorship_before_start"),
        )
        self.assertEqual(result["label"], "likely_blocked")
        self.assertTrue(result["evidence"])
        self.assertTrue(result["limitations"])
        self.assertTrue(result["what_to_verify"])

    def test_ambiguous_future_right_to_work_is_verify_first(self):
        result = self.classify(
            "Candidates must have the right to work in the UK now and in the future.",
            user=UserContext(visa_situation="graduate_route", needs_future_sponsorship=True),
        )
        self.assertEqual(result["label"], "verify_first")
        self.assertIn("ambiguous", result["reason"].lower())

    def test_graduate_route_with_sponsor_match_and_no_blocker_is_worth_applying(self):
        result = self.classify(
            "This is a graduate role for candidates with the right to work in the UK.",
            user=UserContext(visa_situation="graduate_route", needs_future_sponsorship=True),
            salary_text="GBP 32,000 per year",
        )
        self.assertEqual(result["label"], "worth_applying")
        self.assertIn("No detected blocker", result["reason"])
        self.assertEqual(result["employer_match"]["confidence_band"], "high")

    def test_needs_sponsorship_before_start_without_role_level_sponsorship_is_verify_first(self):
        result = self.classify(
            "This is a graduate role for candidates with the right to work in the UK.",
            user=UserContext(visa_situation="needs_sponsorship_before_start"),
        )
        self.assertEqual(result["label"], "verify_first")
        self.assertIn("does not clearly say", result["reason"])

    def test_needs_sponsorship_before_start_with_positive_sponsor_and_salary_is_worth_applying(self):
        result = self.classify(
            "Visa sponsorship available for suitable candidates.",
            user=UserContext(visa_situation="needs_sponsorship_before_start"),
            salary_text="GBP 35,000 per year",
        )
        self.assertEqual(result["label"], "worth_applying")
        self.assertIn("No detected blocker", result["reason"])

    def test_needs_sponsorship_before_start_medium_sponsor_match_is_verify_first(self):
        result = self.classify(
            "Visa sponsorship available for suitable candidates.",
            employer="Bright Future University Hospital",
            user=UserContext(visa_situation="needs_sponsorship_before_start"),
            salary_text="GBP 35,000 per year",
        )
        self.assertEqual(result["label"], "verify_first")
        self.assertEqual(result["employer_match"]["confidence_band"], "medium")
        self.assertIn("medium-confidence", result["reason"])

    def test_needs_sponsorship_before_start_no_sponsorship_is_likely_blocked(self):
        result = self.classify(
            "We cannot provide visa sponsorship for this role.",
            user=UserContext(visa_situation="needs_sponsorship_before_start"),
        )
        self.assertEqual(result["label"], "likely_blocked")
        self.assertIn("sponsorship is not available", result["reason"])

    def test_without_sponsorship_wording_blocks_sponsorship_before_start(self):
        result = self.classify(
            "Applicants must have the right to work in the UK without sponsorship.",
            user=UserContext(visa_situation="needs_sponsorship_before_start"),
        )
        self.assertEqual(result["label"], "likely_blocked")

    def test_graduate_route_no_blocker_no_future_sponsorship_question_is_worth_applying(self):
        # Graduate Route users have current right to work. If the JD has no explicit
        # future-sponsorship question, missing salary is noted in limitations but
        # does not force verify_first — the user can apply and verify later.
        result = self.classify(
            "This is a graduate role for candidates with the right to work in the UK.",
            user=UserContext(visa_situation="graduate_route", needs_future_sponsorship=True),
        )
        self.assertEqual(result["label"], "worth_applying")
        self.assertIn("No detected blocker", result["reason"])
        # Salary limitation is still surfaced
        self.assertTrue(
            any("salary" in lim.lower() for lim in result["limitations"])
        )

    def test_graduate_route_future_sponsorship_medium_sponsor_match_is_verify_first(self):
        result = self.classify(
            "This is a graduate role for candidates with the right to work in the UK.",
            employer="Bright Future University Hospital",
            user=UserContext(visa_situation="graduate_route", needs_future_sponsorship=True),
            salary_text="GBP 32,000 per year",
        )
        self.assertEqual(result["label"], "verify_first")
        self.assertEqual(result["employer_match"]["confidence_band"], "medium")
        self.assertIn("medium-confidence", result["reason"])

    def test_graduate_route_start_after_expiry_is_verify_first(self):
        result = self.classify(
            "Visa sponsorship available for suitable candidates.",
            user=UserContext(
                visa_situation="graduate_route",
                needs_future_sponsorship=True,
                visa_expiry_month="2026-07",
                target_start_month="2026-09",
            ),
            salary_text="GBP 35,000 per year",
        )
        self.assertEqual(result["label"], "verify_first")
        self.assertIn("target start month", result["reason"].lower())

    def test_graduate_route_future_no_sponsorship_is_likely_blocked(self):
        result = self.classify(
            "The employer is unable to sponsor employees either now or in the future.",
            user=UserContext(visa_situation="graduate_route", needs_future_sponsorship=True),
            salary_text="GBP 32,000 per year",
        )
        self.assertEqual(result["label"], "likely_blocked")
        self.assertIn("future", result["reason"].lower())

    def test_missing_employer_returns_unknown_with_missing_evidence(self):
        result = self.classify(
            "This is a graduate role for candidates with the right to work in the UK.",
            employer="",
            user=UserContext(visa_situation="graduate_route", needs_future_sponsorship=True),
            salary_text="GBP 32,000 per year",
        )
        self.assertEqual(result["label"], "unknown")
        self.assertTrue(
            any(item["type"] == "missing_evidence" for item in result["evidence"])
        )
        self.assertIn("Employer name is missing", " ".join(result["limitations"]))

    def test_contradictory_sponsorship_copy_is_verify_first(self):
        result = self.classify(
            "Visa sponsorship available. We cannot provide visa sponsorship for this role.",
            user=UserContext(visa_situation="needs_sponsorship_before_start"),
            salary_text="GBP 35,000 per year",
        )
        self.assertEqual(result["label"], "verify_first")
        self.assertIn("contradictory", result["reason"].lower())

    def test_analyse_job_returns_contract_shaped_output(self):
        output = analyse_job(
            JobInput(
                title="Graduate Analyst",
                employer_raw="Example Ltd",
                description_text="Visa sponsorship available for suitable candidates.",
                salary_text="GBP 35,000 per year",
            ),
            UserContext(visa_situation="needs_sponsorship_before_start"),
            self.matcher,
        )
        self.assertIn("job", output)
        self.assertIn("classification", output)
        self.assertEqual(output["classification"]["job_id"], "paste:manual")
        self.assertIn("visa_signals", output["job"])
        self.assertEqual(
            output["classification"]["employer_match"]["source_name"],
            "GOV.UK Register of Licensed Sponsors",
        )
        self.assertEqual(
            output["classification"]["employer_match"]["source_published_at"],
            "2026-06-04",
        )

    # --- Rule-tuning regression tests (covers the 6 real-seed misses fixed) ---

    def test_graduate_route_permanent_rtw_phrase_is_verify_first_not_blocked(self):
        # real-018: "right to work in the UK without restriction" is a form question,
        # not a citizenship mandate.  For Graduate Route it should be verify_first
        # (they have legal RTW), not likely_blocked.
        result = self.classify(
            "Please confirm: do you have the right to work in the UK without restriction?",
            user=UserContext(visa_situation="graduate_route", needs_future_sponsorship=True),
        )
        self.assertNotEqual(result["label"], "likely_blocked")
        self.assertEqual(result["label"], "verify_first")

    def test_needs_sponsorship_permanent_rtw_phrase_is_still_likely_blocked(self):
        # For a user who needs sponsorship before start, "without restriction" is decisive.
        result = self.classify(
            "Please confirm: do you have the right to work in the UK without restriction?",
            user=UserContext(visa_situation="needs_sponsorship_before_start"),
        )
        self.assertEqual(result["label"], "likely_blocked")

    def test_graduate_route_future_sponsorship_question_alone_is_verify_first(self):
        # real-006, 014-017: future sponsorship question with no sponsor-positive
        # signal should remain verify_first for Graduate Route.
        result = self.classify(
            "Will you now or in the future require visa sponsorship to work in the UK?",
            user=UserContext(visa_situation="graduate_route", needs_future_sponsorship=True),
        )
        self.assertEqual(result["label"], "verify_first")

    def test_graduate_route_future_sponsorship_question_with_sponsor_match_and_positive_is_worth_applying(self):
        # real-004: future-sponsorship question + sponsor-positive wording + confirmed
        # sponsor match = Graduate Route user is worth_applying.
        result = self.classify(
            "We are a registered visa sponsor and consider sponsorship on a case by case basis. "
            "Do you have temporary right to work in the UK and might need sponsorship in the future?",
            employer="Octopus Energy Group",
            user=UserContext(visa_situation="graduate_route", needs_future_sponsorship=True),
        )
        self.assertEqual(result["label"], "worth_applying")

    def test_graduate_route_no_sponsor_match_no_explicit_future_risk_is_worth_applying(self):
        # real-007, real-008, real-019: no sponsor-register match but JD contains only
        # generic right-to-work language (not an explicit future-sponsorship question).
        # Graduate Route user has current RTW — should be worth_applying.
        result = self.classify(
            "Please indicate whether you have the right to work in the UK.",
            employer="UnlistedCompanyXYZ",
            user=UserContext(visa_situation="graduate_route", needs_future_sponsorship=True),
        )
        self.assertEqual(result["label"], "worth_applying")

    def test_graduate_route_sponsor_match_case_by_case_no_salary_is_worth_applying(self):
        # real-003: confirmed sponsor-register employer with case-by-case sponsorship
        # wording and no salary listed; Graduate Route should be worth_applying —
        # salary absence is captured in limitations, not as a blocker.
        result = self.classify(
            "We are a registered visa sponsor. Sponsorship is considered on a case by case basis, "
            "but we are not able to offer it for every role.",
            employer="Octopus Energy Group",
            user=UserContext(visa_situation="graduate_route", needs_future_sponsorship=True),
        )
        self.assertEqual(result["label"], "worth_applying")
        self.assertTrue(
            any("salary" in lim.lower() for lim in result["limitations"]),
            "Salary limitation should still appear even when not a blocker",
        )

    def test_graduate_route_future_sponsorship_question_without_sponsor_match_is_verify_first(self):
        # If a JD explicitly asks about future sponsorship AND there is no sponsor-register
        # match, Graduate Route should remain verify_first (the JD raises the question).
        result = self.classify(
            "Will you now or in the future require visa sponsorship?",
            employer="UnlistedCompanyXYZ",
            user=UserContext(visa_situation="graduate_route", needs_future_sponsorship=True),
        )
        self.assertEqual(result["label"], "verify_first")

    def test_needs_sponsorship_future_question_without_positive_signal_is_verify_first(self):
        # For NSS: future-sponsorship question with no positive wording should be verify_first.
        result = self.classify(
            "Will you now or in the future require visa sponsorship to work in the UK?",
            employer="UnlistedCompanyXYZ",
            user=UserContext(visa_situation="needs_sponsorship_before_start"),
        )
        self.assertEqual(result["label"], "verify_first")


if __name__ == "__main__":
    unittest.main()
