/**
 * Full result / evidence panel for a classified job.
 * Shows: label (conservative copy), reason (verbatim from engine),
 * evidence, employer match, what to verify, limitations, and disclaimer.
 *
 * IMPORTANT: The label copy must never contain "eligible", "you can apply",
 * "this role is safe", or "will sponsor". See CLAUDE.md.
 */
import type { ClassificationResult } from "../engine/types";
import type { PhraseSignal } from "../engine/types";
import { LABEL_DISPLAY } from "../labelCopy";
import { EvidencePanel } from "./EvidencePanel";
import { EmployerMatchPanel } from "./EmployerMatchPanel";
import { HighlightedDescription } from "./HighlightedDescription";

interface Props {
  result: ClassificationResult;
  phraseSignals: PhraseSignal[];
  descriptionText: string;
  applyUrl?: string;
}

/**
 * Only http(s) links are safe to render. A user-pasted "Source URL" must never
 * be allowed to carry a javascript: or data: scheme into an <a href>, which
 * would be an XSS vector (even self-XSS on a shared device).
 */
function isSafeHttpUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch {
    return false;
  }
}

export function ResultPanel({
  result,
  phraseSignals,
  descriptionText,
  applyUrl,
}: Props) {
  const labelDisplay = LABEL_DISPLAY[result.label];
  // CLAUDE.md: "Low confidence must remain visible to the user." Surface a
  // low-confidence employer signal next to the label, not only inside the
  // sponsor-register sub-panel.
  const lowConfidenceEmployer =
    result.employer_match.confidence_band === "low";

  return (
    <article className="result-panel" aria-label="Classification result">
      {/* ── Label + reason ─────────────────────────────────── */}
      <header className="result-header">
        <div
          className={`result-label ${labelDisplay.colorClass}`}
          data-testid="result-label"
          data-label={result.label}
        >
          <span className="label-tag">{labelDisplay.tag}</span>
          <span className="label-heading">{labelDisplay.heading}</span>
        </div>
        <p className="result-reason" data-testid="result-reason">
          {result.reason}
        </p>
        {lowConfidenceEmployer && (
          <p
            className="result-low-confidence"
            data-testid="result-low-confidence"
            role="note"
          >
            Low-confidence employer signal — treat this result with extra
            caution and verify the employer directly.
          </p>
        )}
      </header>

      {/* ── Disclaimer ─────────────────────────────────────── */}
      <aside className="disclaimer" role="note" aria-label="Disclaimer">
        <strong>Triage only, not immigration advice.</strong> This is a
        visa-risk triage tool that scans publicly available job text and a
        static sponsor-register snapshot. It does not replace advice from a
        qualified immigration adviser or solicitor.
      </aside>

      {/* ── Evidence ───────────────────────────────────────── */}
      <EvidencePanel evidence={result.evidence} />

      {/* ── Employer sponsor-register match ────────────────── */}
      <EmployerMatchPanel match={result.employer_match} />

      {/* ── Highlighted job description ────────────────────── */}
      {descriptionText && (
        <section className="description-section" aria-label="Job description">
          <h3>Job description with matched phrases</h3>
          <HighlightedDescription
            text={descriptionText}
            signals={phraseSignals}
          />
        </section>
      )}

      {/* ── What to verify ─────────────────────────────────── */}
      {result.what_to_verify.length > 0 && (
        <section
          className="what-to-verify"
          aria-label="What to verify with the employer"
        >
          <h3>What to verify with the employer</h3>
          <ul>
            {result.what_to_verify.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </section>
      )}

      {/* ── Limitations ────────────────────────────────────── */}
      {result.limitations.length > 0 && (
        <section className="limitations" aria-label="Limitations">
          <h3>Limitations</h3>
          <ul>
            {result.limitations.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </section>
      )}

      {/* ── Apply link (http/https only — see isSafeHttpUrl) ─── */}
      {applyUrl && isSafeHttpUrl(applyUrl) && (
        <section className="apply-link-section">
          <a
            href={applyUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-apply-link"
          >
            View original job posting ↗
          </a>
        </section>
      )}
    </article>
  );
}
