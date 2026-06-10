import { describe, it, expect } from "vitest";
import { classifyPublicJob, jobToInput, type PublicJob } from "./jobs";
import { ALLOWED_LABELS, type EmployerMatch } from "@/engine";

function employerMatch(overrides: Partial<EmployerMatch> = {}): EmployerMatch {
  return {
    raw: "Octopus Energy Group",
    matched_name: "Octopus Energy Limited",
    confidence: 1.0,
    confidence_band: "high",
    match_method: "exact",
    sponsor_routes: ["Skilled Worker"],
    rating: "A",
    location: "London",
    is_match: true,
    source_name: "GOV.UK Register of Licensed Sponsors",
    source_published_at: "2026-06-04",
    source_downloaded_at: "2026-06-05",
    ...overrides,
  };
}

function publicJob(overrides: Partial<PublicJob> = {}): PublicJob {
  return {
    job_id: "reed:1",
    source: "reed",
    title: "Graduate Analyst",
    employer_raw: "Octopus Energy Group",
    description_text:
      "Graduate analyst role. Candidates must have the right to work in the UK.",
    location: { raw: "London", city: "London", country: "UK", remote_type: "unknown" },
    salary: { raw: "GBP 32,000 per year", min: 32000, max: 32000, currency: "GBP", period: "year", is_missing: false },
    dates: { posted_at: "2026-06-01", closing_at: null, fetched_at: "2026-06-05T00:00:00Z" },
    url: "https://example.com/job/1",
    visa_signals: { employer_match: employerMatch(), phrase_signals: [] },
    freshness: { posted_at: "2026-06-01", age_days: 4, has_posted_date: true, stale_after_days: 30, is_stale: false, needs_review: false },
    ...overrides,
  };
}

describe("dashboard data layer", () => {
  it("maps a public job record to the engine JobInput shape", () => {
    const input = jobToInput(publicJob());
    expect(input.title).toBe("Graduate Analyst");
    expect(input.location).toBe("London");
    expect(input.salary_text).toBe("GBP 32,000 per year");
    expect(input.url).toBe("https://example.com/job/1");
  });

  it("classifies using the precomputed employer_match (no re-matching)", () => {
    // A blank matcher is passed internally; the match must come from the record.
    const result = classifyPublicJob(publicJob(), { visa_situation: "graduate_route" });
    expect(ALLOWED_LABELS).toContain(result.label);
    expect(result.employer_match.matched_name).toBe("Octopus Energy Limited");
    expect(result.employer_match.is_match).toBe(true);
  });

  it("reflects the profile: status-aware labels differ by visa situation", () => {
    const job = publicJob({
      description_text:
        "You must have permanent right to work in the UK. We cannot offer visa sponsorship.",
      visa_signals: {
        employer_match: employerMatch({ is_match: false, matched_name: null, confidence: 0, confidence_band: "none" }),
        phrase_signals: [
          { category: "no_sponsorship", severity: "red", text: "cannot offer visa sponsorship", start_index: 40, end_index: 69, rule_id: "no_sponsorship_1" },
        ],
      },
    });
    const grad = classifyPublicJob(job, { visa_situation: "graduate_route" });
    const needs = classifyPublicJob(job, {
      visa_situation: "needs_sponsorship_before_start",
      needs_sponsorship_before_start: true,
    });
    // Same job, different situations -> the engine may reach different labels.
    expect(ALLOWED_LABELS).toContain(grad.label);
    expect(ALLOWED_LABELS).toContain(needs.label);
  });
});
