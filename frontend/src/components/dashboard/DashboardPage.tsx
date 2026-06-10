import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useLocalStorage } from "@/hooks/useLocalStorage";
import {
  DEFAULT_VISA_PROFILE,
  VISA_PROFILE_STORAGE_KEY,
  userContextFromProfile,
  type VisaProfile,
} from "@/visaProfile";
import { VisaProfileForm } from "@/components/VisaProfileForm";
import {
  classifyPublicJob,
  loadJobs,
  type PublicJob,
  type PublicJobsFile,
} from "@/lib/jobs";
import type { ClassificationResult } from "@/engine";
import { JobCard } from "./JobCard";
import { JobDetail } from "./JobDetail";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; file: PublicJobsFile };

interface ClassifiedJob {
  job: PublicJob;
  result: ClassificationResult;
}

export function DashboardPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [searchParams, setSearchParams] = useSearchParams();
  const [profile, setProfile, resetProfile] = useLocalStorage<VisaProfile>(
    VISA_PROFILE_STORAGE_KEY,
    DEFAULT_VISA_PROFILE
  );

  useEffect(() => {
    let cancelled = false;
    loadJobs()
      .then((file) => !cancelled && setState({ status: "ready", file }))
      .catch(
        (err: unknown) =>
          !cancelled &&
          setState({
            status: "error",
            message: err instanceof Error ? err.message : String(err),
          })
      );
    return () => {
      cancelled = true;
    };
  }, []);

  // Re-classify (memoised) whenever the jobs or the profile change.
  const classified = useMemo<ClassifiedJob[]>(() => {
    if (state.status !== "ready") return [];
    const user = userContextFromProfile(profile);
    return state.file.jobs.map((job) => ({
      job,
      result: classifyPublicJob(job, user),
    }));
  }, [state, profile]);

  const selectedId = searchParams.get("job");
  const selected =
    classified.find((c) => c.job.job_id === selectedId) ?? null;

  function select(jobId: string) {
    const next = new URLSearchParams(searchParams);
    next.set("job", jobId);
    setSearchParams(next, { replace: true });
  }

  if (state.status === "loading") {
    return (
      <div className="p-8 text-sm text-muted-foreground" role="status">
        Loading jobs…
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <div className="m-6 rounded-lg border border-[hsl(var(--label-blocked))] bg-[hsl(var(--label-blocked-bg))] p-4 text-sm" role="alert">
        <strong>Could not load jobs:</strong> {state.message}
      </div>
    );
  }

  return (
    <div className="grid h-[calc(100vh-3.5rem)] grid-cols-1 md:grid-cols-[minmax(20rem,26rem)_1fr]">
      {/* Left pane — profile + list */}
      <div className="flex flex-col overflow-hidden border-r border-[hsl(var(--border))]">
        <div className="border-b border-[hsl(var(--border))] p-3">
          <VisaProfileForm
            profile={profile}
            onChange={setProfile}
            onReset={resetProfile}
          />
        </div>
        <div className="flex items-center justify-between px-3 py-2 text-xs text-muted-foreground">
          <span>{classified.length} jobs</span>
          <span>Updated {new Date(state.file.generated_at).toLocaleDateString()}</span>
        </div>
        <ul className="flex-1 space-y-2 overflow-y-auto p-3 pt-0">
          {classified.map(({ job, result }) => (
            <li key={job.job_id}>
              <JobCard
                job={job}
                result={result}
                selected={job.job_id === selectedId}
                onSelect={() => select(job.job_id)}
              />
            </li>
          ))}
        </ul>
      </div>

      {/* Right pane — detail */}
      <div className="overflow-y-auto p-5">
        {selected ? (
          <JobDetail job={selected.job} result={selected.result} />
        ) : (
          <div className="flex h-full items-center justify-center p-8 text-center text-sm text-muted-foreground">
            <div>
              <p>Select a job to see its visa-risk triage and evidence.</p>
              {profile.visa_situation === "unknown" && (
                <p className="mt-2">
                  Tip: set your visa situation above for status-aware labels.
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
