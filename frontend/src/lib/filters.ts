/**
 * Filter + sort state for the dashboard, derived from URL search params so a
 * filtered view is shareable and survives reload. Personal data still stays in
 * localStorage (the visa profile); the filter state is purely about *which jobs
 * are visible* and is safe to put in the URL.
 */

import type { ClassificationResult } from "@/engine";
import type { Label } from "@/engine/types";
import type { PublicJob } from "./jobs";

export type LabelFilter = Label | "all";
export type FreshnessFilter = "all" | "fresh" | "stale" | "missing_date";
export type PostedWithinFilter = "all" | "30" | "90" | "180";
export type SortKey = "label_severity" | "posted_at_desc" | "posted_at_asc";

export interface FilterState {
  label: LabelFilter;
  source: string;
  location: string;
  freshness: FreshnessFilter;
  /** Maximum posting age in days ("all" = any age). Undated jobs are hidden
   * when a specific window is selected, since their recency can't be confirmed. */
  posted_within: PostedWithinFilter;
  sort: SortKey;
  /** Free-text job-interest keywords (comma separated). Filters to matching
   * jobs and ranks stronger matches first. */
  keyword: string;
}

export const DEFAULT_FILTERS: FilterState = {
  label: "all",
  source: "all",
  location: "",
  freshness: "all",
  posted_within: "all",
  sort: "label_severity",
  keyword: "",
};

// Lower is more important: surface red labels and ambiguity over greens by
// default so the user looks at what's most at risk of being misjudged first.
const LABEL_SEVERITY: Record<Label, number> = {
  likely_blocked: 0,
  verify_first: 1,
  unknown: 2,
  worth_applying: 3,
};

const FILTER_KEYS: ReadonlyArray<keyof FilterState> = [
  "label",
  "source",
  "location",
  "freshness",
  "posted_within",
  "sort",
  "keyword",
];

function readParam<T extends string>(
  params: URLSearchParams,
  key: string,
  allowed: ReadonlyArray<T>,
  fallback: T
): T {
  const raw = params.get(key);
  if (raw && (allowed as ReadonlyArray<string>).includes(raw)) {
    return raw as T;
  }
  return fallback;
}

export function filtersFromParams(params: URLSearchParams): FilterState {
  return {
    label: readParam<LabelFilter>(
      params,
      "label",
      ["all", "worth_applying", "verify_first", "likely_blocked", "unknown"],
      "all"
    ),
    source: (params.get("source") ?? "all").trim() || "all",
    location: (params.get("loc") ?? "").trim(),
    freshness: readParam<FreshnessFilter>(
      params,
      "fresh",
      ["all", "fresh", "stale", "missing_date"],
      "all"
    ),
    posted_within: readParam<PostedWithinFilter>(
      params,
      "within",
      ["all", "30", "90", "180"],
      "all"
    ),
    sort: readParam<SortKey>(
      params,
      "sort",
      ["label_severity", "posted_at_desc", "posted_at_asc"],
      "label_severity"
    ),
    keyword: (params.get("q") ?? "").trim(),
  };
}

/** Merge filter updates into the URLSearchParams, dropping defaults to keep the URL clean. */
export function paramsWithFilters(
  base: URLSearchParams,
  next: FilterState
): URLSearchParams {
  const out = new URLSearchParams(base);
  const writes: Record<keyof FilterState, string> = {
    label: next.label,
    source: next.source,
    location: next.location,
    freshness: next.freshness,
    posted_within: next.posted_within,
    sort: next.sort,
    keyword: next.keyword,
  };
  const paramKey: Record<keyof FilterState, string> = {
    label: "label",
    source: "source",
    location: "loc",
    freshness: "fresh",
    posted_within: "within",
    sort: "sort",
    keyword: "q",
  };
  for (const key of FILTER_KEYS) {
    const value = writes[key];
    const isDefault = value === DEFAULT_FILTERS[key];
    if (!value || isDefault) {
      out.delete(paramKey[key]);
    } else {
      out.set(paramKey[key], value);
    }
  }
  return out;
}

export interface ClassifiedJob {
  job: PublicJob;
  result: ClassificationResult;
}

function passesFreshness(job: PublicJob, filter: FreshnessFilter): boolean {
  if (filter === "all") return true;
  const f = job.freshness;
  if (!f) return filter === "missing_date";
  if (filter === "missing_date") return !f.has_posted_date;
  if (filter === "fresh") return f.has_posted_date && !f.is_stale;
  if (filter === "stale") return f.has_posted_date && f.is_stale;
  return true;
}

function passesPostedWithin(job: PublicJob, filter: PostedWithinFilter): boolean {
  if (filter === "all") return true;
  const maxDays = Number(filter);
  const age = job.freshness?.age_days;
  // Undated jobs can't be confirmed recent, so hide them when a window is set.
  if (age == null) return false;
  return age <= maxDays;
}

function passesLocation(job: PublicJob, query: string): boolean {
  if (!query) return true;
  const needle = query.toLowerCase();
  const raw = job.location?.raw?.toLowerCase() ?? "";
  const city = job.location?.city?.toLowerCase() ?? "";
  const country = job.location?.country?.toLowerCase() ?? "";
  return raw.includes(needle) || city.includes(needle) || country.includes(needle);
}

