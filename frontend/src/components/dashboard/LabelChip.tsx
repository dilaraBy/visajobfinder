import type { Label } from "@/engine";
import { LABEL_DISPLAY } from "@/labelCopy";
import { cn } from "@/lib/utils";

/**
 * Editorial tag, not a pill. A short, uppercased, letter-spaced word with a
 * solid coloured left rule — reads like a magazine kicker or wire-service
 * label. Colour PLUS text, always: colour is never the only signal
 * (CLAUDE.md). The text "Worth applying" is visually tied to "No detected
 * blocker; verify with employer" in `LABEL_DISPLAY`.
 */
const TONE: Record<Label, { rule: string; text: string }> = {
  worth_applying: {
    rule: "border-l-[hsl(var(--label-worth))]",
    text: "text-[hsl(var(--label-worth))]",
  },
  verify_first: {
    rule: "border-l-[hsl(var(--label-verify))]",
    text: "text-[hsl(var(--label-verify))]",
  },
  likely_blocked: {
    rule: "border-l-[hsl(var(--label-blocked))]",
    text: "text-[hsl(var(--label-blocked))]",
  },
  unknown: {
    rule: "border-l-[hsl(var(--label-unknown))]",
    text: "text-[hsl(var(--label-unknown))]",
  },
};

export function LabelChip({
  label,
  className,
}: {
  label: Label;
  className?: string;
}) {
  const tone = TONE[label];
  return (
    <span
      data-label={label}
      className={cn(
        "inline-flex items-center border-l-[3px] pl-2 text-[10px] font-semibold uppercase leading-tight tracking-[0.08em]",
        tone.rule,
        tone.text,
        className
      )}
    >
      {LABEL_DISPLAY[label].tag}
    </span>
  );
}
