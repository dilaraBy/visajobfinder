import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Menu } from "lucide-react";

import { useLocalStorage } from "@/hooks/useLocalStorage";
import {
  DEFAULT_VISA_PROFILE,
  VISA_PROFILE_STORAGE_KEY,
  userContextFromProfile,
  type VisaProfile,
} from "@/visaProfile";
import {
  classifyPublicJob,
  loadJobs,
  type PublicJobsFile,
} from "@/lib/jobs";
import {
  DEFAULT_FILTERS,
  applyFilters,
  availableCategories,
  availableSources,
  filtersFromParams,
  paramsWithFilters,
  parseKeywords,
  toggleKeyword,
  type ClassifiedJob,
  type FilterState,
} from "@/lib/filters";
import {
  TRACKING_STORAGE_KEY,
  withEntry,
  type TrackingEntry,
  type TrackingState,
} from "@/lib/tracking";
import { JobCard } from "./JobCard";
import { JobDetail } from "./JobDetail";
import { FilterBar } from "./FilterBar";
import { JobInterests } from "./JobInterests";
import { ProfileDrawer, PROFILE_DRAWER_ID } from "./ProfileDrawer";

const DRAWER_OPEN_STORAGE_KEY = "vjf_drawer_open_v1";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; file: PublicJobsFile };

