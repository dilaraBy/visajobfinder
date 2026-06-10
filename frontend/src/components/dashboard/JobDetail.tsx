import type { ClassificationResult } from "@/engine";
import type { PublicJob } from "@/lib/jobs";
import { freshnessDisplay } from "@/lib/freshness";
import { ResultPanel } from "@/components/ResultPanel";

interface Props {
  job: PublicJob;
  result: ClassificationResult;
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2 text-sm">
      <span className="w-24 shrink-0 text-muted-foreground">{label}</span>
      <span className="text-foreground">{value}</span>
    </div>
  );
}

export function JobDetail({ job, result }: Props) {
  const fresh = freshnessDisplay(job);
  const location = job.location?.raw || job.location?.city || "Not stated";

  return (
    <div className="space-y-4">
      <header className="space-y-2 border-b border-[hsl(var(--border))] pb-4">
        <h2 className="text-lg font-semibold leading-tight">{job.title}</h2>
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
    </div>
  );
}
