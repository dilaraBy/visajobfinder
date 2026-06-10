// Port of pipeline/sponsor_register/matcher.py.
// Uses sequenceRatio() (a faithful port of difflib.SequenceMatcher.ratio()).
// This file is a PORT and must stay in sync with the Python source of truth.

import type { EmployerMatch } from "./types";
import { normaliseEmployerName } from "./normalise";
import { sequenceRatio } from "./sequenceMatcher";

export const HIGH_CONFIDENCE = 0.92;
export const MEDIUM_CONFIDENCE = 0.82;
export const LOW_CANDIDATE = 0.6;
export const DEFAULT_SOURCE_NAME = "GOV.UK Register of Licensed Sponsors";

// Generic sector/structure words that, when they are the *only* thing two names
// share, are not enough to assert a reliable sponsor match. Mirrors
// GENERIC_MATCH_TOKENS in pipeline/sponsor_register/matcher.py.
const GENERIC_MATCH_TOKENS = new Set<string>([
  "and", "the", "group", "holdings", "holding", "international", "global",
  "uk", "services", "service", "solutions", "solution", "consulting",
  "consultancy", "consultants", "recruitment", "staffing", "education",
  "care", "training", "management", "technologies", "technology", "systems",
  "partners", "associates", "agency", "trading", "enterprises", "enterprise",
  "ventures", "capital",
]);

/** True if the two normalised names share at least one non-generic token. */
function sharesDistinctiveToken(queryNorm: string, candidateNorm: string): boolean {
  const candidateTokens = tokenSet(candidateNorm);
  for (const token of tokenSet(queryNorm)) {
    if (candidateTokens.has(token) && !GENERIC_MATCH_TOKENS.has(token)) {
      return true;
    }
  }
  return false;
}

export interface SponsorRecord {
  organisation_name: string;
  sponsor_routes: string[];
  rating: string | null;
  location: string | null;
  aliases: string[];
}

export interface SponsorRegisterSource {
  source_name: string;
  source_published_at: string | null;
  downloaded_at: string | null;
}

function searchableNames(record: SponsorRecord): [string, string][] {
  const names: [string, string][] = [
    [record.organisation_name, "organisation_name"],
  ];
  for (const alias of record.aliases) {
    names.push([alias, "alias"]);
  }
  return names;
}

export function confidenceBand(confidence: number, isMatch = true): string {
  if (!isMatch && confidence <= 0) {
    return "none";
  }
  if (confidence >= HIGH_CONFIDENCE) {
    return "high";
  }
  if (confidence >= MEDIUM_CONFIDENCE) {
    return "medium";
  }
  return "low";
}

function tokenSet(value: string): Set<string> {
  return new Set(value.split(/\s+/).filter(Boolean));
}

/** Character trigrams of a normalised name. For names shorter than 3 chars the
 * whole string is used as a single key (3-char trigrams never collide with
 * these). Mirrors _trigrams in pipeline/sponsor_register/matcher.py. */
function trigrams(text: string): Set<string> {
  if (text.length < 3) {
    return text ? new Set([text]) : new Set();
  }
  const grams = new Set<string>();
  for (let i = 0; i <= text.length - 3; i += 1) {
    grams.add(text.slice(i, i + 3));
  }
  return grams;
}

function isSubset(a: Set<string>, b: Set<string>): boolean {
  for (const x of a) {
    if (!b.has(x)) return false;
  }
  return true;
}

function setIntersectionSize(a: Set<string>, b: Set<string>): number {
  let count = 0;
  for (const x of a) {
    if (b.has(x)) count += 1;
  }
  return count;
}

