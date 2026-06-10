/**
 * Per-job tracking (status + note + deadline) kept in localStorage only.
 *
 * CLAUDE.md Data Principles: personal data MUST stay browser-local in v1.
 * Nothing in this module makes a network call.
 *
 * Export/import is a single JSON file that contains both the visa profile
 * and the tracking map, so the user can move data between machines without
 * an account. Imports merge defensively: unknown fields are dropped, and
 * malformed entries are skipped rather than failing the whole import.
 */

import {
  DEFAULT_VISA_PROFILE,
  type VisaProfile,
  VISA_SITUATION_LABELS,
} from "@/visaProfile";

export const TRACKING_STORAGE_KEY = "vjf_job_tracking_v1";

export const TRACKING_STATUSES = [
  "interested",
  "applied",
  "rejected",
  "offer",
] as const;

export type TrackingStatus = (typeof TRACKING_STATUSES)[number];

export const TRACKING_STATUS_LABEL: Record<TrackingStatus, string> = {
  interested: "Interested",
  applied: "Applied",
  rejected: "Rejected",
  offer: "Offer",
};

export interface TrackingEntry {
  status: TrackingStatus | null;
  note: string;
  deadline: string; // YYYY-MM-DD or ""
  updated_at: string; // ISO timestamp
}

export type TrackingState = Record<string, TrackingEntry>;

export const EMPTY_TRACKING_ENTRY: TrackingEntry = {
  status: null,
  note: "",
  deadline: "",
  updated_at: "",
};

function isTrackingStatus(value: unknown): value is TrackingStatus {
  return (
    typeof value === "string" &&
    (TRACKING_STATUSES as readonly string[]).includes(value)
  );
}

/** Build a sanitised TrackingEntry from arbitrary user input (e.g. an import). */
export function sanitiseEntry(raw: unknown): TrackingEntry | null {
  if (!raw || typeof raw !== "object") return null;
  const obj = raw as Record<string, unknown>;
  const status = isTrackingStatus(obj.status) ? obj.status : null;
  const note = typeof obj.note === "string" ? obj.note : "";
  const deadline =
    typeof obj.deadline === "string" && /^\d{4}-\d{2}-\d{2}$/.test(obj.deadline)
      ? obj.deadline
      : "";
  const updated_at =
    typeof obj.updated_at === "string" ? obj.updated_at : new Date().toISOString();
  // Drop completely empty entries so we don't grow the store with no-ops.
  if (!status && !note && !deadline) return null;
  return { status, note, deadline, updated_at };
}

export interface ExportFile {
  app: "visajobfinder";
  version: 1;
  exported_at: string;
  visa_profile: VisaProfile;
  tracking: TrackingState;
}

export function buildExport(
  profile: VisaProfile,
  tracking: TrackingState
): ExportFile {
  return {
    app: "visajobfinder",
    version: 1,
    exported_at: new Date().toISOString(),
    visa_profile: profile,
    tracking,
  };
}

export interface ImportSummary {
  profileImported: boolean;
  trackedJobs: number;
  errors: string[];
}

export interface ParsedImport {
  profile: VisaProfile | null;
  tracking: TrackingState;
  summary: ImportSummary;
}

function sanitiseProfile(raw: unknown): VisaProfile | null {
  if (!raw || typeof raw !== "object") return null;
  const obj = raw as Record<string, unknown>;
  const situation =
    typeof obj.visa_situation === "string" &&
    Object.keys(VISA_SITUATION_LABELS).includes(obj.visa_situation)
      ? (obj.visa_situation as VisaProfile["visa_situation"])
      : DEFAULT_VISA_PROFILE.visa_situation;
  return {
    visa_situation: situation,
    needs_sponsorship_before_start: Boolean(obj.needs_sponsorship_before_start),
    needs_future_sponsorship: Boolean(obj.needs_future_sponsorship),
    visa_expiry_month:
      typeof obj.visa_expiry_month === "string" ? obj.visa_expiry_month : "",
    target_start_month:
      typeof obj.target_start_month === "string" ? obj.target_start_month : "",
  };
}

export function parseImport(text: string): ParsedImport {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch (err) {
    return {
      profile: null,
      tracking: {},
      summary: {
        profileImported: false,
        trackedJobs: 0,
        errors: [`Could not parse JSON: ${(err as Error).message}`],
      },
    };
  }
  if (!data || typeof data !== "object") {
    return {
      profile: null,
      tracking: {},
      summary: {
        profileImported: false,
        trackedJobs: 0,
        errors: ["Expected a JSON object at the top level."],
      },
    };
  }
  const obj = data as Record<string, unknown>;
  const errors: string[] = [];
  if (obj.app !== "visajobfinder") {
    errors.push(
      'File does not look like a VisaJobFinder export (missing "app": "visajobfinder").'
    );
  }

  const profile = sanitiseProfile(obj.visa_profile);
  const tracking: TrackingState = {};
  const rawTracking = obj.tracking;
  if (rawTracking && typeof rawTracking === "object") {
    for (const [jobId, entry] of Object.entries(rawTracking)) {
      const sanitised = sanitiseEntry(entry);
      if (sanitised) tracking[jobId] = sanitised;
    }
  }

  return {
    profile,
    tracking,
    summary: {
      profileImported: profile !== null,
      trackedJobs: Object.keys(tracking).length,
      errors,
    },
  };
}

/** Remove an entry's tombstone (or fully empty entry) from the state. */
export function withEntry(
  state: TrackingState,
  jobId: string,
  patch: Partial<TrackingEntry>
): TrackingState {
  const current = state[jobId] ?? EMPTY_TRACKING_ENTRY;
  const next: TrackingEntry = {
    ...current,
    ...patch,
    updated_at: new Date().toISOString(),
  };
  const isEmpty = !next.status && !next.note && !next.deadline;
  const out = { ...state };
  if (isEmpty) {
    delete out[jobId];
  } else {
    out[jobId] = next;
  }
  return out;
}
