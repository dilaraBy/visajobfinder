import type { Label } from "@/engine";
import { LABEL_DISPLAY } from "@/labelCopy";
import { cn } from "@/lib/utils";

// Colour PLUS text, always — colour-blind safe. Green = "no detected blocker",
// never "safe"; the copy in LABEL_DISPLAY reinforces this.
const TONE: Record<Label, string> = {
  worth_applying:
    "text-[hsl(var(--label-worth))] bg-[hsl(var(--label-worth-bg))]",
  verify_first:
    "text-[hsl(var(--label-verify))] bg-[hsl(var(--label-verify-bg))]",
  likely_blocked:
    "text-[hsl(var(--label-blocked))] bg-[hsl(var(--label-blocked-bg))]",
  unknown:
    "text-[hsl(var(--label-unknown))] bg-[hsl(var(--label-unknown-bg))]",
};

export function LabelChip({
  label,
  className,
}: {
  label: Label;
  className?: string;
}) {
  return (
    <span
      data-label={label}
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
        TONE[label],
        className
      )}
    >
      {LABEL_DISPLAY[label].tag}
    </span>
  );
}
