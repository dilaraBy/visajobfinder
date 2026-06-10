from pathlib import Path
import tempfile
import unittest
from unittest import mock

from pipeline.build_jobs import adapter_from_spec, build_public_jobs
from pipeline.sources import AdzunaAdapter, ReedAdapter
from pipeline.sources.env_file import load_env_file, parse_env_text
from pipeline.sources.freshness import (
    compute_age_days,
    freshness_for,
    summarise_freshness,
)
from pipeline.sources import link_check


ROOT = Path(__file__).resolve().parents[1]
SPONSOR_PATH = ROOT / "data" / "sponsor_register" / "sample_sponsors.csv"
DATA_SOURCES = ROOT / "data" / "sources"
RUN_AT = "2026-06-04T09:00:00Z"


class EnvFileTest(unittest.TestCase):
    def test_parse_handles_comments_quotes_and_export(self):
        values = parse_env_text(
            "\n".join(
                [
                    "# comment",
                    "",
                    "REED_API_KEY=abc123",
                    'ADZUNA_APP_ID="quoted-id"',
                    "export ADZUNA_APP_KEY='single'",
                    "NOT_A_PAIR",
                ]
            )
        )
        self.assertEqual(values["REED_API_KEY"], "abc123")
        self.assertEqual(values["ADZUNA_APP_ID"], "quoted-id")
        self.assertEqual(values["ADZUNA_APP_KEY"], "single")
        self.assertNotIn("NOT_A_PAIR", values)

    def test_load_does_not_override_existing_env_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("REED_API_KEY=from_file\nADZUNA_APP_ID=file_id\n", encoding="utf-8")
            environ = {"REED_API_KEY": "from_shell"}
            applied = load_env_file(path, environ=environ)

            self.assertEqual(environ["REED_API_KEY"], "from_shell")  # shell wins
            self.assertEqual(environ["ADZUNA_APP_ID"], "file_id")
            self.assertIn("ADZUNA_APP_ID", applied)
            self.assertNotIn("REED_API_KEY", applied)

    def test_missing_file_is_not_an_error(self):
        self.assertEqual(load_env_file(Path("does-not-exist.env"), environ={}), {})


class FreshnessTest(unittest.TestCase):
    def test_compute_age_days(self):
        self.assertEqual(compute_age_days("2026-05-05", RUN_AT), 30)
        self.assertIsNone(compute_age_days(None, RUN_AT))
        self.assertIsNone(compute_age_days("not-a-date", RUN_AT))
        # Future posted date is clamped to 0 (clock/source skew, not fresh-future).
        self.assertEqual(compute_age_days("2026-07-01", RUN_AT), 0)

    def test_freshness_flags(self):
        fresh = freshness_for("2026-06-01", RUN_AT, stale_after_days=30)
        self.assertTrue(fresh["has_posted_date"])
        self.assertFalse(fresh["is_stale"])
        self.assertFalse(fresh["needs_review"])

        stale = freshness_for("2026-01-01", RUN_AT, stale_after_days=30)
        self.assertTrue(stale["is_stale"])

        undated = freshness_for(None, RUN_AT)
        self.assertFalse(undated["has_posted_date"])
        self.assertFalse(undated["is_stale"])
        self.assertTrue(undated["needs_review"])

    def test_summarise(self):
        jobs = [
            {"freshness": freshness_for("2026-06-01", RUN_AT)},
            {"freshness": freshness_for("2026-01-01", RUN_AT)},
            {"freshness": freshness_for(None, RUN_AT)},
        ]
        summary = summarise_freshness(jobs)
        self.assertEqual(summary, {"total": 3, "fresh": 1, "stale": 1, "missing_date": 1})


class _FakeResponse:
    def __init__(self, status):
        self.status = status

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class LinkCheckTest(unittest.TestCase):
    def test_ok_link(self):
        with mock.patch.object(
            link_check.urllib.request, "urlopen", return_value=_FakeResponse(200)
        ):
            result = link_check.check_url("https://example.com/job")
        self.assertTrue(result["ok"])
        self.assertEqual(result["status_code"], 200)

    def test_missing_url(self):
        result = link_check.check_url("")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "missing_url")

    def test_head_rejected_falls_back_to_get(self):
        import urllib.error

        def fake_urlopen(request, timeout=10):
            if request.get_method() == "HEAD":
                raise urllib.error.HTTPError(request.full_url, 405, "no head", {}, None)
            return _FakeResponse(200)

        with mock.patch.object(link_check.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = link_check.check_url("https://example.com/job")
        self.assertTrue(result["ok"])

    def test_summarise_links(self):
        jobs = [
            {"link_status": {"ok": True}},
            {"link_status": {"ok": False}},
            {"no": "status"},
        ]
        self.assertEqual(link_check.summarise_links(jobs), {"checked": 2, "ok": 1, "dead": 1})


class AdapterResultsKnobTest(unittest.TestCase):
    def test_results_knob_caps_per_source(self):
        reed = adapter_from_spec("reed:live", results=500)
        adzuna = adapter_from_spec("adzuna:live", results=500)
        self.assertEqual(reed.results_to_take, 100)  # capped
        self.assertEqual(adzuna.results_per_page, 50)  # capped

    def test_live_reed_maps_records_with_mocked_network(self):
        payload = {
            "results": [
                {
                    "jobId": 555,
                    "jobTitle": "Graduate Data Analyst",
                    "employerName": "Example Ltd",
                    "jobDescription": "Visa sponsorship available for the right candidate.",
                    "locationName": "London",
                    "minimumSalary": 32000,
                    "maximumSalary": 38000,
                    "date": "2026-06-01",
                    "jobUrl": "https://www.reed.co.uk/jobs/555",
                }
            ]
        }
        adapter = ReedAdapter(mode="live", env={"REED_API_KEY": "test-key"})
        with mock.patch("pipeline.sources.adapters._fetch_json", return_value=payload):
            jobs, run = adapter.fetch_jobs(RUN_AT)
        self.assertEqual(run.status, "ok")
        self.assertEqual(jobs[0].employer_raw, "Example Ltd")
        self.assertEqual(jobs[0].salary_min, 32000)


class BuildIntegrationTest(unittest.TestCase):
    def test_build_includes_freshness_summary_and_per_job_block(self):
        output = build_public_jobs(
            source_files=[DATA_SOURCES / "sample_jobs.json"],
            sponsor_register_path=SPONSOR_PATH,
            generated_at=RUN_AT,
        )
        self.assertIn("freshness_summary", output)
        self.assertEqual(
            output["freshness_summary"]["total"], len(output["jobs"])
        )
        self.assertTrue(all("freshness" in job for job in output["jobs"]))
        self.assertNotIn("link_summary", output)  # link checking off by default

    def test_build_with_link_checker_injected(self):
        calls = []

        def fake_checker(url):
            calls.append(url)
            return {"url": url, "ok": True, "status_code": 200, "error": None}

        output = build_public_jobs(
            source_files=[DATA_SOURCES / "sample_jobs.json"],
            sponsor_register_path=SPONSOR_PATH,
            generated_at=RUN_AT,
            link_checker=fake_checker,
        )
        self.assertIn("link_summary", output)
        self.assertEqual(output["link_summary"]["checked"], len(output["jobs"]))
        self.assertTrue(all("link_status" in job for job in output["jobs"]))
        self.assertEqual(len(calls), len(output["jobs"]))


if __name__ == "__main__":
    unittest.main()
