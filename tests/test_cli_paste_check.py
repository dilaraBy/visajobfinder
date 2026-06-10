import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from pipeline.cli import paste_check


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "sponsor_register" / "sample_sponsors.csv"
)


class PasteCheckCliTest(unittest.TestCase):
    def run_cli(self, *args):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = paste_check.main(
                [
                    *args,
                    "--sponsor-register",
                    str(FIXTURE_PATH),
                ]
            )
        return status, stdout.getvalue()

    def test_default_output_includes_json_and_human_summary(self):
        status, output = self.run_cli(
            "--title",
            "Graduate Analyst",
            "--employer",
            "Example Ltd",
            "--description",
            "Candidates must have the right to work in the UK without sponsorship.",
            "--visa-situation",
            "needs_sponsorship_before_start",
            "--location",
            "London",
            "--salary",
            "GBP 32,000 per year",
        )

        self.assertEqual(status, 0)
        json_part, summary = output.split("\n\nSummary\n", 1)
        payload = json.loads(json_part)

        self.assertEqual(payload["classification"]["label"], "likely_blocked")
        self.assertEqual(payload["job"]["location"]["raw"], "London")
        self.assertEqual(payload["job"]["salary"]["raw"], "GBP 32,000 per year")
        self.assertIn("Label: likely_blocked", summary)
        self.assertIn("Employer match: Example UK Limited", summary)
        self.assertIn("What to verify:", summary)
        self.assertIn("Limitations:", summary)

    def test_json_output_mode_is_parseable_without_summary(self):
        status, output = self.run_cli(
            "--title",
            "Graduate Analyst",
            "--employer",
            "Example Ltd",
            "--description",
            "Visa sponsorship available for suitable candidates.",
            "--visa-situation",
            "needs_sponsorship_before_start",
            "--salary",
            "GBP 35,000 per year",
            "--output",
            "json",
        )

        self.assertEqual(status, 0)
        payload = json.loads(output)
        self.assertEqual(payload["classification"]["label"], "worth_applying")
        self.assertNotIn("Summary", output)

    def test_description_file_is_accepted(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("We cannot provide visa sponsorship for this role.")
            description_path = handle.name

        try:
            status, output = self.run_cli(
                "--title",
                "Graduate Analyst",
                "--employer",
                "Example Ltd",
                "--description-file",
                description_path,
                "--visa-situation",
                "graduate_route",
                "--needs-future-sponsorship",
                "--output",
                "summary",
            )
        finally:
            Path(description_path).unlink(missing_ok=True)

        self.assertEqual(status, 0)
        self.assertTrue(output.startswith("Summary\n"))
        self.assertIn("Label: verify_first", output)
        self.assertIn("cannot provide visa sponsorship", output)


if __name__ == "__main__":
    unittest.main()
