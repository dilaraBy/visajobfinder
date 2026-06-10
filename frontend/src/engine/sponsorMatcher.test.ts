import { describe, it, expect } from "vitest";
import {
  SponsorMatcher,
  scoreNames,
  LOW_CANDIDATE,
  type SponsorRecord,
} from "./sponsorMatcher";

// Reference implementation: the exhaustive scan the blocking index replaces.
// The indexed matcher must return the same match as scanning every record.
function bruteForceMatch(
  matcher: SponsorMatcher,
  raw: string
): [string | null, number, string | null] {
  const text = (raw || "").trim();
  if (!text) return [null, 0.0, null];
  let bestName: string | null = null;
  let bestScore = 0.0;
  let bestMethod: string | null = null;
  for (const record of matcher.records) {
    const names: [string, string][] = [
      [record.organisation_name, "organisation_name"],
      ...record.aliases.map((a): [string, string] => [a, "alias"]),
    ];
    for (const [name, nameType] of names) {
      const [score, method] = scoreNames(text, name);
      if (score > bestScore) {
        bestScore = score;
        bestName = record.organisation_name;
        if (score === 1.0) {
          bestMethod = nameType === "organisation_name" ? "exact" : "alias";
        } else {
          bestMethod = nameType === "alias" ? "alias" : method;
        }
      }
    }
  }
  if (bestName === null || bestScore < LOW_CANDIDATE) return [null, 0.0, null];
  return [bestName, bestScore, bestMethod];
}

function rec(organisation_name: string, aliases: string[] = []): SponsorRecord {
  return {
    organisation_name,
    sponsor_routes: ["Skilled Worker"],
    rating: "A",
    location: "London",
    aliases,
  };
}

describe("SponsorMatcher indexed == brute force", () => {
  // Varied enough that the index actually prunes (shared tokens, overlapping
  // substrings, near-duplicates) rather than returning every record.
  const matcher = new SponsorMatcher([
    rec("Northbridge Analytics Ltd", ["Northbridge"]),
    rec("Northbridge Consulting Group"),
    rec("North Star Trading Limited"),
    rec("Bright Future University", ["BFU"]),
    rec("Bright Future Recruitment Ltd"),
    rec("CareWorks Group Limited"),
    rec("Care Solutions UK"),
    rec("Octopus Energy Group"),
    rec("Acme Digital Ltd"),
    rec("Acme Engineering Services"),
    rec("Global Tech Solutions Ltd"),
    rec("Greenfield Trading Company"),
    rec("Riverside Care Homes"),
    rec("Meridian Financial Partners"),
    rec("Summit Consulting Limited"),
    rec("Apex Engineering Group"),
    rec("Bluewave Technologies"),
    rec("Crown Recruitment Agency"),
    rec("Delta Logistics UK"),
    rec("Evergreen Holdings Ltd"),
  ]);

  const probes = [
    "Northbridge Analytics Ltd",
    "NORTHBRIDGE ANALYTICS LTD",
    "Northbridge Analytics",
    "Northbridge",
    "Octopus Energy",
    "CareWorks Group",
    "Northbrige Analytcs", // typos
    "Globl Tech Solutions",
    "Conslting Limited",
    "Recruitement Agency",
    "Care Homes",
    "Trading Company",
    "Engineering Group",
    "Completely Unrelated Employer",
    "zzqq nonexistent xyz",
    "",
    "   ",
    "BFU",
  ];

  for (const probe of probes) {
    it(`matches brute force for ${JSON.stringify(probe)}`, () => {
      const [name, score, method] = bruteForceMatch(matcher, probe);
      const match = matcher.match(probe);
      expect([match.matched_name, match.confidence, match.match_method]).toEqual(
        [name, score, method]
      );
    });
  }
});
