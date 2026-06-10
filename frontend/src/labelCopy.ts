/**
 * Conservative display copy for visa-risk labels.
 *
 * IMPORTANT: These strings must never contain "eligible", "you can apply",
 * "this role is safe", or "will sponsor". See CLAUDE.md Product Truth.
 *
 * Labels map to display text exactly as specified:
 *  worth_applying  → "Worth applying — no detected blocker; verify with employer"
 *  verify_first    → "Verify first"
 *  likely_blocked  → "Likely blocked"
 *  unknown         → "Unknown"
 */

import type { Label } from "./engine/types";

export interface LabelDisplay {
  heading: string;
  tag: string;
  colorClass: string;
}

export const LABEL_DISPLAY: Record<Label, LabelDisplay> = {
  worth_applying: {
    heading: "Worth applying — no detected blocker; verify with employer",
    tag: "Worth applying",
    colorClass: "label-worth-applying",
  },
  verify_first: {
    heading: "Verify first",
    tag: "Verify first",
    colorClass: "label-verify-first",
  },
  likely_blocked: {
    heading: "Likely blocked",
    tag: "Likely blocked",
    colorClass: "label-likely-blocked",
  },
  unknown: {
    heading: "Unknown",
    tag: "Unknown",
    colorClass: "label-unknown",
  },
};

/** Severity to CSS class for phrase signal rows */
export const SEVERITY_CLASS: Record<string, string> = {
  red: "severity-red",
  amber: "severity-amber",
  green: "severity-green",
};
