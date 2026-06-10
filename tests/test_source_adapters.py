from pathlib import Path
import unittest

from pipeline.build_jobs import build_public_jobs
from pipeline.classifier.models import JobInput
from pipeline.sources import AdzunaAdapter, GreenhouseAdapter, LeverAdapter, ReedAdapter, SourceAdapter
from pipeline.sources.adapters import _iso_date


ROOT = Path(__file__).resolve().parents[1]
DATA_SOURCES = ROOT / "data" / "sources"
SPONSOR_PATH = ROOT / "data" / "sponsor_register" / "sample_sponsors.csv"


def _fetch(adapter: SourceAdapter):
    return adapter.fetch_jobs("2026-06-04T09:00:00Z")


class IsoDateTest(unittest.TestCase):
    def test_iso_date_passes_through(self):
        self.assertEqual(_iso_date("2026-06-03"), "2026-06-03")

    def test_iso_timestamp_is_truncated(self):
        self.assertEqual(_iso_date("2026-06-04T08:00:00Z"), "2026-06-04")

    def test_uk_day_first_format_is_converted(self):
        self.assertEqual(_iso_date("04/06/2026"), "2026-06-04")

    def test_invalid_uk_date_becomes_none(self):
        self.assertIsNone(_iso_date("31/02/2026"))

    def test_invalid_iso_date_becomes_none(self):
        self.assertIsNone(_iso_date("2026-13-40"))

    def test_unparseable_text_becomes_none(self):
        self.assertIsNone(_iso_date("yesterday"))
        self.assertIsNone(_iso_date(""))
        self.assertIsNone(_iso_date(None))


class SourceAdapterTest(unittest.TestCase):
    def test_reed_fixture_normalises_to_job_input(self):
        jobs, run = _fetch(ReedAdapter(fixture_path=DATA_SOURCES / "reed_fixture.json"))

        self.assertEqual(run.status, "ok")
        self.assertEqual(run.fetched_count, 1)
        self.assertEqual(run.normalised_count, 1)
        self.assertIsInstance(jobs[0], JobInput)
        self.assertEqual(jobs[0].job_id, "reed:10001")
        self.assertEqual(jobs[0].employer_raw, "Northbridge Analytics")
        self.assertEqual(jobs[0].salary_min, 33000)
        self.assertNotIn("<p>", jobs[0].description_text)
        self.assertIn("Visa sponsorship may be available", jobs[0].description_text)
        # The live Reed API returns DD/MM/YYYY; the fixture mirrors that shape
        # so a format regression cannot pass the suite silently again.
        self.assertEqual(jobs[0].posted_at, "2026-06-04")
        self.assertEqual(jobs[0].closing_at, "2026-07-04")

    def test_adzuna_fixture_normalises_to_job_input(self):
        jobs, run = _fetch(AdzunaAdapter(fixture_path=DATA_SOURCES / "adzuna_fixture.json"))

        self.assertEqual(run.status, "ok")
        self.assertEqual(jobs[0].job_id, "adzuna:adz-20001")
        self.assertEqual(jobs[0].employer_raw, "Example Ltd")
        self.assertEqual(jobs[0].location, "Manchester")
        self.assertEqual(jobs[0].posted_at, "2026-06-03")

    def test_greenhouse_fixture_parses_public_board_shape(self):
        jobs, run = _fetch(
            GreenhouseAdapter(
                fixture_path=DATA_SOURCES / "greenhouse_fixture.json",
                employer_name="CareWorks Group",
            )
        )

        self.assertEqual(run.status, "ok")
        self.assertEqual(jobs[0].job_id, "greenhouse:30001")
        self.assertEqual(jobs[0].title, "Graduate Software Engineer")
        self.assertEqual(jobs[0].location, "Birmingham")
        self.assertIn("SC clearance", jobs[0].description_text)
        self.assertNotIn("<div>", jobs[0].description_text)

    def test_lever_fixture_parses_public_board_shape(self):
        jobs, run = _fetch(
            LeverAdapter(
                fixture_path=DATA_SOURCES / "lever_fixture.json",
                employer_name="NoSponsor Solutions",
            )
        )

        self.assertEqual(run.status, "ok")
        self.assertEqual(jobs[0].job_id, "lever:lev-40001")
        self.assertEqual(jobs[0].title, "Operations Graduate Scheme")
        self.assertEqual(jobs[0].location, "Leeds")
        self.assertEqual(jobs[0].posted_at, "2026-06-02")
        self.assertIn("cannot provide visa sponsorship", jobs[0].description_text)

    def test_reed_live_mode_reports_missing_credentials_as_source_run_error(self):
        jobs, run = ReedAdapter(mode="live", env={}).fetch_jobs("2026-06-04T09:00:00Z")

        self.assertEqual(jobs, [])
        self.assertEqual(run.status, "error")
        self.assertEqual(run.fetched_count, 0)
        self.assertIn("REED_API_KEY", run.error or "")
        self.assertIn("fixture mode", run.error or "")

    def test_adzuna_live_mode_reports_missing_credentials_as_source_run_error(self):
        jobs, run = AdzunaAdapter(mode="live", env={}).fetch_jobs("2026-06-04T09:00:00Z")

        self.assertEqual(jobs, [])
        self.assertEqual(run.status, "error")
        self.assertIn("ADZUNA_APP_ID", run.error or "")
        self.assertIn("ADZUNA_APP_KEY", run.error or "")
        self.assertIn("fixture mode", run.error or "")

    def test_public_build_keeps_description_scope_as_excerpt(self):
        output = build_public_jobs(
            source_files=[DATA_SOURCES / "sample_jobs.json"],
            sponsor_register_path=SPONSOR_PATH,
            generated_at="2026-06-04T09:00:00Z",
        )

        self.assertTrue(output["jobs"])
        self.assertTrue(all(job["description_scope"] == "excerpt" for job in output["jobs"]))
        self.assertTrue(
            all(
                "Only a description excerpt was stored" in " ".join(job["visa_signals"]["base_limitations"])
                for job in output["jobs"]
            )
        )


if __name__ == "__main__":
    unittest.main()
