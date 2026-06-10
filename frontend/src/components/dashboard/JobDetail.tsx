import type { ClassificationResult } from "@/engine";
import type { PublicJob } from "@/lib/jobs";
import type { TrackingEntry } from "@/lib/tracking";
import { freshnessDisplay } from "@/lib/freshness";
import { ResultPanel } from "@/components/ResultPanel";
import { JobTracking } from "./JobTracking";

interface Props {
  job: PublicJob;
  result: ClassificationResult;
  tracking?: TrackingEntry;
  onTrackingChange: (patch: Partial<TrackingEntry>) => void;
  onTrackingClear: () => void;
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-3 text-[13px]">
      <span className="w-20 shrink-0 text-[10px] uppercase tracking-[0.12em] text-muted-foreground pt-1">
        {label}
      </span>
      <span className="text-foreground">{value}</span>
    </div>
  );
}

export function JobDetail({
  job,
  result,
  tracking,
  onTrackingChange,
  onTrackingClear,
}: Props) {
  const fresh = freshnessDisplay(job);
  const location = job.location?.raw || job.location?.city || "Not stated";

  return (
    <div className="space-y-4">
      <header className="space-y-3 border-b border-[hsl(var(--border))] pb-4">
        <h2 className="font-display text-[1.6rem] font-semibold leading-[1.15] tracking-tight text-foreground">
          {job.title}
        </h2>
        <div className="space-y-1">
          <MetaRow label="Employer" value={job.employer_raw || "Not stated"} />
          <MetaRow label="Location" value={location} />
          <MetaRow label="Source" value={job.source.toUpperCase()} />
          <MetaRow
            label="Salary"
            value={job.salary?.raw || "Not stated"}
          />
          <MetaRow label="Freshness" value={fresh.text} />
        </div>
      </header>

      {/* Reused evidence panel keeps the dashboard and paste-checker identical. */}
      <ResultPanel
        result={result}
        phraseSignals={job.visa_signals.phrase_signals}
        descriptionText={job.description_text}
        applyUrl={job.url ?? undefined}
      />

      <JobTracking
        entry={tracking}
        onChange={onTrackingChange}
        onClear={onTrackingClear}
      />
    </div>
  );
}
