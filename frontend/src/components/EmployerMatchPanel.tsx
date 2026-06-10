/**
 * Shows the employer sponsor-register match details.
 * When is_match is false, says "No sponsor-register match found in the loaded data"
 * — NOT "employer cannot sponsor" (per CLAUDE.md Product Truth).
 */
import type { EmployerMatch } from "../engine/types";

interface Props {
  match: EmployerMatch;
}

export function EmployerMatchPanel({ match }: Props) {
  return (
    <section
      className="employer-match-panel"
      aria-label="Employer sponsor-register check"
    >
      <h3>Sponsor-register check</h3>

      {match.is_match ? (
        <div className="employer-match employer-match--found">
          <p className="match-status match-status--found">
            Sponsor-register match found
          </p>
          <dl className="match-details">
            <dt>Matched name</dt>
            <dd>{match.matched_name}</dd>

            <dt>Confidence band</dt>
            <dd>
              <span
                className={`confidence-badge confidence-badge--${match.confidence_band}`}
              >
                {match.confidence_band}
              </span>{" "}
              ({(match.confidence * 100).toFixed(1)}%)
            </dd>

            <dt>Match method</dt>
            <dd>{match.match_method ?? "—"}</dd>

            {match.sponsor_routes.length > 0 && (
              <>
                <dt>Sponsor routes</dt>
                <dd>{match.sponsor_routes.join(", ")}</dd>
              </>
            )}

            {match.rating && (
              <>
                <dt>Rating</dt>
                <dd>{match.rating}</dd>
              </>
            )}

            {match.location && (
              <>
                <dt>Location on register</dt>
                <dd>{match.location}</dd>
              </>
            )}
          </dl>
        </div>
      ) : (
        <div className="employer-match employer-match--none">
          <p className="match-status match-status--none">
            No sponsor-register match found in the loaded data
          </p>
          {match.matched_name && (
            <p className="match-low-candidate">
              Low-confidence candidate: {match.matched_name} (
              {(match.confidence * 100).toFixed(1)}%)
            </p>
          )}
          <p className="match-caveat">
            This does not mean the employer lacks a licence — the loaded
            register data may be incomplete or outdated.
          </p>
        </div>
      )}

      <div className="match-provenance">
        <span className="provenance-label">Register source:</span>{" "}
        {match.source_name ?? "Unknown"}
        {match.source_published_at && (
          <> · Published: {match.source_published_at}</>
        )}
        {match.source_downloaded_at && (
          <> · Downloaded: {match.source_downloaded_at}</>
        )}
      </div>
    </section>
  );
}
