/**
 * Paste-a-Job Checker page.
 *
 * Data flow:
 *   1. Visa profile persisted to localStorage (browser only, no server).
 *   2. User pastes job fields and submits.
 *   3. Client-side TS engine classifies the job (no network call).
 *   4. Result + evidence panel renders.
 *
 * The only network request is the one-time fetch of /sponsors.json at startup
 * (the real GOV.UK register). No analytics, no telemetry, no external CDN.
 */
import { useEffect, useRef, useState } from "react";
import "../app.css";

import { analyseJob } from "@/engine/engine";
import type { AnalyseResult } from "@/engine/engine";
import { SponsorMatcher } from "@/engine/sponsorMatcher";
import type { SponsorRegisterFile } from "@/engine/sponsorData";
import { matcherFromFile } from "@/engine/sponsorData";

import { useLocalStorage } from "@/hooks/useLocalStorage";
import type { VisaProfile } from "@/visaProfile";
import {
  DEFAULT_VISA_PROFILE,
  VISA_PROFILE_STORAGE_KEY,
  userContextFromProfile,
} from "@/visaProfile";

import { VisaProfileForm } from "@/components/VisaProfileForm";
import { PasteJobForm } from "@/components/PasteJobForm";
import type { JobFormValues } from "@/components/PasteJobForm";
import { ResultPanel } from "@/components/ResultPanel";

type CheckState =
  | { status: "loading_sponsors" }
  | { status: "sponsor_error"; message: string }
  | { status: "ready"; result: null }
  | { status: "ready"; result: AnalyseResult; description: string; applyUrl: string };

export function CheckPage() {
  const matcherRef = useRef<SponsorMatcher | null>(null);
  const [appState, setAppState] = useState<CheckState>({
    status: "loading_sponsors",
  });

  const [profile, setProfile, resetProfile] = useLocalStorage<VisaProfile>(
    VISA_PROFILE_STORAGE_KEY,
    DEFAULT_VISA_PROFILE
  );

  // Load the sponsor register once on mount.
  useEffect(() => {
    let cancelled = false;
    fetch(`${import.meta.env.BASE_URL}sponsors.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<SponsorRegisterFile>;
      })
      .then((file) => {
        if (cancelled) return;
        matcherRef.current = matcherFromFile(file);
        setAppState({ status: "ready", result: null });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : String(err);
        setAppState({ status: "sponsor_error", message: msg });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleJobSubmit(values: JobFormValues) {
    if (!matcherRef.current) return;

    const jobInput = {
      job_id: "paste:manual",
      source: "paste",
      title: values.title,
      employer_raw: values.employer,
      description_text: values.description,
      location: values.location || null,
      salary_text: values.salary_text || null,
      url: values.source_url || null,
    };

    const result = analyseJob(
      jobInput,
      userContextFromProfile(profile),
      matcherRef.current
    );
    setAppState({
      status: "ready",
      result,
      description: values.description,
      applyUrl: values.source_url,
    });
  }

  const isLoading = appState.status === "loading_sponsors";
  const hasResult = appState.status === "ready" && appState.result !== null;

  return (
    <div className="mx-auto max-w-6xl p-4">
      {appState.status === "sponsor_error" && (
        <div className="error-state" role="alert">
          <strong>Could not load the sponsor register:</strong>{" "}
          {appState.message}. Sponsor-register matching will not work.
        </div>
      )}

      <div className="main-columns">
        <div className="left-column">
          <VisaProfileForm
            profile={profile}
            onChange={setProfile}
            onReset={resetProfile}
          />
          <PasteJobForm onSubmit={handleJobSubmit} isLoading={isLoading} />
        </div>

        <div className="right-column">
          {appState.status === "loading_sponsors" && (
            <div className="loading-state" role="status" aria-live="polite">
              Loading sponsor register…
            </div>
          )}

          {appState.status === "ready" && !hasResult && (
            <div className="idle-state">
              Paste a job on the left and click <strong>Check this job</strong>{" "}
              to see the visa-risk triage result here.
            </div>
          )}

          {hasResult && appState.status === "ready" && appState.result !== null && (
            <ResultPanel
              result={appState.result.classification}
              phraseSignals={appState.result.phrase_signals}
              descriptionText={appState.description}
              applyUrl={appState.applyUrl}
            />
          )}
        </div>
      </div>
    </div>
  );
}