export function DashboardPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [searchParams, setSearchParams] = useSearchParams();
  const [storedProfile, setProfile, resetProfile] = useLocalStorage<VisaProfile>(
    VISA_PROFILE_STORAGE_KEY,
    DEFAULT_VISA_PROFILE
  );
  // Merge over defaults so a profile saved before a new field existed (e.g. a
  // returning visitor without target_keywords) can never crash on a missing
  // field. Memoised so identity only changes when the stored value changes.
  const profile = useMemo<VisaProfile>(
    () => ({ ...DEFAULT_VISA_PROFILE, ...storedProfile }),
    [storedProfile]
  );
  const [tracking, setTracking] = useLocalStorage<TrackingState>(
    TRACKING_STORAGE_KEY,
    {}
  );
  const [drawerOpen, setDrawerOpen] = useLocalStorage<boolean>(
    DRAWER_OPEN_STORAGE_KEY,
    false
  );
  const hamburgerRef = useRef<HTMLButtonElement>(null);

  function patchTracking(jobId: string, patch: Partial<TrackingEntry>) {
    setTracking(withEntry(tracking, jobId, patch));
  }

  function clearTracking(jobId: string) {
    const next = { ...tracking };
    delete next[jobId];
    setTracking(next);
  }

  function handleImport(
    importedProfile: VisaProfile | null,
    importedTracking: TrackingState
  ) {
    if (importedProfile) setProfile(importedProfile);
    setTracking({ ...tracking, ...importedTracking });
  }

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

  // Derive the engine's UserContext from only the classification-relevant
  // fields, so editing job interests (target_keywords) does NOT re-run
  // classification — keywords only filter/rank the display.
  const user = useMemo(
    () => userContextFromProfile(profile),
    [
      profile.visa_situation,
      profile.visa_expiry_month,
      profile.needs_sponsorship_before_start,
      profile.needs_future_sponsorship,
      profile.target_start_month,
    ]
  );

  // Re-classify (memoised) whenever the jobs or the visa context change.
  const classified = useMemo<ClassifiedJob[]>(() => {
    if (state.status !== "ready") return [];
    return state.file.jobs.map((job) => ({
      job,
      result: classifyPublicJob(job, user),
    }));
  }, [state, user]);

  const filters = useMemo(() => filtersFromParams(searchParams), [searchParams]);
  const visible = useMemo(
    () => applyFilters(classified, filters),
    [classified, filters]
  );
  const sources = useMemo(() => availableSources(classified), [classified]);
  const categories = useMemo(
    () => availableCategories(classified),
    [classified]
  );

  // Seed the live keyword filter from the saved profile once, when the URL
  // carries no `q` yet, so a returning user sees their interests applied.
  const seededRef = useRef(false);
  useEffect(() => {
    if (seededRef.current) return;
    seededRef.current = true;
    if (!searchParams.get("q") && profile.target_keywords.length > 0) {
      const next = new URLSearchParams(searchParams);
      next.set("q", profile.target_keywords.join(", "));
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectedId = searchParams.get("job");
  // If a selection is filtered out, drop it so the detail pane doesn't show a
  // stale card; the user can re-select from the visible list.
  const selected = visible.find((c) => c.job.job_id === selectedId) ?? null;

  function select(jobId: string) {
    const next = new URLSearchParams(searchParams);
    next.set("job", jobId);
    setSearchParams(next, { replace: true });
  }

  function updateFilters(nextFilters: FilterState) {
    const next = paramsWithFilters(searchParams, nextFilters);
    // Drop the selected-job param when the filters would hide it.
    const selId = next.get("job");
    if (selId) {
      const stillVisible = applyFilters(classified, nextFilters).some(
        (c) => c.job.job_id === selId
      );
      if (!stillVisible) next.delete("job");
    }
    setSearchParams(next, { replace: true });
  }

  function resetFilters() {
    updateFilters(DEFAULT_FILTERS);
  }

  // Keyword edits update the live filter (URL) and persist the saved interests
  // (profile), so the view is both shareable and remembered next visit.
  function setKeyword(next: string) {
    updateFilters({ ...filters, keyword: next });
    setProfile({ ...profile, target_keywords: parseKeywords(next) });
  }

  function toggleCategory(category: string) {
    setKeyword(toggleKeyword(filters.keyword, category));
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

  const profileUnset = profile.visa_situation === "unknown";

  return (
    <div className="grid h-[calc(100vh-3.5rem)] grid-cols-1 md:grid-cols-[minmax(24rem,34rem)_1fr]">
      {/* Left pane — toolbar + job list (the main event) */}
      <div className="flex flex-col overflow-hidden border-r border-[hsl(var(--border))]">
        <div className="flex items-center gap-2 border-b border-[hsl(var(--border))] px-3 py-2">
          <button
            ref={hamburgerRef}
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-haspopup="dialog"
            aria-expanded={drawerOpen}
            aria-controls={PROFILE_DRAWER_ID}
            aria-label={
              profileUnset
                ? "Open visa profile (visa situation not set)"
                : "Open visa profile and settings"
            }
            className="relative inline-flex h-7 w-7 items-center justify-center rounded-md border border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))]"
          >
            <Menu className="h-4 w-4" />
            {profileUnset && (
              <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-[hsl(var(--label-verify))]" />
            )}
          </button>
          <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
            Visa profile &amp; data
          </span>
          <span className="ml-auto text-xs text-muted-foreground">
            Updated {new Date(state.file.generated_at).toLocaleDateString()}
          </span>
        </div>

        <JobInterests
          categories={categories}
          keyword={filters.keyword}
          onKeywordChange={setKeyword}
          onToggleCategory={toggleCategory}
        />
        <FilterBar
          filters={filters}
          sources={sources}
          totalJobs={classified.length}
          visibleJobs={visible.length}
          onChange={updateFilters}
          onReset={resetFilters}
        />
        <ul className="flex-1 overflow-y-auto">
          {visible.length === 0 ? (
            <li className="px-3 py-6 text-center text-xs text-muted-foreground">
              No jobs match the current filters.
            </li>
          ) : (
            visible.map(({ job, result }) => (
              <li key={job.job_id}>
                <JobCard
                  job={job}
                  result={result}
                  selected={job.job_id === selectedId}
                  trackingStatus={tracking[job.job_id]?.status ?? null}
                  onSelect={() => select(job.job_id)}
                />
              </li>
            ))
          )}
        </ul>
      </div>

      {/* Right pane — detail */}
      <div className="overflow-y-auto p-5">
        {selected ? (
          <JobDetail
            job={selected.job}
            result={selected.result}
            tracking={tracking[selected.job.job_id]}
            onTrackingChange={(patch) =>
              patchTracking(selected.job.job_id, patch)
            }
            onTrackingClear={() => clearTracking(selected.job.job_id)}
          />
        ) : (
          <div className="flex h-full items-center justify-center p-8 text-center text-sm text-muted-foreground">
            <div>
              <p>Select a job to see its visa-risk triage and evidence.</p>
              {profileUnset && (
                <p className="mt-2">
                  Tip: open the menu (top left) to set your visa situation for
                  status-aware labels.
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      <ProfileDrawer
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          hamburgerRef.current?.focus();
        }}
        profile={profile}
        onProfileChange={setProfile}
        onProfileReset={resetProfile}
        tracking={tracking}
        onImport={handleImport}
      />
    </div>
  );
}
