/**
 * Displays the evidence list from a ClassificationResult.
 * Found evidence and missing_evidence items are both shown prominently.
 * A classification without evidence is not acceptable — see CLAUDE.md.
 */
import type { EvidenceItem } from "../engine/types";
import { SEVERITY_CLASS } from "../labelCopy";

interface Props {
  evidence: EvidenceItem[];
}

function evidenceTypeLabel(type: string): string {
  switch (type) {
    case "phrase_signal":
      return "Phrase match";
    case "sponsor_register":
      return "Sponsor register";
    case "missing_evidence":
      return "Missing evidence";
    default:
      return type;
  }
}

function categoryLabel(category: string): string {
  switch (category) {
    case "citizenship_required":
      return "Citizenship requirement";
    case "permanent_right_to_work":
      return "Permanent / unrestricted RTW";
    case "no_sponsorship":
      return "No sponsorship";
    case "future_sponsorship_risk":
      return "Future sponsorship risk";
    case "sponsorship_positive":
      return "Sponsorship positive";
    case "security_clearance":
      return "Security clearance";
    case "ambiguous":
      return "Ambiguous";
    case "sponsor_match":
      return "Sponsor register match";
    case "low_confidence_candidate":
      return "Low-confidence sponsor candidate";
    case "jd_phrase":
      return "Phrase scanning";
    default:
      return category;
  }
}

export function EvidencePanel({ evidence }: Props) {
  const found = evidence.filter((e) => e.type !== "missing_evidence");
  const missing = evidence.filter((e) => e.type === "missing_evidence");

  return (
    <section className="evidence-panel" aria-label="Evidence">
      <h3>Evidence</h3>

      {evidence.length === 0 && (
        <div
          className="evidence-group evidence-group--missing"
          data-testid="evidence-empty"
        >
          <p className="evidence-text">
            No evidence was returned for this result. A classification without
            evidence is not reliable — verify the role directly with the
            employer.
          </p>
        </div>
      )}

      {found.length > 0 && (
        <div className="evidence-group evidence-group--found">
          <h4 className="evidence-group-heading evidence-group-heading--found">
            Evidence found ({found.length})
          </h4>
          <ul className="evidence-list">
            {found.map((item, i) => (
              <li
                key={i}
                className={`evidence-item evidence-item--${item.type} ${
                  item.severity ? SEVERITY_CLASS[item.severity] : ""
                }`}
                data-testid="evidence-item"
                data-type={item.type}
              >
                <span className="evidence-type-badge">
                  {evidenceTypeLabel(item.type)}
                </span>
                {item.category && (
                  <span className="evidence-category">
                    {categoryLabel(item.category)}
                  </span>
                )}
                {item.severity && (
                  <span
                    className={`evidence-severity ${SEVERITY_CLASS[item.severity]}`}
                    aria-label={`severity: ${item.severity}`}
                  >
                    {item.severity.toUpperCase()}
                  </span>
                )}
                <p className="evidence-text">{item.text}</p>
                {item.rule_id && (
                  <span className="evidence-rule-id">Rule: {item.rule_id}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {missing.length > 0 && (
        <div
          className="evidence-group evidence-group--missing"
          data-testid="missing-evidence-group"
        >
          <h4 className="evidence-group-heading evidence-group-heading--missing">
            Missing evidence ({missing.length})
          </h4>
          <ul className="evidence-list">
            {missing.map((item, i) => (
              <li
                key={i}
                className="evidence-item evidence-item--missing"
                data-testid="missing-evidence-item"
              >
                <span className="evidence-type-badge evidence-type-badge--missing">
                  Missing
                </span>
                {item.category && (
                  <span className="evidence-category">
                    {categoryLabel(item.category)}
                  </span>
                )}
                <p className="evidence-text">{item.text}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
