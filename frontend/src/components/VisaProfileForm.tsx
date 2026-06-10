/**
 * Visa situation controls. Values persist in localStorage.
 * Personal data stays browser-local; nothing is sent to any server.
 */
import type { VisaProfile } from "../visaProfile";
import { VISA_SITUATION_LABELS } from "../visaProfile";
import { ALLOWED_VISA_SITUATIONS } from "../engine/types";

interface Props {
  profile: VisaProfile;
  onChange: (profile: VisaProfile) => void;
  onReset: () => void;
}

export function VisaProfileForm({ profile, onChange, onReset }: Props) {
  function set<K extends keyof VisaProfile>(key: K, value: VisaProfile[K]) {
    onChange({ ...profile, [key]: value });
  }

  return (
    <section className="visa-profile-form" aria-label="Your visa situation">
      <div className="profile-header">
        <h2>Your visa situation</h2>
        <span className="data-local-note" role="note">
          Your data stays in this browser only — nothing is sent to any server.
        </span>
        <button
          type="button"
          className="btn-reset"
          onClick={onReset}
          aria-label="Clear saved visa profile"
        >
          Reset profile
        </button>
      </div>

      <div className="form-row">
        <label htmlFor="visa-situation">Visa situation</label>
        <select
          id="visa-situation"
          value={profile.visa_situation}
          onChange={(e) =>
            set(
              "visa_situation",
              e.target.value as VisaProfile["visa_situation"]
            )
          }
        >
          {ALLOWED_VISA_SITUATIONS.map((s) => (
            <option key={s} value={s}>
              {VISA_SITUATION_LABELS[s]}
            </option>
          ))}
        </select>
      </div>

      <div className="form-row form-row--checkbox">
        <input
          type="checkbox"
          id="needs-sponsorship-before-start"
          checked={profile.needs_sponsorship_before_start}
          onChange={(e) =>
            set("needs_sponsorship_before_start", e.target.checked)
          }
        />
        <label htmlFor="needs-sponsorship-before-start">
          I need a work visa before the job start date
        </label>
        <p className="field-hint field-hint--checkbox">
          Tick this if you are not on a work visa yet, or your current visa
          expires before the role starts. It applies the stricter
          sponsorship-before-start rules.
        </p>
      </div>

      <div className="form-row form-row--checkbox">
        <input
          type="checkbox"
          id="needs-future-sponsorship"
          checked={profile.needs_future_sponsorship}
          onChange={(e) => set("needs_future_sponsorship", e.target.checked)}
        />
        <label htmlFor="needs-future-sponsorship">
          I may need Skilled Worker sponsorship in future (e.g. after Graduate
          Route expires)
        </label>
        <p className="field-hint field-hint--checkbox">
          Most relevant for Graduate Route holders. Enables checks for
          future-sponsorship wording in the job description.
        </p>
      </div>

      <div className="form-row">
        <label htmlFor="visa-expiry-month">
          Visa expiry month{" "}
          <span className="field-hint">(YYYY-MM, optional)</span>
        </label>
        <input
          type="text"
          id="visa-expiry-month"
          placeholder="e.g. 2025-09"
          value={profile.visa_expiry_month}
          pattern="\d{4}-\d{2}"
          maxLength={7}
          onChange={(e) => set("visa_expiry_month", e.target.value)}
        />
      </div>

      <div className="form-row">
        <label htmlFor="target-start-month">
          Target start month{" "}
          <span className="field-hint">(YYYY-MM, optional)</span>
        </label>
        <input
          type="text"
          id="target-start-month"
          placeholder="e.g. 2025-11"
          value={profile.target_start_month}
          pattern="\d{4}-\d{2}"
          maxLength={7}
          onChange={(e) => set("target_start_month", e.target.value)}
        />
      </div>
    </section>
  );
}
