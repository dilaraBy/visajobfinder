// Loads the static sponsor register that ships with the app.
// sponsors.json is generated from data/sponsor_register/sample_sponsors.csv by
// scripts/gen_parity_golden.py (see frontend/README.md). It is intentionally a
// static JSON artifact so the engine can run fully client-side with no network.

import { SponsorMatcher } from "./sponsorMatcher";
import type { SponsorRecord, SponsorRegisterSource } from "./sponsorMatcher";

export interface SponsorRegisterFile {
  source: SponsorRegisterSource;
  records: SponsorRecord[];
}

/** Build a SponsorMatcher from a loaded sponsors.json payload. */
export function matcherFromFile(file: SponsorRegisterFile): SponsorMatcher {
  return new SponsorMatcher(file.records, file.source);
}

/**
 * Load the bundled sponsors.json (served from /sponsors.json) and build a
 * matcher. Use this in the browser; tests load the fixture directly instead.
 *
 * Only a same-origin, relative path is accepted. This preserves the local-only
 * privacy guarantee: the engine must never be pointed at a remote register.
 */
export async function loadSponsorMatcher(
  url = "/sponsors.json"
): Promise<SponsorMatcher> {
  if (!url.startsWith("/")) {
    throw new Error(
      `loadSponsorMatcher only accepts a local, same-origin path; got: ${url}`
    );
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load sponsor register from ${url}`);
  }
  const file = (await response.json()) as SponsorRegisterFile;
  return matcherFromFile(file);
}
