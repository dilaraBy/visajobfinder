import { describe, it, expect } from "vitest";

import type { ClassificationResult } from "@/engine";
import type { Label } from "@/engine/types";
import type { PublicJob } from "./jobs";
import {
  DEFAULT_FILTERS,
  applyFilters,
  availableCategories,
  availableSources,
  filtersFromParams,
  hasActiveFilters,
  keywordScore,
  paramsWithFilters,
  parseKeywords,
  passesKeywords,
  toggleKeyword,
  type ClassifiedJob,
  type FilterState,
} from "./filters";

function job(overrides: Partial<PublicJob> = {}): PublicJob {
  return {
    job_id: "reed:1",
    source: "reed",
    title: "Graduate Analyst",
    employer_raw: "Octopus",
    description_text: "x",
    location: { raw: "London", city: "London", country: "UK", remote_type: "unknown" },
    salary: null,
    dates: { posted_at: "2026-06-01", closing_at: null, fetched_at: null },
    url: null,
    visa_signals: {
      employer_match: {
        raw: "Octopus",
        matched_name: null,
        confidence: 0,
        confidence_band: "none",
        match_method: null,
        sponsor_routes: [],
        rating: null,
        location: null,
        is_match: false,
        source_name: null,
        source_published_at: null,
        source_downloaded_at: null,
      },
      phrase_signals: [],
    },
    freshness: {
      posted_at: "2026-06-01",
      age_days: 9,
      has_posted_date: true,
      stale_after_days: 30,
      is_stale: false,
      needs_review: false,
    },
    ...overrides,
  };
}

function classified(label: Label, j: PublicJob): ClassifiedJob {
  const result: ClassificationResult = {
    job_id: j.job_id,
    label,
    reason: "",
    evidence: [],
    employer_match: j.visa_signals.employer_match,
    what_to_verify: [],
    limitations: [],
  };
  return { job: j, result };
}

describe("filtersFromParams", () => {
  it("returns defaults for an empty URL", () => {
    expect(filtersFromParams(new URLSearchParams())).toEqual(DEFAULT_FILTERS);
  });

  it("parses all supported filters", () => {
    const params = new URLSearchParams(
      "label=verify_first&source=reed&loc=London&fresh=stale&sort=posted_at_desc"
    );
    expect(filtersFromParams(params)).toEqual({
      label: "verify_first",
      source: "reed",
      location: "London",
      freshness: "stale",
      posted_within: "all",
      sort: "posted_at_desc",
      keyword: "",
    });
  });

  it("falls back when a param is unknown", () => {
    const params = new URLSearchParams("label=eligible&sort=random");
    const filters = filtersFromParams(params);
    expect(filters.label).toBe("all");
    expect(filters.sort).toBe("label_severity");
  });
});

describe("paramsWithFilters", () => {
  it("drops defaults so the URL stays clean", () => {
    const next = paramsWithFilters(new URLSearchParams("job=reed:1"), DEFAULT_FILTERS);
    expect(next.get("job")).toBe("reed:1");
    expect(next.get("label")).toBeNull();
    expect(next.get("sort")).toBeNull();
  });

  it("writes only non-default values", () => {
    const next = paramsWithFilters(new URLSearchParams(), {
      ...DEFAULT_FILTERS,
      label: "verify_first",
      location: "Manchester",
    });
    expect(next.get("label")).toBe("verify_first");
    expect(next.get("loc")).toBe("Manchester");
    expect(next.get("source")).toBeNull();
  });
});

