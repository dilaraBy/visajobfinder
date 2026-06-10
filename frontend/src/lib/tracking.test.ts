import { describe, it, expect } from "vitest";

import {
  buildExport,
  parseImport,
  sanitiseEntry,
  withEntry,
  type TrackingState,
} from "./tracking";
import { DEFAULT_VISA_PROFILE } from "@/visaProfile";

describe("sanitiseEntry", () => {
  it("accepts a well-formed entry", () => {
    const entry = sanitiseEntry({
      status: "applied",
      note: "called recruiter",
      deadline: "2026-07-01",
      updated_at: "2026-06-10T10:00:00.000Z",
    });
    expect(entry).toMatchObject({
      status: "applied",
      note: "called recruiter",
      deadline: "2026-07-01",
    });
  });

  it("drops unknown statuses", () => {
    expect(sanitiseEntry({ status: "ghosted", note: "n" })).toMatchObject({
      status: null,
      note: "n",
    });
  });

  it("rejects deadlines that are not YYYY-MM-DD", () => {
    expect(sanitiseEntry({ status: "interested", deadline: "2026/07/01" })).toMatchObject({
      status: "interested",
      deadline: "",
    });
  });

  it("returns null for entries with no useful content", () => {
    expect(sanitiseEntry({ status: null, note: "", deadline: "" })).toBeNull();
    expect(sanitiseEntry(null)).toBeNull();
  });
});

describe("withEntry", () => {
  it("adds a new entry", () => {
    const next = withEntry({}, "reed:1", { status: "applied" });
    expect(next["reed:1"].status).toBe("applied");
    expect(next["reed:1"].updated_at).not.toBe("");
  });

  it("removes an entry when all fields become empty", () => {
    const start: TrackingState = {
      "reed:1": { status: "applied", note: "x", deadline: "", updated_at: "t" },
    };
    const next = withEntry(start, "reed:1", { status: null, note: "" });
    expect(next["reed:1"]).toBeUndefined();
  });
});

describe("buildExport / parseImport round-trip", () => {
  const tracking: TrackingState = {
    "reed:1": {
      status: "applied",
      note: "first stage",
      deadline: "2026-07-01",
      updated_at: "2026-06-10T10:00:00.000Z",
    },
  };
  const profile = {
    ...DEFAULT_VISA_PROFILE,
    visa_situation: "graduate_route" as const,
    visa_expiry_month: "2026-09",
  };

  it("round-trips profile and tracking", () => {
    const file = buildExport(profile, tracking);
    const parsed = parseImport(JSON.stringify(file));
    expect(parsed.profile).toEqual(profile);
    expect(parsed.tracking).toEqual(tracking);
    expect(parsed.summary.errors).toEqual([]);
    expect(parsed.summary.profileImported).toBe(true);
    expect(parsed.summary.trackedJobs).toBe(1);
  });

  it("flags non-VisaJobFinder JSON but still imports recognisable fields", () => {
    const parsed = parseImport(
      JSON.stringify({ visa_profile: profile, tracking })
    );
    expect(parsed.summary.errors.length).toBeGreaterThan(0);
    expect(parsed.profile).toEqual(profile);
    expect(parsed.tracking).toEqual(tracking);
  });

  it("reports a parse error for bad JSON", () => {
    const parsed = parseImport("not json");
    expect(parsed.summary.errors[0]).toMatch(/JSON/);
    expect(parsed.profile).toBeNull();
    expect(parsed.tracking).toEqual({});
  });

  it("silently drops malformed tracking entries", () => {
    const parsed = parseImport(
      JSON.stringify({
        app: "visajobfinder",
        version: 1,
        exported_at: "x",
        visa_profile: profile,
        tracking: {
          "reed:1": { status: "applied", deadline: "garbage", updated_at: "t" },
          "reed:2": "not an object",
          "reed:3": { status: null, note: "", deadline: "" }, // empty
        },
      })
    );
    expect(Object.keys(parsed.tracking)).toEqual(["reed:1"]);
    expect(parsed.tracking["reed:1"].deadline).toBe("");
  });
});
