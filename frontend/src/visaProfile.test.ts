import { describe, it, expect } from "vitest";

import {
  DEFAULT_VISA_PROFILE,
  userContextFromProfile,
} from "./visaProfile";

describe("legacy profile compatibility", () => {
  it("merging a profile saved before target_keywords existed yields a usable array", () => {
    // Simulates a returning visitor whose stored localStorage profile predates
    // the target_keywords field. The dashboard merges over defaults so reads
    // like profile.target_keywords.length can never crash.
    const legacy = {
      visa_situation: "graduate_route",
      needs_sponsorship_before_start: false,
      needs_future_sponsorship: false,
      visa_expiry_month: "",
      target_start_month: "",
    } as unknown as Partial<typeof DEFAULT_VISA_PROFILE>;
    const merged = { ...DEFAULT_VISA_PROFILE, ...legacy };
    expect(Array.isArray(merged.target_keywords)).toBe(true);
    expect(merged.target_keywords.length).toBe(0);
  });
});

describe("userContextFromProfile", () => {
  it("never leaks job interests into the visa context (engine parity guard)", () => {
    const withoutKeywords = userContextFromProfile({
      ...DEFAULT_VISA_PROFILE,
      visa_situation: "graduate_route",
    });
    const withKeywords = userContextFromProfile({
      ...DEFAULT_VISA_PROFILE,
      visa_situation: "graduate_route",
      target_keywords: ["psychology graduate", "finance"],
    });
    // target_keywords must not appear in, or otherwise change, the UserContext.
    expect(withKeywords).toEqual(withoutKeywords);
    expect("target_keywords" in withKeywords).toBe(false);
  });
});
