import { describe, expect, it } from "vitest";
import golden from "./__fixtures__/parity_golden.json";
import sponsorsFile from "./__fixtures__/sponsors.json";
import { matcherFromFile } from "./sponsorData";
import type { SponsorRegisterFile } from "./sponsorData";
import { analyseJob } from "./engine";
import type { JobInput, UserContext } from "./types";

interface GoldenCase {
  dataset: string;
  case_id: string;
  eval_id: string;
  job: JobInput;
  user_context: UserContext;
  expected: {
    label: string;
    evidence_categories: string[];
    sponsor: {
      matched_name: string | null;
      confidence_band: string;
      is_match: boolean;
      confidence: number;
    };
  };
}

const cases = (golden as { cases: GoldenCase[] }).cases;
const matcher = matcherFromFile(sponsorsFile as SponsorRegisterFile);

function evidenceCategories(evidence: { category: string }[]): string[] {
  return [...new Set(evidence.map((e) => e.category))].sort();
}

describe("TS engine parity with Python golden", () => {
  it("loaded a non-empty golden corpus", () => {
    expect(cases.length).toBeGreaterThan(0);
  });

  it.each(cases.map((c) => [c.case_id, c] as const))(
    "label parity: %s",
    (_caseId, testCase) => {
      const out = analyseJob(testCase.job, testCase.user_context, matcher);
      expect(out.classification.label).toBe(testCase.expected.label);
    }
  );

  it.each(cases.map((c) => [c.case_id, c] as const))(
    "evidence category parity: %s",
    (_caseId, testCase) => {
      const out = analyseJob(testCase.job, testCase.user_context, matcher);
      expect(evidenceCategories(out.classification.evidence)).toEqual(
        [...testCase.expected.evidence_categories].sort()
      );
    }
  );

  it.each(cases.map((c) => [c.case_id, c] as const))(
    "sponsor match parity: %s",
    (_caseId, testCase) => {
      const out = analyseJob(testCase.job, testCase.user_context, matcher);
      const sponsor = out.classification.employer_match;
      expect({
        matched_name: sponsor.matched_name,
        confidence_band: sponsor.confidence_band,
        is_match: sponsor.is_match,
      }).toEqual({
        matched_name: testCase.expected.sponsor.matched_name,
        confidence_band: testCase.expected.sponsor.confidence_band,
        is_match: testCase.expected.sponsor.is_match,
      });
    }
  );

  // Soft check on the SequenceMatcher equivalence: confidence should match the
  // Python value closely (3dp). Reported separately so a tiny float drift does
  // not mask the categorical band/label parity above.
  it.each(cases.map((c) => [c.case_id, c] as const))(
    "sponsor confidence close to Python: %s",
    (_caseId, testCase) => {
      const out = analyseJob(testCase.job, testCase.user_context, matcher);
      expect(out.classification.employer_match.confidence).toBeCloseTo(
        testCase.expected.sponsor.confidence,
        3
      );
    }
  );
});