function tokenSimilarity(left: string, right: string): number {
  const leftTokens = tokenSet(left);
  const rightTokens = tokenSet(right);
  if (leftTokens.size === 0 || rightTokens.size === 0) {
    return 0.0;
  }

  const intersection = setIntersectionSize(leftTokens, rightTokens);
  const dice = (2 * intersection) / (leftTokens.size + rightTokens.size);
  const sortedLeft = [...leftTokens].sort().join(" ");
  const sortedRight = [...rightTokens].sort().join(" ");
  const sequence = sequenceRatio(sortedLeft, sortedRight);

  if (
    isSubset(leftTokens, rightTokens) ||
    isSubset(rightTokens, leftTokens)
  ) {
    if (Math.min(leftTokens.size, rightTokens.size) >= 2) {
      return Math.max(dice, sequence, 0.86);
    }
    return Math.max(dice, sequence, 0.78);
  }

  return Math.max(dice, sequence);
}

function hasWeakTokenAlignment(left: string, right: string): boolean {
  const leftTokens = left.split(/\s+/).filter(Boolean);
  const rightTokens = right.split(/\s+/).filter(Boolean);
  if (leftTokens.length === 0 || rightTokens.length === 0) {
    return true;
  }
  const leftSet = new Set(leftTokens);
  const rightSet = new Set(rightTokens);
  if (isSubset(leftSet, rightSet) || isSubset(rightSet, leftSet)) {
    return false;
  }

  for (const token of leftTokens) {
    let best = 0;
    for (const candidate of rightTokens) {
      const ratio = sequenceRatio(token, candidate);
      if (ratio > best) best = ratio;
    }
    if (best < 0.8) {
      return true;
    }
  }
  return false;
}

function substringScore(query: string, candidate: string): number {
  const queryTokens = query.split(/\s+/).filter(Boolean);
  const candidateTokens = candidate.split(/\s+/).filter(Boolean);
  if (queryTokens.length < 2 || candidateTokens.length < 2) {
    return 0.0;
  }
  if (candidate.includes(query) || query.includes(candidate)) {
    return 0.86;
  }
  return 0.0;
}

export function scoreNames(
  rawQuery: string,
  rawCandidate: string
): [number, string] {
  const query = normaliseEmployerName(rawQuery);
  const candidate = normaliseEmployerName(rawCandidate);
  if (!query || !candidate) {
    return [0.0, "token_set"];
  }
  if (query === candidate) {
    return [1.0, "exact"];
  }

  const sequence = sequenceRatio(query, candidate);
  const tokenScore = tokenSimilarity(query, candidate);
  const subScore = substringScore(query, candidate);
  let score = Math.max(sequence, tokenScore, subScore);
  if (hasWeakTokenAlignment(query, candidate)) {
    score *= 0.95;
  }
  if (score === subScore && subScore > 0) {
    return [score, "substring"];
  }
  return [score, "token_set"];
}

// One searchable name entry; the array index is the original iteration order.
interface MatcherEntry {
  record: SponsorRecord;
  name: string;
  nameType: string;
}

export class SponsorMatcher {
  records: SponsorRecord[];
  source_name: string;
  source_published_at: string | null;
  source_downloaded_at: string | null;

  // Blocking indexes — see _build_index in the Python source of truth. The
  // candidate set for a query is every entry that is an exact normalised match,
  // shares a normalised token, or shares a character trigram. Scoring itself is
  // unchanged, so results match the brute-force scan for realistic names.
  private entries: MatcherEntry[] = [];
  private exactIndex: Map<string, number> = new Map();
  private tokenIndex: Map<string, number[]> = new Map();
  private trigramIndex: Map<string, number[]> = new Map();

  constructor(
    records: SponsorRecord[],
    source: Partial<SponsorRegisterSource> = {}
  ) {
    this.records = records;
    this.source_name = source.source_name ?? DEFAULT_SOURCE_NAME;
    this.source_published_at = source.source_published_at ?? null;
    this.source_downloaded_at = source.downloaded_at ?? null;
    this.buildIndex();
  }

