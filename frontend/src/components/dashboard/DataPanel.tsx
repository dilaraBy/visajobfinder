/**
 * Export/import of the user's local data (visa profile + tracking). A single
 * JSON file moves between machines so v1 has no need for accounts. All work
 * happens client-side; no network calls.
 */
import { useId, useRef, useState } from "react";

import {
  buildExport,
  parseImport,
  type TrackingState,
  type ImportSummary,
} from "@/lib/tracking";
import type { VisaProfile } from "@/visaProfile";

interface Props {
  profile: VisaProfile;
  tracking: TrackingState;
  onImport: (profile: VisaProfile | null, tracking: TrackingState) => void;
}

export function DataPanel({ profile, tracking, onImport }: Props) {
  const fileInputId = useId();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [feedback, setFeedback] = useState<
    | { kind: "ok"; summary: ImportSummary }
    | { kind: "error"; message: string }
    | null
  >(null);

  function downloadJson() {
    const data = buildExport(profile, tracking);
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    const stamp = new Date().toISOString().slice(0, 10);
    link.download = `visajobfinder-${stamp}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function onFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow re-selecting the same file
    if (!file) return;
    file
      .text()
      .then((text) => {
        const parsed = parseImport(text);
        onImport(parsed.profile, parsed.tracking);
        setFeedback({ kind: "ok", summary: parsed.summary });
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : String(err);
        setFeedback({ kind: "error", message });
      });
  }

  return (
    <section
      className="space-y-2 border-b border-[hsl(var(--border))] px-3 py-2"
      aria-labelledby="data-panel-heading"
    >
      <h3
        id="data-panel-heading"
        className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground"
      >
        Your data
      </h3>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={downloadJson}
          className="h-7 rounded-md border border-[hsl(var(--border))] px-2 text-xs hover:bg-[hsl(var(--muted))]"
        >
          Export JSON
        </button>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="h-7 rounded-md border border-[hsl(var(--border))] px-2 text-xs hover:bg-[hsl(var(--muted))]"
        >
          Import JSON
        </button>
        <input
          id={fileInputId}
          ref={fileInputRef}
          type="file"
          accept="application/json,.json"
          className="hidden"
          onChange={onFileChange}
        />
      </div>
      {feedback?.kind === "ok" && (
        <p
          className="text-[11px] text-muted-foreground"
          role="status"
        >
          Imported {feedback.summary.trackedJobs} tracked job
          {feedback.summary.trackedJobs === 1 ? "" : "s"}
          {feedback.summary.profileImported ? " and visa profile" : ""}.
          {feedback.summary.errors.length > 0 && (
            <>
              {" "}
              <span className="text-[hsl(var(--label-blocked))]">
                Notes: {feedback.summary.errors.join("; ")}
              </span>
            </>
          )}
        </p>
      )}
      {feedback?.kind === "error" && (
        <p
          className="text-[11px] text-[hsl(var(--label-blocked))]"
          role="alert"
        >
          Import failed: {feedback.message}
        </p>
      )}
    </section>
  );
}
