from pathlib import Path
import tempfile
import unittest

from pipeline.build_jobs import (
    adapter_from_spec,
    build_public_jobs,
    main,
    normalise_source_file,
    write_public_jobs,
)
from pipeline.sources import AdzunaAdapter, GreenhouseAdapter, ReedAdapter
from pipeline.sources.dedupe import dedupe_jobs
from pipeline.sources.normalise import normalise_raw_job


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "sources" / "sample_jobs.json"
SPONSOR_PATH = ROOT / "data" / "sponsor_register" / "sample_sponsors.csv"


class BuildJobsTest(unittest.TestCase):
    def test_normalise_raw_job_sets_contract_fields(self):
        job = normalise_raw_job(
            {
                "source": "sample",
                "source_job_id": "123",
                "title": " Graduate Analyst ",
                "employer_raw": "Example Ltd",
                "description_text": "Visa sponsorship available.",
                "location": "London",
                "salary_text": "GBP 32,000",
            },
            fetched_at="2026-06-04T09:00:00Z",
        )

        self.assertEqual(job.job_id, "sample:123")
        self.assertEqual(job.source_job_id, "123")
        self.assertEqual(job.fetched_at, "2026-06-04T09:00:00Z")
        self.assertEqual(job.title, "Graduate Analyst")

    def test_normalise_raw_job_excerpt_limits_public_description_text(self):
        job = normalise_raw_job(
            {
                "source": "sample",
                "source_job_id": "long",
                "title": "Graduate Analyst",
                "employer_raw": "Example Ltd",
                "description_text": " ".join(["visa wording"] * 120),
            },
            fetched_at="2026-06-04T09:00:00Z",
        )

        self.assertLessEqual(len(job.description_text), 703)
        self.assertTrue(job.description_text.endswith("..."))

    def test_dedupe_jobs_keeps_first_matching_listing(self):
        jobs, source_run = normalise_source_file(SOURCE_PATH, "2026-06-04T09:00:00Z")

        self.assertEqual(source_run.fetched_count, 5)
        self.assertEqual(source_run.normalised_count, 5)
        deduped = dedupe_jobs(jobs)

        self.assertEqual(len(deduped), 4)
        self.assertEqual(deduped[2].source_job_id, "grad-consultant-001")

    def test_build_public_jobs_matches_data_contract_shape(self):
        output = build_public_jobs(
            source_files=[SOURCE_PATH],
            sponsor_register_path=SPONSOR_PATH,
            generated_at="2026-06-04T09:00:00Z",
        )

        self.assertEqual(output["generated_at"], "2026-06-04T09:00:00Z")
        self.assertEqual(output["source_runs"][0]["status"], "ok")
        self.assertEqual(output["source_runs"][0]["fetched_count"], 5)
        self.assertEqual(len(output["jobs"]), 4)

        first = output["jobs"][0]
        self.assertEqual(first["job_id"], "sample:grad-marketing-001")
        self.assertEqual(first["source_job_id"], "grad-marketing-001")
        self.assertIn("description_hash", first)
        self.assertEqual(first["description_scope"], "excerpt")
        self.assertIn("location", first)
        self.assertIn("salary", first)
        self.assertIn("visa_signals", first)
        self.assertEqual(first["dates"]["fetched_at"], "2026-06-04T09:00:00Z")
        self.assertTrue(first["visa_signals"]["phrase_signals"])
        self.assertIn(
            "Only a description excerpt was stored",
            " ".join(first["visa_signals"]["base_limitations"]),
        )

    def test_build_public_jobs_accepts_source_adapters(self):
        output = build_public_jobs(
            source_files=[],
            sponsor_register_path=SPONSOR_PATH,
            generated_at="2026-06-04T09:00:00Z",
            adapters=[
                GreenhouseAdapter(
                    fixture_path=ROOT / "data" / "sources" / "greenhouse_fixture.json",
                    employer_name="CareWorks Group",
                )
            ],
        )

        self.assertEqual(output["source_runs"][0]["source"], "greenhouse")
        self.assertEqual(output["source_runs"][0]["status"], "ok")
        self.assertEqual(len(output["jobs"]), 1)
        self.assertEqual(output["jobs"][0]["description_scope"], "excerpt")

    def test_partial_adapter_failure_does_not_break_public_build(self):
        output = build_public_jobs(
            source_files=[],
            sponsor_register_path=SPONSOR_PATH,
            generated_at="2026-06-04T09:00:00Z",
            adapters=[
                ReedAdapter(fixture_path=ROOT / "data" / "sources" / "reed_fixture.json"),
                AdzunaAdapter(mode="live", env={}),
            ],
        )

        self.assertEqual(len(output["source_runs"]), 2)
        self.assertEqual(output["source_runs"][1]["status"], "error")
        self.assertIn("ADZUNA_APP_ID", output["source_runs"][1]["error"])
        self.assertEqual(len(output["jobs"]), 1)

    def test_adapter_from_spec_parses_fixture_and_live_modes(self):
        fixture_adapter = adapter_from_spec(
            r"greenhouse:fixture:data\sources\greenhouse_fixture.json"
        )
        live_adapter = adapter_from_spec("reed:live")

        self.assertIsInstance(fixture_adapter, GreenhouseAdapter)
        self.assertEqual(fixture_adapter.mode, "fixture")
        self.assertEqual(fixture_adapter.fixture_path, Path(r"data\sources\greenhouse_fixture.json"))
        self.assertIsInstance(live_adapter, ReedAdapter)
        self.assertEqual(live_adapter.mode, "live")

    def test_min_jobs_guard_refuses_to_write_empty_dataset(self):
        # A total source wipe-out (e.g. all live fetches 401) must not publish
        # an empty jobs.json over the last good snapshot.
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "jobs.json"
            exit_code = main(
                [
                    "--source-file", str(Path(temp_dir) / "does_not_exist.json"),
                    "--sponsor-register", str(SPONSOR_PATH),
                    "--output", str(output_path),
                    "--min-jobs", "1",
                ]
            )
            self.assertEqual(exit_code, 1)
            self.assertFalse(output_path.exists())

    def test_zero_jobs_still_written_without_min_jobs_guard(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "jobs.json"
            exit_code = main(
                [
                    "--source-file", str(Path(temp_dir) / "does_not_exist.json"),
                    "--sponsor-register", str(SPONSOR_PATH),
                    "--output", str(output_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())

    def test_write_public_jobs_creates_json_file(self):
        output = build_public_jobs(
            source_files=[SOURCE_PATH],
            sponsor_register_path=SPONSOR_PATH,
            generated_at="2026-06-04T09:00:00Z",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "jobs.json"
            write_public_jobs(output, path)

            self.assertTrue(path.exists())
            self.assertIn('"jobs"', path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
