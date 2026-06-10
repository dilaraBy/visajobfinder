// Typed mirrors of pipeline/classifier/models.py.
// This file is a PORT of the Python source of truth. Keep it in sync.

export const ALLOWED_LABELS = [
  "worth_applying",
  "verify_first",
  "likely_blocked",
  "unknown",
] as const;
export type Label = (typeof ALLOWED_LABELS)[number];

export const ALLOWED_VISA_SITUATIONS = [
  "graduate_route",
  "needs_sponsorship_before_start",
  "unknown",
] as const;
export type VisaSituation = (typeof ALLOWED_VISA_SITUATIONS)[number];

/** Minimal job shape accepted by the engine and paste checker. */
export interface JobInput {
  job_id?: string;
  source?: string;
  source_job_id?: string | null;
  title?: string;
  employer_raw?: string;
  description_text?: string;
  location?: string | null;
  salary_text?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  posted_at?: string | null;
  closing_at?: string | null;
  fetched_at?: string | null;
  url?: string | null;
}

/** Apply Python dataclass defaults to a partial JobInput. */
export function normaliseJobInput(job: JobInput): Required<JobInput> {
  return {
    job_id: job.job_id ?? "paste:manual",
    source: job.source ?? "paste",
    source_job_id: job.source_job_id ?? null,
    title: job.title ?? "",
    employer_raw: job.employer_raw ?? "",
    description_text: job.description_text ?? "",
    location: job.location ?? null,
    salary_text: job.salary_text ?? null,
    salary_min: job.salary_min ?? null,
    salary_max: job.salary_max ?? null,
    posted_at: job.posted_at ?? null,
    closing_at: job.closing_at ?? null,
    fetched_at: job.fetched_at ?? null,
    url: job.url ?? null,
  };
}

/** The v1 visa context used for status-aware decision rules. */
export interface UserContext {
  visa_situation?: VisaSituation;
  visa_expiry_month?: string | null;
  needs_sponsorship_before_start?: boolean;
  needs_future_sponsorship?: boolean;
  target_start_month?: string | null;
}

export function normaliseUserContext(user: UserContext): Required<UserContext> {
  const visa_situation = user.visa_situation ?? "unknown";
  if (!(ALLOWED_VISA_SITUATIONS as readonly string[]).includes(visa_situation)) {
    throw new Error(
      `Unsupported visa_situation '${visa_situation}'. Expected one of ${[
        ...ALLOWED_VISA_SITUATIONS,
      ]
        .slice()
        .sort()
        .join(", ")}.`
    );
  }
  return {
    visa_situation,
    visa_expiry_month: user.visa_expiry_month ?? null,
    needs_sponsorship_before_start: Boolean(user.needs_sponsorship_before_start),
    needs_future_sponsorship: Boolean(user.needs_future_sponsorship),
    target_start_month: user.target_start_month ?? null,
  };
}

export interface PhraseSignal {
  category: string;
  severity: string;
  text: string;
  start_index: number;
  end_index: number;
  rule_id: string;
}

export interface EmployerMatch {
  raw: string;
  matched_name: string | null;
  confidence: number;
  confidence_band: string;
  match_method: string | null;
  sponsor_routes: string[];
  rating: string | null;
  location: string | null;
  is_match: boolean;
  source_name: string | null;
  source_published_at: string | null;
  source_downloaded_at: string | null;
}

/** Round confidence to 3 dp, mirroring EmployerMatch.to_dict() in Python. */
export function employerMatchToDict(match: EmployerMatch): EmployerMatch {
  return { ...match, confidence: round3(match.confidence) };
}

export interface EvidenceItem {
  type: string;
  category: string;
  severity?: string;
  text: string;
  start_index?: number;
  end_index?: number;
  rule_id?: string;
}

export interface ClassificationResult {
  job_id: string;
  label: Label;
  reason: string;
  evidence: EvidenceItem[];
  employer_match: EmployerMatch;
  what_to_verify: string[];
  limitations: string[];
}

/** Match Python's round() (banker's rounding) closely enough for 3dp display. */
export function round3(value: number): number {
  // Python round() uses round-half-to-even; JS Math.round is half-up.
  // For the confidence values produced by the matcher the difference is
  // immaterial, but we replicate banker's rounding to be safe.
  const factor = 1000;
  const scaled = value * factor;
  const floor = Math.floor(scaled);
  const diff = scaled - floor;
  let rounded: number;
  if (Math.abs(diff - 0.5) < 1e-9) {
    rounded = floor % 2 === 0 ? floor : floor + 1;
  } else {
    rounded = Math.round(scaled);
  }
  return rounded / factor;
}
