/**
 * Per-job tracking controls (status + note + deadline), persisted to
 * localStorage. Lives inside JobDetail. No network calls.
 */
import {
  EMPTY_TRACKING_ENTRY,
  TRACKING_STATUSES,
  TRACKING_STATUS_LABEL,
  type TrackingEntry,
  type TrackingStatus,
} from "@/lib/tracking";

interface Props {
  entry: TrackingEntry | undefined;
  onChange: (patch: Partial<TrackingEntry>) => void;
  onClear: () => void;
}

const INPUT_CLASS =
  "h-7 w-full rounded-md border border-[hsl(var(--border))] bg-transparent px-2 text-sm focus:outline-none focus:ring-1 focus:ring-[hsl(var(--ring))]";

export function JobTracking({ entry, onChange, onClear }: Props) {
  const current = entry ?? EMPTY_TRACKING_ENTRY;
  const hasAny = Boolean(current.status || current.note || current.deadline);

  return (
    <section
      className="space-y-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--muted))]/30 p-3"
      aria-labelledby="job-tracking-heading"
    >
      <div className="flex items-center justify-between">
        <h3
          id="job-tracking-heading"
          className="text-sm font-medium text-foreground"
        >
          Your tracking
        </h3>
        {hasAny && (
          <button
            type="button"
            onClick={onClear}
            className="text-[11px] text-muted-foreground underline-offset-2 hover:underline"
          >
            Clear
          </button>
        )}
      </div>
      <p className="text-[11px] text-muted-foreground">
        Stored only in this browser. Use Export to back up or move to another
        device.
      </p>

      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Status">
        <button
          type="button"
          onClick={() => onChange({ status: null })}
          className={statusBtnClass(current.status === null)}
          aria-pressed={current.status === null}
        >
          None
        </button>
        {TRACKING_STATUSES.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onChange({ status: s })}
            className={statusBtnClass(current.status === s)}
            aria-pressed={current.status === s}
          >
            {TRACKING_STATUS_LABEL[s]}
          </button>
        ))}
      </div>

      <label className="block text-xs">
        <span className="mb-1 block text-muted-foreground">Note</span>
        <textarea
          rows={3}
          className={`${INPUT_CLASS} h-auto py-1.5`}
          value={current.note}
          onChange={(e) => onChange({ note: e.target.value })}
          placeholder="Recruiter name, follow-up actions, salary question…"
        />
      </label>

      <label className="block text-xs">
        <span className="mb-1 block text-muted-foreground">Deadline</span>
        <input
          type="date"
          className={INPUT_CLASS}
          value={current.deadline}
          onChange={(e) => onChange({ deadline: e.target.value })}
        />
      </label>
    </section>
  );
}

function statusBtnClass(active: boolean): string {
  return [
    "rounded-full border px-2.5 py-0.5 text-[11px]",
    active
      ? "border-[hsl(var(--ring))] bg-[hsl(var(--ring))]/15 text-foreground"
      : "border-[hsl(var(--border))] text-muted-foreground hover:bg-[hsl(var(--muted))]",
  ].join(" ");
}

export function trackingBadge(status: TrackingStatus | null): string | null {
  if (!status) return null;
  return TRACKING_STATUS_LABEL[status];
}
