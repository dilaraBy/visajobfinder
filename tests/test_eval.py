from pathlib import Path
import copy
import unittest
from unittest.mock import patch

from pipeline.eval.run_eval import (
    evaluate_dataset,
    evidence_matches,
    format_report,
    load_dataset,
    validate_dataset,
)
from pipeline.sponsor_register.matcher import SponsorMatcher


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "eval" / "labelled_jobs.sample.json"
REAL_DATASET_PATH = ROOT / "data" / "eval" / "labelled_jobs.real.json"
SYNTHETIC_DATASET_PATH = ROOT / "data" / "eval" / "synthetic_edge_cases.json"
SPONSOR_PATH = ROOT / "data" / "sponsor_register" / "sample_sponsors.csv"


class EvalTest(unittest.TestCase):
    def setUp(self):
        self.dataset = load_dataset(DATASET_PATH)
        self.matcher = SponsorMatcher.from_csv(SPONSOR_PATH)

    def test_sample_dataset_reports_required_metrics(self):
        report = evaluate_dataset(self.dataset, self.matcher)

        self.assertEqual(report["dataset"]["records"], 7)
        self.assertEqual(report["dataset"]["cases"], 14)
        self.assertIn("graduate_route", report["by_visa_situation"])
        self.assertIn("needs_sponsorship_before_start", report["by_visa_situation"])

        graduate = report["by_visa_situation"]["graduate_route"]
        self.assertIn("false_red", graduate)
        self.assertIn("false_green", graduate)
        self.assertIn("unknown", graduate)
        self.assertIn("verify_first", graduate)

        self.assertEqual(
            report["sponsor_matching"]["high_confidence_precision"],
            100.0,
        )
        self.assertEqual(
            report["sponsor_matching"]["labelled_decision_precision"],
            100.0,
        )
        self.assertEqual(
            report["sponsor_matching"]["labelled_sponsor_precision"],
            100.0,
        )
        self.assertEqual(report["evidence_extraction"]["accuracy"], 100.0)

    def test_report_is_readable_for_readme(self):
        report = evaluate_dataset(self.dataset, self.matcher)
        text = format_report(report)

        self.assertIn("Visa Engine Evaluation", text)
        self.assertIn("False red rate", text)
        self.assertIn("False green rate", text)
        self.assertIn("Unknown rate", text)
        self.assertIn("Verify-first rate", text)
        self.assertIn("Sponsor matching", text)
        self.assertIn("Labelled sponsor precision", text)
        self.assertIn("Evidence extraction", text)
        self.assertIn("not legal or immigration advice", text)

    def test_real_seed_dataset_schema_is_executable(self):
        dataset = load_dataset(REAL_DATASET_PATH)
        report = evaluate_dataset(dataset, self.matcher)

        self.assertEqual(report["dataset"]["records"], 20)
        self.assertEqual(report["dataset"]["records_excluded"], 0)
        self.assertEqual(report["dataset"]["cases"], 40)
        self.assertIn("graduate_route", report["by_visa_situation"])
        self.assertIn("needs_sponsorship_before_start", report["by_visa_situation"])
        self.assertIsNotNone(
            report["by_visa_situation"]["needs_sponsorship_before_start"]["false_green"]["rate"]
        )
        self.assertEqual(report["sponsor_matching"]["labelled_records"], 20)
        self.assertIsNotNone(report["sponsor_matching"]["labelled_sponsor_precision"])
        self.assertGreater(report["sponsor_matching"]["high_confidence_predictions"], 0)
        self.assertIsNotNone(report["sponsor_matching"]["high_confidence_precision"])

    def test_real_seed_dataset_has_review_metadata(self):
        dataset = load_dataset(REAL_DATASET_PATH)
        validation = validate_dataset(dataset)

        self.assertEqual(validation["records_checked"], 20)
        self.assertEqual(validation["records_in_eval"], 20)
        self.assertEqual(validation["records_excluded"], 0)
        self.assertEqual(validation["errors"], [])

        for record in dataset["records"]:
            self.assertEqual(record["review_status"], "confirmed")
            self.assertIsInstance(record["default_dashboard_fit"], bool)
            self.assertEqual(record["eval_use"], "classification_and_evidence")

    def test_excluded_records_are_not_counted(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["records"][0]["eval_use"] = "exclude"

        report = evaluate_dataset(dataset, self.matcher)

        self.assertEqual(report["dataset"]["records_available"], 7)
        self.assertEqual(report["dataset"]["records"], 6)
        self.assertEqual(report["dataset"]["records_excluded"], 1)
        self.assertEqual(report["dataset"]["cases"], 12)

    def test_metric_rates_are_calculated_from_classifier_outputs(self):
        dataset = {
            "schema_version": 1,
            "name": "metric unit dataset",
            "records": [
                {
                    "eval_id": "metric:001",
                    "source": "manual",
                    "title": "Case one",
                    "employer_raw": "Example Ltd",
                    "description_text": "Visa sponsorship available.",
                    "eval_use": "classification_and_evidence",
                    "cases": [
                        {
                            "case_id": "metric:001:graduate",
                            "user_context": {"visa_situation": "graduate_route"},
                            "expected_label": "worth_applying",
                            "expected_evidence": [
                                {
                                    "category": "sponsorship_positive",
                                    "text_contains": "Visa sponsorship available",
                                }
                            ],
                        }
                    ],
                },
                {
                    "eval_id": "metric:002",
                    "source": "manual",
                    "title": "Case two",
                    "employer_raw": "Example Ltd",
                    "description_text": "Sponsorship unclear.",
                    "eval_use": "classification_and_evidence",
                    "cases": [
                        {
                            "case_id": "metric:002:graduate",
                            "user_context": {"visa_situation": "graduate_route"},
                            "expected_label": "verify_first",
                            "expected_evidence": [
                                {
                                    "category": "ambiguous",
                                    "text_contains": "Sponsorship unclear",
                                }
                            ],
                        }
                    ],
                },
                {
                    "eval_id": "metric:003",
                    "source": "manual",
                    "title": "Case three",
                    "employer_raw": "Example Ltd",
                    "description_text": "We cannot provide visa sponsorship.",
                    "eval_use": "classification_and_evidence",
                    "cases": [
                        {
                            "case_id": "metric:003:graduate",
                            "user_context": {"visa_situation": "graduate_route"},
                            "expected_label": "likely_blocked",
                            "expected_evidence": [
                                {
                                    "category": "no_sponsorship",
                                    "text_contains": "cannot provide visa sponsorship",
                                }
                            ],
                        }
                    ],
                },
                {
                    "eval_id": "metric:004",
                    "source": "manual",
                    "title": "Case four",
                    "employer_raw": "Example Ltd",
                    "description_text": "Missing signal.",
                    "eval_use": "classification_and_evidence",
                    "cases": [
                        {
                            "case_id": "metric:004:graduate",
                            "user_context": {"visa_situation": "graduate_route"},
                            "expected_label": "likely_blocked",
                            "expected_evidence": [
                                {
                                    "category": "no_sponsorship",
                                    "text_contains": "Missing signal",
                                }
                            ],
                        }
                    ],
                },
            ],
        }
        outputs = [
            _classification_output(
                "worth_applying",
                [{"category": "sponsorship_positive", "text": "Visa sponsorship available"}],
            ),
            _classification_output(
                "likely_blocked",
                [{"category": "ambiguous", "text": "Sponsorship unclear"}],
            ),
            _classification_output(
                "worth_applying",
                [{"category": "no_sponsorship", "text": "cannot provide visa sponsorship"}],
            ),
            _classification_output(
                "unknown",
                [{"category": "ambiguous", "text": "Missing signal"}],
            ),
        ]

        with patch("pipeline.eval.run_eval.analyse_job", side_effect=outputs):
            report = evaluate_dataset(dataset, self.matcher)

        graduate = report["by_visa_situation"]["graduate_route"]
        self.assertEqual(graduate["exact_label"], {"count": 1, "total": 4, "rate": 25.0})
        self.assertEqual(graduate["false_red"], {"count": 1, "total": 4, "rate": 25.0})
        self.assertEqual(graduate["false_green"], {"count": 1, "total": 4, "rate": 25.0})
        self.assertEqual(graduate["verify_first"], {"count": 0, "total": 4, "rate": 0.0})
        self.assertEqual(graduate["unknown"], {"count": 1, "total": 4, "rate": 25.0})
        self.assertEqual(report["evidence_extraction"]["matched_cases"], 3)
        self.assertEqual(report["evidence_extraction"]["cases_with_expected_evidence"], 4)
        self.assertEqual(report["evidence_extraction"]["accuracy"], 75.0)

    def test_overlapping_right_to_work_evidence_can_be_covered_by_stricter_signal(self):
        self.assertTrue(
            evidence_matches(
                [
                    {
                        "category": "no_sponsorship",
                        "text": "legal right to work in the UK without requiring visa sponsorship",
                    }
                ],
                [
                    {
                        "category": "ambiguous",
                        "text_contains": "legal right to work in the UK",
                    }
                ],
            )
        )

    def test_synthetic_edge_cases_are_executable_and_non_empty(self):
        """Synthetic fixture must produce classification results for all its records.

        This guards against the synthetic file being silently empty or schema-broken.
        The synthetic dataset is for rule-harness coverage only; do NOT mix its
        metrics with real-seed metrics in public claims.
        """
        dataset = load_dataset(SYNTHETIC_DATASET_PATH)
        # The synthetic flag must be present at the top level
        self.assertTrue(
            dataset.get("synthetic"),
            "synthetic_edge_cases.json must have top-level synthetic:true",
        )
        report = evaluate_dataset(dataset, self.matcher)
        # Must have records
        self.assertGreater(report["dataset"]["records"], 0, "Synthetic dataset has zero records")
        self.assertGreater(report["dataset"]["cases"], 0, "Synthetic dataset produced zero cases")
        # Both visa situations must be represented
        self.assertIn("graduate_route", report["by_visa_situation"])
        self.assertIn("needs_sponsorship_before_start", report["by_visa_situation"])
        # No false-green allowed even in synthetic cases
        graduate = report["by_visa_situation"]["graduate_route"]
        nss = report["by_visa_situation"]["needs_sponsorship_before_start"]
        self.assertEqual(graduate["false_green"]["count"], 0, "Synthetic: false-green in graduate_route")
        self.assertEqual(nss["false_green"]["count"], 0, "Synthetic: false-green in needs_sponsorship_before_start")

    def test_sponsor_failure_examples_are_reported(self):
        dataset = {
            "schema_version": 1,
            "name": "sponsor failure unit dataset",
            "records": [
                {
                    "eval_id": "sponsor:001",
                    "source": "manual",
                    "title": "Fixture mismatch",
                    "employer_raw": "Example Ltd",
                    "description_text": "Short excerpt with no visa claim.",
                    "eval_use": "classification_and_evidence",
                    "sponsor_match_expected": {
                        "available": True,
                        "is_match": False,
                        "matched_name": None,
                        "notes": "Intentional mismatch for reporting coverage.",
                    },
                    "cases": [
                        {
                            "case_id": "sponsor:001:graduate",
                            "user_context": {"visa_situation": "graduate_route"},
                            "expected_label": "unknown",
                            "expected_evidence": [],
                        }
                    ],
                }
            ],
        }

        with patch(
            "pipeline.eval.run_eval.analyse_job",
            return_value=_classification_output("unknown", []),
        ):
            report = evaluate_dataset(dataset, self.matcher)

        self.assertEqual(report["sponsor_matching"]["labelled_sponsor_precision"], 0.0)
        self.assertEqual(len(report["sponsor_matching"]["failure_case_examples"]), 1)
        self.assertIn("Sponsor label failure examples", format_report(report))


def _classification_output(label, evidence):
    return {
        "classification": {
            "label": label,
            "reason": "Mocked classifier output for metric calculation tests.",
            "evidence": evidence,
        }
    }


if __name__ == "__main__":
    unittest.main()
