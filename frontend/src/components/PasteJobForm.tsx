/**
 * Paste-a-Job form. Captures the fields needed for JobInput and calls
 * onSubmit when the user clicks "Check this job".
 */
import { useState } from "react";

export interface JobFormValues {
  title: string;
  employer: string;
  location: string;
  salary_text: string;
  source_url: string;
  description: string;
}

const EMPTY: JobFormValues = {
  title: "",
  employer: "",
  location: "",
  salary_text: "",
  source_url: "",
  description: "",
};

interface Props {
  onSubmit: (values: JobFormValues) => void;
  isLoading: boolean;
}

export function PasteJobForm({ onSubmit, isLoading }: Props) {
  const [values, setValues] = useState<JobFormValues>(EMPTY);

  function set<K extends keyof JobFormValues>(key: K, value: string) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit(values);
  }

  function handleClear() {
    setValues(EMPTY);
  }

  return (
    <form
      className="paste-job-form"
      onSubmit={handleSubmit}
      aria-label="Paste a job to check"
    >
      <h2>Paste a job to check</h2>

      <div className="form-row">
        <label htmlFor="job-title">Job title</label>
        <input
          type="text"
          id="job-title"
          placeholder="e.g. Software Engineer"
          value={values.title}
          onChange={(e) => set("title", e.target.value)}
        />
      </div>

      <div className="form-row">
        <label htmlFor="job-employer">
          Employer name <span className="field-required">(required for sponsor-register check)</span>
        </label>
        <input
          type="text"
          id="job-employer"
          placeholder="e.g. Acme Ltd"
          value={values.employer}
          onChange={(e) => set("employer", e.target.value)}
        />
      </div>

      <div className="form-row">
        <label htmlFor="job-location">Location <span className="field-hint">(optional)</span></label>
        <input
          type="text"
          id="job-location"
          placeholder="e.g. London, UK"
          value={values.location}
          onChange={(e) => set("location", e.target.value)}
        />
      </div>

      <div className="form-row">
        <label htmlFor="job-salary">
          Salary{" "}
          <span className="field-hint">
            (optional — affects the Skilled Worker salary check)
          </span>
        </label>
        <input
          type="text"
          id="job-salary"
          placeholder="e.g. £35,000–£45,000"
          value={values.salary_text}
          onChange={(e) => set("salary_text", e.target.value)}
        />
        <p className="field-hint">
          Paste the salary from the ad. A missing or non-numeric salary adds a
          verification flag for sponsorship-before-start situations.
        </p>
      </div>

      <div className="form-row">
        <label htmlFor="job-url">Source URL <span className="field-hint">(optional)</span></label>
        <input
          type="url"
          id="job-url"
          placeholder="https://..."
          value={values.source_url}
          onChange={(e) => set("source_url", e.target.value)}
        />
      </div>

      <div className="form-row form-row--full">
        <label htmlFor="job-description">
          Job description <span className="field-required">(required for phrase scanning)</span>
        </label>
        <textarea
          id="job-description"
          rows={12}
          placeholder="Paste the full job description here…"
          value={values.description}
          onChange={(e) => set("description", e.target.value)}
        />
      </div>

      <div className="form-actions">
        <button
          type="submit"
          className="btn-primary"
          disabled={isLoading}
          aria-busy={isLoading}
        >
          {isLoading ? "Checking…" : "Check this job"}
        </button>
        <button
          type="button"
          className="btn-secondary"
          onClick={handleClear}
          disabled={isLoading}
        >
          Clear
        </button>
      </div>
    </form>
  );
}