  private buildIndex(): void {
    for (const record of this.records) {
      for (const [name, nameType] of searchableNames(record)) {
        const idx = this.entries.length;
        this.entries.push({ record, name, nameType });
        const norm = normaliseEmployerName(name);
        if (!norm) continue;
        if (!this.exactIndex.has(norm)) this.exactIndex.set(norm, idx);
        for (const token of tokenSet(norm)) {
          const bucket = this.tokenIndex.get(token);
          if (bucket) bucket.push(idx);
          else this.tokenIndex.set(token, [idx]);
        }
        for (const gram of trigrams(norm)) {
          const bucket = this.trigramIndex.get(gram);
          if (bucket) bucket.push(idx);
          else this.trigramIndex.set(gram, [idx]);
        }
      }
    }
  }

  private noMatch(raw: string): EmployerMatch {
    return {
      raw,
      matched_name: null,
      confidence: 0.0,
      confidence_band: "none",
      match_method: null,
      sponsor_routes: [],
      rating: null,
      location: null,
      is_match: false,
      source_name: this.source_name,
      source_published_at: this.source_published_at,
      source_downloaded_at: this.source_downloaded_at,
    };
  }

  private buildMatch(
    raw: string,
    record: SponsorRecord,
    score: number,
    method: string | null,
    isMatch: boolean
  ): EmployerMatch {
    // A demoted match (would be >= MEDIUM but failed the distinctive-token gate)
    // is surfaced as a low-confidence candidate so the closest register entry
    // stays visible for the user to verify.
    const band = isMatch
      ? confidenceBand(score, true)
      : score > 0
        ? "low"
        : "none";
    return {
      raw,
      matched_name: record.organisation_name,
      confidence: score,
      confidence_band: band,
      match_method: method,
      sponsor_routes: record.sponsor_routes,
      rating: record.rating,
      location: record.location,
      is_match: isMatch,
      source_name: this.source_name,
      source_published_at: this.source_published_at,
      source_downloaded_at: this.source_downloaded_at,
    };
  }

  match(employerRaw: string): EmployerMatch {
    const raw = (employerRaw || "").trim();
    if (!raw) {
      return this.noMatch(employerRaw || "");
    }

    const query = normaliseEmployerName(raw);

    // Exact normalised match scores 1.0; nothing beats it.
    if (query) {
      const exactIdx = this.exactIndex.get(query);
      if (exactIdx !== undefined) {
        const entry = this.entries[exactIdx];
        const method =
          entry.nameType === "organisation_name" ? "exact" : "alias";
        return this.buildMatch(raw, entry.record, 1.0, method, true);
      }
    }

    // Otherwise score candidates sharing a token or trigram with the query.
    const candidateIdxs = new Set<number>();
    if (query) {
      for (const token of tokenSet(query)) {
        const bucket = this.tokenIndex.get(token);
        if (bucket) for (const i of bucket) candidateIdxs.add(i);
      }
      for (const gram of trigrams(query)) {
        const bucket = this.trigramIndex.get(gram);
        if (bucket) for (const i of bucket) candidateIdxs.add(i);
      }
    }

    let bestIdx = -1;
    let bestScore = 0.0;
    let bestMethod: string | null = null;
    let bestName = "";
    for (const idx of [...candidateIdxs].sort((a, b) => a - b)) {
      const { name, nameType } = this.entries[idx];
      const [score, method] = scoreNames(raw, name);
      if (score > bestScore) {
        bestIdx = idx;
        bestScore = score;
        bestName = name;
        if (score === 1.0) {
          bestMethod = nameType === "organisation_name" ? "exact" : "alias";
        } else {
          bestMethod = nameType === "alias" ? "alias" : method;
        }
      }
    }

    if (bestIdx === -1 || bestScore < LOW_CANDIDATE) {
      return this.noMatch(raw);
    }
    // A non-exact match only counts as reliable if it is very strong (>= HIGH)
    // or rests on a shared distinctive token (rejects character coincidences
    // between different companies).
    const reliable =
      bestScore >= HIGH_CONFIDENCE ||
      (bestScore >= MEDIUM_CONFIDENCE &&
        sharesDistinctiveToken(query, normaliseEmployerName(bestName)));
    return this.buildMatch(
      raw,
      this.entries[bestIdx].record,
      bestScore,
      bestMethod,
      reliable
    );
  }
}
