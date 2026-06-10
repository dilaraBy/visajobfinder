// Data layer for the dashboard. Loads the static jobs.json the pipeline writes
// and classifies each job per the browser-local visa profile, reusing the
// parity-locked engine. Sponsor matching is NOT re-run here — the pipeline
// precomputes employer_match + phrase_signals, so we pass them straight through.

import {
  classifyJob,
  SponsorMatcher,
  type ClassificationResult,
  type EmployerMatch,
  type JobInput,
  type PhraseSignal,
  type UserContext,
} from "@/engine";

export interface PublicJobLocation {
  raw: string | null;
  city: string | null;
  country: string | null;
  remote_type: string | null;
}

export interface PublicJobSalary {
  raw: string | null;
  min: number | null;
  max: number | null;
  currency: string | null;
  period: string | null;
  is_missing: boolean;
}

export interface PublicJobDates {
  posted_at: string | null;
  closing_at: string | null;
  fetched_at: string | null;
}

export interface PublicJobFreshness {
  posted_at: string | null;
  age_days: number | null;
  has_posted_date: boolean;
  stale_after_days: number;
  is_stale: boolean;
  needs_review: boolean;
}

export interface PublicJob {
  job_id: string;
  source: string;
  source_job_id?: string | null;
  title: string;
  employer_raw: string;
  description_text: string;
  description_scope?: string;
  location: PublicJobLocation | null;
  salary: PublicJobSalary | null;
  dates: PublicJobDates | null;
  url: string | null;
  visa_signals: {
    employer_match: EmployerMatch;
    phrase_signals: PhraseSignal[];
    base_limitations?: string[];
  };
  freshness: PublicJobFreshness | null;
}

export interface PublicJobsFile {
  generated_at: string;
  source_runs: unknown[];
  freshness_summary?: unknown;
  jobs: PublicJob[];
}

// No sponsor matching happens in the dashboard, so an empty matcher is enough;
// classifyJob uses the precomputed employer_match we pass via options.
const EMPTY_MATCHER = new SponsorMatcher([]);

/** Load the static jobs file. Only a local, same-origin path is accepted. */
export async function loadJobs(
  url = `${import.meta.env.BASE_URL}jobs.json`
): Promise<PublicJobsFile> {
  if (!url.startsWith("/")) {
    throw new Error(`loadJobs only accepts a local, same-origin path; got: ${url}`);
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load jobs from ${url} (HTTP ${response.status})`);
  }
  return (await response.json()) as PublicJobsFile;
}

/** Map a public job record to the engine's JobInput shape. */
export function jobToInput(job: PublicJob): JobInput {
  return {
    job_id: job.job_id,
    source: job.source,
    source_job_id: job.source_job_id ?? null,
    title: job.title,
    employer_raw: job.employer_raw,
    description_text: job.description_text,
    location: job.location?.raw ?? null,
    salary_text: job.salary?.raw ?? null,
    salary_min: job.salary?.min ?? null,
    salary_max: job.salary?.max ?? null,
    posted_at: job.dates?.posted_at ?? null,
    closing_at: job.dates?.closing_at ?? null,
    fetched_at: job.dates?.fetched_at ?? null,
    url: job.url,
  };
}

/**
 * Classify one job for the active profile using the engine's precomputed
 * signals. This is deterministic and cheap, so the dashboard can re-run it for
 * every job whenever the profile changes.
 */
export function classifyPublicJob(
  job: PublicJob,
  user: UserContext
): ClassificationResult {
  return classifyJob(jobToInput(job), user, EMPTY_MATCHER, {
    phraseSignals: job.visa_signals.phrase_signals,
    employerMatch: job.visa_signals.employer_match,
  });
}
