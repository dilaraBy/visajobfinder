import type { ClassificationResult } from "@/engine";
import type { PublicJob } from "@/lib/jobs";
import {
  TRACKING_STATUS_LABEL,
  type TrackingStatus,
} from "@/lib/tracking";
import { freshnessDisplay } from "@/lib/freshness";
import { cn } from "@/lib/utils";
import { LabelChip } from "./LabelChip";

interface Props {
  job: PublicJob;
  result: ClassificationResult;
  selected: boolean;
  trackingStatus?: TrackingStatus | null;
  onSelect: () => void;
}

/** A one-line evidence hint for the card (full evidence lives in the detail pane). */
function keyEvidence(job: PublicJob, result: ClassificationResult): string | null {
  const phrase = result.evidence.find((e) => e.type === "phrase" && e.text);
  if (phrase) return `“${phrase.text}”`;
  const match = job.visa_signals.employer_match;
  if (match.is_match && match.matched_name) {
    return `Sponsor-register match: ${match.matched_name}`;
  }
  return null;
}

export function JobCard({
  job,
  result,
  selected,
  trackingStatus,
  onSelect,
}: Props) {
  const fresh = freshnessDisplay(job);
  const location = job.location?.raw || job.location?.city || "Location not stated";
  const evidence = keyEvidence(job, result);

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "group w-full border-l-[3px] py-2.5 pl-3 pr-2 text-left transition-colors",
        "border-b border-b-[hsl(var(--border))]",
        "hover:bg-[hsl(var(--muted))]/40 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[hsl(var(--ring))]",
        selected
          ? "border-l-[hsl(var(--ring))] bg-[hsl(var(--muted))]/60"
          : "border-l-transparent"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-display text-[15px] font-semibold leading-[1.25] text-foreground">
          {job.title}
        </h3>
        <LabelChip label={result.label} className="shrink-0 pt-px" />
      </div>

      <p className="mt-0.5 text-[13px] text-foreground/85">
        {job.employer_raw || "Employer not stated"}
      </p>

      <div className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[11px] text-muted-foreground">
        <span>{location}</span>
        <span aria-hidden className="opacity-50">·</span>
        <span className="uppercase tracking-[0.12em]">{job.source}</span>
        <span aria-hidden className="opacity-50">·</span>
        <span className={cn(fresh.stale && "text-[hsl(var(--label-verify))]")}>
          {fresh.text}
        </span>
        {trackingStatus && (
          <>
            <span aria-hidden className="opacity-50">·</span>
            <span className="uppercase tracking-[0.12em] text-foreground">
              {TRACKING_STATUS_LABEL[trackingStatus]}
            </span>
          </>
        )}
      </div>

      {result.reason && (
        <p className="mt-1 line-clamp-2 text-[12px] text-foreground/75">
          {result.reason}
        </p>
      )}

      {evidence && (
        <p className="mt-0.5 line-clamp-1 text-[12px] italic text-muted-foreground">
          {evidence}
        </p>
      )}
    </button>
  );
}