describe("applyFilters", () => {
  const items: ClassifiedJob[] = [
    classified("likely_blocked", job({ job_id: "a", source: "reed", location: { raw: "London", city: "London", country: "UK", remote_type: null } })),
    classified("worth_applying", job({ job_id: "b", source: "adzuna", location: { raw: "Manchester", city: "Manchester", country: "UK", remote_type: null }, freshness: { posted_at: "2026-05-01", age_days: 40, has_posted_date: true, stale_after_days: 30, is_stale: true, needs_review: false } })),
    classified("verify_first", job({ job_id: "c", source: "reed", location: null, freshness: { posted_at: null, age_days: null, has_posted_date: false, stale_after_days: 30, is_stale: false, needs_review: true } })),
    classified("unknown", job({ job_id: "d", source: "lever", location: { raw: "Remote (UK)", city: null, country: "UK", remote_type: "remote" } })),
  ];

  it("filters by label", () => {
    const out = applyFilters(items, { ...DEFAULT_FILTERS, label: "verify_first" });
    expect(out.map((c) => c.job.job_id)).toEqual(["c"]);
  });

  it("filters by source", () => {
    const out = applyFilters(items, { ...DEFAULT_FILTERS, source: "reed" });
    expect(out.map((c) => c.job.job_id).sort()).toEqual(["a", "c"]);
  });

  it("case-insensitive location substring matches city/raw/country", () => {
    const out = applyFilters(items, { ...DEFAULT_FILTERS, location: "manch" });
    expect(out.map((c) => c.job.job_id)).toEqual(["b"]);
  });

  it("freshness=missing_date returns only jobs without posted dates", () => {
    const out = applyFilters(items, { ...DEFAULT_FILTERS, freshness: "missing_date" });
    expect(out.map((c) => c.job.job_id)).toEqual(["c"]);
  });

  it("freshness=stale returns only stale jobs", () => {
    const out = applyFilters(items, { ...DEFAULT_FILTERS, freshness: "stale" });
    expect(out.map((c) => c.job.job_id)).toEqual(["b"]);
  });

  it("posted_within=30 keeps only recent dated jobs and hides undated", () => {
    const out = applyFilters(items, { ...DEFAULT_FILTERS, posted_within: "30" });
    // a (9d) and d (9d) are within 30; b (40d) and c (undated) are excluded.
    expect(out.map((c) => c.job.job_id).sort()).toEqual(["a", "d"]);
  });

  it("posted_within=90 keeps the 40-day job but still hides undated", () => {
    const out = applyFilters(items, { ...DEFAULT_FILTERS, posted_within: "90" });
    expect(out.map((c) => c.job.job_id).sort()).toEqual(["a", "b", "d"]);
  });

  it("default sort surfaces likely_blocked over worth_applying", () => {
    const out = applyFilters(items, DEFAULT_FILTERS);
    expect(out[0].result.label).toBe("likely_blocked");
    expect(out[out.length - 1].result.label).toBe("worth_applying");
  });

  it("posted_at_desc puts undated jobs at the bottom", () => {
    const out = applyFilters(items, { ...DEFAULT_FILTERS, sort: "posted_at_desc" });
    expect(out[out.length - 1].job.job_id).toBe("c");
  });
});

describe("misc helpers", () => {
  it("availableSources returns sorted unique source ids", () => {
    const items: ClassifiedJob[] = [
      classified("worth_applying", job({ source: "reed" })),
      classified("worth_applying", job({ source: "adzuna" })),
      classified("worth_applying", job({ source: "reed" })),
    ];
    expect(availableSources(items)).toEqual(["adzuna", "reed"]);
  });

  it("hasActiveFilters ignores sort but counts keyword", () => {
    expect(hasActiveFilters(DEFAULT_FILTERS)).toBe(false);
    expect(
      hasActiveFilters({ ...DEFAULT_FILTERS, sort: "posted_at_desc" })
    ).toBe(false);
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, label: "verify_first" })).toBe(true);
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, location: "x" })).toBe(true);
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, keyword: "psychology" })).toBe(true);
  });

  it("availableCategories returns sorted unique categories, ignoring missing", () => {
    const items: ClassifiedJob[] = [
      classified("worth_applying", job({ category: "psychology graduate" })),
      classified("worth_applying", job({ category: "finance graduate" })),
      classified("worth_applying", job({ category: "psychology graduate" })),
      classified("worth_applying", job({ category: null })),
      classified("worth_applying", job({})),
    ];
    expect(availableCategories(items)).toEqual([
      "finance graduate",
      "psychology graduate",
    ]);
  });
});

