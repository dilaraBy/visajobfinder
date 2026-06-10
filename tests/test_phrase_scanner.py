import unittest

from pipeline.classifier.phrase_scanner import scan_description


class PhraseScannerTest(unittest.TestCase):
    def test_scans_obvious_blockers(self):
        signals = scan_description("British citizenship required. We cannot provide visa sponsorship.")
        categories = {signal.category for signal in signals}
        self.assertIn("citizenship_required", categories)
        self.assertIn("no_sponsorship", categories)

    def test_scans_ambiguous_future_right_to_work_phrase(self):
        signals = scan_description("You must have the right to work in the UK now and in the future.")
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].category, "future_sponsorship_risk")
        self.assertIn("now and in the future", signals[0].text.lower())

    def test_scans_security_clearance_as_amber(self):
        signals = scan_description("The successful candidate may need SC clearance.")
        self.assertEqual(signals[0].category, "security_clearance")
        self.assertEqual(signals[0].severity, "amber")

    def test_scans_without_sponsorship_variants_from_real_ads(self):
        examples = [
            "Please select 'No' if you would require visa sponsorship.",
            "The right-to-work question says to select 'No' if visa sponsorship would be required.",
            "Candidates need the right to work in the UK without sponsorship.",
            "Application asks whether the candidate has full right to work in the UK without sponsorship.",
            "You need legal right to work in the UK without requiring visa sponsorship.",
            "The employer is unable to sponsor employees either now or in the future.",
        ]

        for text in examples:
            with self.subTest(text=text):
                categories = {signal.category for signal in scan_description(text)}
                self.assertIn("no_sponsorship", categories)

    def test_scans_future_sponsorship_question(self):
        signals = scan_description("Will you require visa sponsorship at any point to work in the UK?")
        self.assertEqual(signals[0].category, "future_sponsorship_risk")

    def test_scans_temporary_right_to_work_future_sponsorship_wording(self):
        signals = scan_description(
            "I have temporary right to work in the UK, and might need sponsorship in the future."
        )
        self.assertEqual(signals[0].category, "future_sponsorship_risk")

    def test_scans_work_without_restriction_as_permanent_right_to_work(self):
        signals = scan_description("Do you have the right to work in the UK without restriction?")
        self.assertEqual(signals[0].category, "permanent_right_to_work")
        self.assertEqual(signals[0].severity, "red")

    def test_scans_generic_eligibility_to_work_as_ambiguous(self):
        signals = scan_description("Candidates must be eligible to work in the UK.")
        self.assertEqual(signals[0].category, "ambiguous")
        self.assertEqual(signals[0].text, "must be eligible to work in the UK")

    def test_scans_all_applicants_right_to_work_span(self):
        signals = scan_description("All applicants must have the right to work in the UK.")
        self.assertEqual(signals[0].category, "ambiguous")
        self.assertEqual(signals[0].text, "All applicants must have the right to work in the UK")

    def test_scans_registered_sponsor_and_case_by_case_wording(self):
        signals = scan_description(
            "Octopus Energy is a registered visa sponsor and sponsorship is considered case by case."
        )
        categories = {signal.category for signal in signals}
        self.assertIn("sponsorship_positive", categories)
        self.assertIn("ambiguous", categories)

    def test_scans_application_form_right_to_work_questions(self):
        signals = scan_description("Do you have the legal right to work in London?")
        self.assertEqual(signals[0].category, "ambiguous")
        self.assertEqual(signals[0].text, "Do you have the legal right to work in London?")

    def test_scans_temporary_right_to_work_status_sponsorship_needs(self):
        signals = scan_description(
            "The form asks candidates to select current right-to-work status including "
            "temporary right-to-work status and sponsorship needs."
        )
        categories = {signal.category for signal in signals}
        self.assertIn("future_sponsorship_risk", categories)


if __name__ == "__main__":
    unittest.main()
