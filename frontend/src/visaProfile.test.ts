import { describe, it, expect } from "vitest";

import {
  DEFAULT_VISA_PROFILE,
  userContextFromProfile,
} from "./visaProfile";

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
