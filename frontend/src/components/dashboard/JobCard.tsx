import type { ClassificationResult } from "@/engine";
import type { PublicJob } from "@/lib/jobs";
import { freshnessDisplay } from "@/lib/freshness";
import { cn } from "@/lib/utils";
import { LabelChip } from "./LabelChip";

interface Props {
  job: PublicJob;
  result: ClassificationResult;
  selected: boolean;
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

export function JobCard({ job, result, selected, onSelect }: Props) {
  const fresh = freshnessDisplay(job);
  const location = job.location?.raw || job.location?.city || "Location not stated";
  const evidence = keyEvidence(job, result);

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "w-full rounded-lg border bg-card p-3 text-left transition-colors",
        "hover:border-[hsl(var(--ring))] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]",
        selected
          ? "border-[hsl(var(--ring))] ring-1 ring-[hsl(var(--ring))]"
          : "border-[hsl(var(--border))]"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold leading-snug">{job.title}</h3>
        <LabelChip label={result.label} className="shrink-0" />
      </div>

      <p className="mt-0.5 text-sm text-muted-foreground">
        {job.employer_raw || "Employer not stated"}
      </p>

      <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
        <span>{location}</span>
        <span aria-hidden>·</span>
        <span className="uppercase tracking-wide">{job.source}</span>
        <span aria-hidden>·</span>
        <span className={cn(fresh.stale && "text-[hsl(var(--label-verify))]")}>
          {fresh.text}
        </span>
      </div>

      <p className="mt-2 line-clamp-2 text-xs text-foreground/80">
        {result.reason}
      </p>

      {evidence && (
        <p className="mt-1.5 line-clamp-1 text-xs italic text-muted-foreground">
          {evidence}
        </p>
      )}
    </button>
  );
}