describe("keyword matching", () => {
  it("parseKeywords splits on commas into trimmed lowercase phrases", () => {
    expect(parseKeywords("Psychology Graduate, Finance ,, data analyst")).toEqual([
      "psychology graduate",
      "finance",
      "data analyst",
    ]);
    expect(parseKeywords("   ")).toEqual([]);
  });

  it("passesKeywords is OR over phrases and true when empty", () => {
    const j = job({ title: "Psychology Graduate", category: "psychology graduate" });
    expect(passesKeywords(j, [])).toBe(true);
    expect(passesKeywords(j, ["psychology graduate"])).toBe(true);
    expect(passesKeywords(j, ["finance"])).toBe(false);
    expect(passesKeywords(j, ["finance", "psychology graduate"])).toBe(true);
  });

  it("keywordScore weights title over category over body", () => {
    const titleHit = job({ title: "Data Analyst", category: "x", description_text: "y" });
    const categoryHit = job({ title: "Analyst", category: "data analyst", description_text: "y" });
    const bodyHit = job({ title: "Analyst", category: "x", description_text: "data analyst role" });
    expect(keywordScore(titleHit, ["data analyst"])).toBe(3);
    expect(keywordScore(categoryHit, ["data analyst"])).toBe(2);
    expect(keywordScore(bodyHit, ["data analyst"])).toBe(1);
  });

  it("toggleKeyword adds and removes a phrase", () => {
    expect(toggleKeyword("", "psychology graduate")).toBe("psychology graduate");
    expect(toggleKeyword("psychology graduate", "psychology graduate")).toBe("");
    expect(toggleKeyword("finance", "psychology graduate")).toBe(
      "finance, psychology graduate"
    );
  });

  it("applyFilters filters to matches and ranks stronger matches first", () => {
    const items: ClassifiedJob[] = [
      // worth_applying but only a body match (weak)
      classified(
        "worth_applying",
        job({ job_id: "weak", title: "Analyst", category: "x", description_text: "psychology team" })
      ),
      // likely_blocked with a title match (strong) — ranks first despite severity
      classified(
        "likely_blocked",
        job({ job_id: "strong", title: "Psychology Graduate", category: "psychology graduate", description_text: "z" })
      ),
      // no match at all — filtered out
      classified("verify_first", job({ job_id: "none", title: "Finance", category: "finance", description_text: "z" })),
    ];
    const out = applyFilters(items, { ...DEFAULT_FILTERS, keyword: "psychology" });
    expect(out.map((c) => c.job.job_id)).toEqual(["strong", "weak"]);
  });

  it("empty keyword leaves ordering identical to no keyword", () => {
    const items: ClassifiedJob[] = [
      classified("worth_applying", job({ job_id: "b" })),
      classified("likely_blocked", job({ job_id: "a" })),
    ];
    const withEmpty = applyFilters(items, { ...DEFAULT_FILTERS, keyword: "" });
    const without = applyFilters(items, DEFAULT_FILTERS);
    expect(withEmpty.map((c) => c.job.job_id)).toEqual(without.map((c) => c.job.job_id));
  });
});

describe("paramsWithFilters round-trips", () => {
  it("filtersFromParams ∘ paramsWithFilters is identity on non-default values", () => {
    const target: FilterState = {
      label: "verify_first",
      source: "reed",
      location: "London",
      freshness: "stale",
      posted_within: "90",
      sort: "posted_at_desc",
      keyword: "data analyst, finance",
    };
    const params = paramsWithFilters(new URLSearchParams(), target);
    expect(params.get("q")).toBe("data analyst, finance");
    expect(filtersFromParams(params)).toEqual(target);
  });

  it("drops an empty keyword from the URL", () => {
    const next = paramsWithFilters(new URLSearchParams("q=psychology"), DEFAULT_FILTERS);
    expect(next.get("q")).toBeNull();
  });
});
