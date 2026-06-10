/**
 * Renders a plain-text job description with matched phrase-signal spans
 * highlighted. Highlights use start_index/end_index from PhraseSignal.
 *
 * The text is split into: [before][highlight][between][highlight]…[after]
 * Non-overlapping spans only (the engine guarantees this).
 */
import type { PhraseSignal } from "../engine/types";
import { SEVERITY_CLASS } from "../labelCopy";

interface Props {
  text: string;
  signals: PhraseSignal[];
}

interface Segment {
  text: string;
  highlighted: boolean;
  severity?: string;
  ruleId?: string;
}

function buildSegments(text: string, signals: PhraseSignal[]): Segment[] {
  if (!text) return [];

  // Sort by start index (engine already sorts but be defensive)
  const sorted = [...signals].sort((a, b) => a.start_index - b.start_index);

  const segments: Segment[] = [];
  let cursor = 0;

  for (const signal of sorted) {
    const { start_index, end_index, severity, rule_id } = signal;
    if (start_index > cursor) {
      segments.push({ text: text.slice(cursor, start_index), highlighted: false });
    }
    if (end_index > start_index) {
      segments.push({
        text: text.slice(start_index, end_index),
        highlighted: true,
        severity,
        ruleId: rule_id,
      });
      cursor = end_index;
    }
  }

  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), highlighted: false });
  }

  return segments;
}

export function HighlightedDescription({ text, signals }: Props) {
  const segments = buildSegments(text, signals);

  return (
    <pre
      className="highlighted-description"
      aria-label="Job description with matched phrases highlighted"
    >
      {segments.map((seg, i) =>
        seg.highlighted ? (
          <mark
            key={i}
            className={`phrase-highlight ${SEVERITY_CLASS[seg.severity ?? ""] ?? ""}`}
            title={seg.ruleId ?? undefined}
            data-testid="phrase-highlight"
            data-severity={seg.severity}
          >
            {seg.text}
          </mark>
        ) : (
          <span key={i}>{seg.text}</span>
        )
      )}
    </pre>
  );
}
