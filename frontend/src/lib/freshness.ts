import type { PublicJob, PublicJobFreshness } from "./jobs";

export interface FreshnessDisplay {
  text: string;
  /** True when the listing has no machine-verified posted date. */
  unverified: boolean;
  stale: boolean;
}

/**
 * Honest freshness label. If a listing has no machine-verified age (source
 * gave no parseable posted date), show the raw date marked as unverified —
 * or "No posting date" — rather than implying we confirmed its recency.
 */
export function freshnessDisplay(job: PublicJob): FreshnessDisplay {
  const f: PublicJobFreshness | null = job.freshness;
  const rawDate = job.dates?.posted_at ?? f?.posted_at ?? null;

  if (f && f.has_posted_date && typeof f.age_days === "number") {
    return {
      text: f.age_days <= 0 ? "Posted today" : `Posted ${f.age_days}d ago`,
      unverified: false,
      stale: f.is_stale,
    };
  }
  if (rawDate) {
    return { text: `Posted ${rawDate} (unverified)`, unverified: true, stale: false };
  }
  return { text: "No posting date", unverified: true, stale: false };
}
