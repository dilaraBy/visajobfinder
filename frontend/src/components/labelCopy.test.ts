/**
 * Tests for label copy mapping.
 * Asserts:
 *  - every label maps to the exact headings specified in CLAUDE.md
 *  - forbidden strings never appear in any label copy
 */
import { describe, it, expect } from "vitest";
import { LABEL_DISPLAY } from "../labelCopy";
import type { Label } from "../engine/types";
import { ALLOWED_LABELS } from "../engine/types";

// Strings that must NEVER appear in rendered label copy (CLAUDE.md Product Truth).
const FORBIDDEN_STRINGS = [
  "you are eligible",
  "you can apply",
  "this role is safe",
  "will sponsor",
  "this company will sponsor",
  "this replaces immigration advice",
  "eligible",
  "safe",
  "can apply",
  "guaranteed",
  "visa approved",
];

describe("LABEL_DISPLAY copy mapping", () => {
  it("covers every allowed label", () => {
    const covered = Object.keys(LABEL_DISPLAY) as Label[];
    expect(covered.sort()).toEqual([...ALLOWED_LABELS].sort());
  });

  it("worth_applying heading matches CLAUDE.md spec", () => {
    expect(LABEL_DISPLAY.worth_applying.heading).toBe(
      "Worth applying — no detected blocker; verify with employer"
    );
  });

  it("verify_first heading matches spec", () => {
    expect(LABEL_DISPLAY.verify_first.heading).toBe("Verify first");
  });

  it("likely_blocked heading matches spec", () => {
    expect(LABEL_DISPLAY.likely_blocked.heading).toBe("Likely blocked");
  });

  it("unknown heading matches spec", () => {
    expect(LABEL_DISPLAY.unknown.heading).toBe("Unknown");
  });

  describe("forbidden strings never appear in any label copy", () => {
    for (const label of ALLOWED_LABELS) {
      const display = LABEL_DISPLAY[label];
      const allCopy = [display.heading, display.tag].join(" ").toLowerCase();

      for (const forbidden of FORBIDDEN_STRINGS) {
        it(`label '${label}' does not contain '${forbidden}'`, () => {
          expect(allCopy).not.toContain(forbidden.toLowerCase());
        });
      }
    }
  });
});
