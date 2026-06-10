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
export type SortKey = "label_severity" | "posted_at_desc" | "posted_at_asc";

export interface FilterState {
  label: LabelFilter;
  source: string;
  location: string;
  freshness: FreshnessFilter;
  sort: SortKey;
}

export const DEFAULT_FILTERS: FilterState = {
  label: "all",
  source: "all",
  location: "",
  freshness: "all",
  sort: "label_severity",
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
  "sort",
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
    sort: readParam<SortKey>(
      params,
      "sort",
      ["label_severity", "posted_at_desc", "posted_at_asc"],
      "label_severity"
    ),
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
    sort: next.sort,
  };
  const paramKey: Record<keyof FilterState, string> = {
    label: "label",
    source: "source",
    location: "loc",
    freshness: "fresh",
    sort: "sort",
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

function passesLocation(job: PublicJob, query: string): boolean {
  if (!query) return true;
  const needle = query.toLowerCase();
  const raw = job.location?.raw?.toLowerCase() ?? "";
  const city = job.location?.city?.toLowerCase() ?? "";
  const country = job.location?.country?.toLowerCase() ?? "";
  return raw.includes(needle) || city.includes(needle) || country.includes(needle);
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

export function applyFilters(
  items: ClassifiedJob[],
  filters: FilterState
): ClassifiedJob[] {
  const filtered = items.filter(({ job, result }) => {
    if (filters.label !== "all" && result.label !== filters.label) return false;
    if (filters.source !== "all" && job.source !== filters.source) return false;
    if (!passesLocation(job, filters.location)) return false;
    if (!passesFreshness(job, filters.freshness)) return false;
    return true;
  });

  const sorted = filtered.slice();
  if (filters.sort === "label_severity") {
    sorted.sort((a, b) => {
      const diff = LABEL_SEVERITY[a.result.label] - LABEL_SEVERITY[b.result.label];
      if (diff !== 0) return diff;
      return compareByPostedAt(a.job, b.job, 1); // newer first within a label tier
    });
  } else if (filters.sort === "posted_at_desc") {
    sorted.sort((a, b) => compareByPostedAt(a.job, b.job, 1));
  } else if (filters.sort === "posted_at_asc") {
    sorted.sort((a, b) => compareByPostedAt(a.job, b.job, -1));
  }
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

export function hasActiveFilters(filters: FilterState): boolean {
  return (
    filters.label !== DEFAULT_FILTERS.label ||
    filters.source !== DEFAULT_FILTERS.source ||
    filters.location !== DEFAULT_FILTERS.location ||
    filters.freshness !== DEFAULT_FILTERS.freshness
  );
}