/**
 * Split a keyword string into lowercased phrases. Split on commas only (not
 * spaces) so multi-word interests like "psychology graduate" stay one phrase
 * and don't shatter into a "graduate" token that matches everything.
 */
export function parseKeywords(query: string): string[] {
  return query
    .toLowerCase()
    .split(",")
    .map((phrase) => phrase.trim())
    .filter(Boolean);
}

/** True when no phrases are given, or the job matches at least one (OR). */
export function passesKeywords(job: PublicJob, phrases: string[]): boolean {
  if (phrases.length === 0) return true;
  const haystack = [
    job.title,
    job.employer_raw,
    job.category ?? "",
    job.description_text,
  ]
    .join(" ")
    .toLowerCase();
  return phrases.some((phrase) => haystack.includes(phrase));
}

/** Relevance score: title hits weigh most, then category, then body. */
export function keywordScore(job: PublicJob, phrases: string[]): number {
  if (phrases.length === 0) return 0;
  const title = (job.title ?? "").toLowerCase();
  const category = (job.category ?? "").toLowerCase();
  const body = (job.description_text ?? "").toLowerCase();
  let score = 0;
  for (const phrase of phrases) {
    if (title.includes(phrase)) score += 3;
    else if (category.includes(phrase)) score += 2;
    else if (body.includes(phrase)) score += 1;
  }
  return score;
}

function compareByPostedAt(a: PublicJob, b: PublicJob, direction: 1 | -1): number {
  // Listings without a posted date sink to the bottom regardless of direction,
  // so unknown ages never look "freshest" or "oldest".
  const aDate = a.freshness?.has_posted_date ? a.freshness.posted_at : null;
  const bDate = b.freshness?.has_posted_date ? b.freshness.posted_at : null;
  if (aDate && !bDate) return -1;
  if (!aDate && bDate) return 1;
  if (!aDate && !bDate) return 0;
  return aDate! < bDate! ? direction : aDate! > bDate! ? -direction : 0;
}

/** The active sort comparator, independent of keyword ranking. */
function baseComparator(
  sort: SortKey
): (a: ClassifiedJob, b: ClassifiedJob) => number {
  if (sort === "posted_at_desc") {
    return (a, b) => compareByPostedAt(a.job, b.job, 1);
  }
  if (sort === "posted_at_asc") {
    return (a, b) => compareByPostedAt(a.job, b.job, -1);
  }
  // label_severity (default)
  return (a, b) => {
    const diff = LABEL_SEVERITY[a.result.label] - LABEL_SEVERITY[b.result.label];
    if (diff !== 0) return diff;
    return compareByPostedAt(a.job, b.job, 1); // newer first within a label tier
  };
}

export function applyFilters(
  items: ClassifiedJob[],
  filters: FilterState
): ClassifiedJob[] {
  const tokens = parseKeywords(filters.keyword);
  const filtered = items.filter(({ job, result }) => {
    if (filters.label !== "all" && result.label !== filters.label) return false;
    if (filters.source !== "all" && job.source !== filters.source) return false;
    if (!passesLocation(job, filters.location)) return false;
    if (!passesFreshness(job, filters.freshness)) return false;
    if (!passesPostedWithin(job, filters.posted_within)) return false;
    if (!passesKeywords(job, tokens)) return false;
    return true;
  });

  const compare = baseComparator(filters.sort);
  const sorted = filtered.slice();
  sorted.sort((a, b) => {
    if (tokens.length > 0) {
      // Stronger keyword matches first; the active sort (label_severity by
      // default) is preserved as the within-group tiebreaker.
      const scoreDiff = keywordScore(b.job, tokens) - keywordScore(a.job, tokens);
      if (scoreDiff !== 0) return scoreDiff;
    }
    return compare(a, b);
  });
  return sorted;
}

/** Unique source IDs present in the dataset, alphabetised, for the source dropdown. */
export function availableSources(items: ClassifiedJob[]): string[] {
  const set = new Set<string>();
  for (const { job } of items) {
    if (job.source) set.add(job.source);
  }
  return Array.from(set).sort();
}

/** Add or remove a phrase from a comma-separated keyword string. Used by the
 * interest chips so toggling a chip stays in sync with the free-text box. */
export function toggleKeyword(current: string, phrase: string): string {
  const target = phrase.trim().toLowerCase();
  const phrases = parseKeywords(current);
  const next = phrases.includes(target)
    ? phrases.filter((p) => p !== target)
    : [...phrases, target];
  return next.join(", ");
}

/** Unique job categories present in the dataset, alphabetised, for the
 * interest chips. Jobs without a category are ignored. */
export function availableCategories(items: ClassifiedJob[]): string[] {
  const set = new Set<string>();
  for (const { job } of items) {
    const category = job.category?.trim();
    if (category) set.add(category);
  }
  return Array.from(set).sort();
}

export function hasActiveFilters(filters: FilterState): boolean {
  return (
    filters.label !== DEFAULT_FILTERS.label ||
    filters.source !== DEFAULT_FILTERS.source ||
    filters.location !== DEFAULT_FILTERS.location ||
    filters.freshness !== DEFAULT_FILTERS.freshness ||
    filters.posted_within !== DEFAULT_FILTERS.posted_within ||
    filters.keyword !== DEFAULT_FILTERS.keyword
  );
}
