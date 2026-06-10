/**
 * Dense filter row above the job list. All controls write into the URL via the
 * parent so a filtered/sorted view is shareable and survives reload. Personal
 * data still lives in localStorage (visa profile) — the URL only carries
 * "which jobs am I currently looking at" state.
 */
import {
  DEFAULT_FILTERS,
  type FilterState,
  type FreshnessFilter,
  type LabelFilter,
  type PostedWithinFilter,
  type SortKey,
} from "@/lib/filters";

interface FilterBarProps {
  filters: FilterState;
  sources: string[];
  totalJobs: number;
  visibleJobs: number;
  onChange: (next: FilterState) => void;
  onReset: () => void;
}

const SELECT_CLASS =
  "h-7 rounded-md border border-[hsl(var(--border))] bg-transparent px-2 text-xs text-[hsl(var(--foreground))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--ring))]";

const INPUT_CLASS =
  "h-7 w-full rounded-md border border-[hsl(var(--border))] bg-transparent px-2 text-xs placeholder:text-[hsl(var(--muted-foreground))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--ring))]";

export function FilterBar({
  filters,
  sources,
  totalJobs,
  visibleJobs,
  onChange,
  onReset,
}: FilterBarProps) {
  function patch<K extends keyof FilterState>(key: K, value: FilterState[K]) {
    onChange({ ...filters, [key]: value });
  }

  const filtersActive =
    filters.label !== DEFAULT_FILTERS.label ||
    filters.source !== DEFAULT_FILTERS.source ||
    filters.location !== DEFAULT_FILTERS.location ||
    filters.freshness !== DEFAULT_FILTERS.freshness ||
    filters.posted_within !== DEFAULT_FILTERS.posted_within ||
    filters.sort !== DEFAULT_FILTERS.sort ||
    filters.keyword !== DEFAULT_FILTERS.keyword;

  return (
    <div className="space-y-2 border-b border-[hsl(var(--border))] px-3 py-2">
      <div className="grid grid-cols-2 gap-2">
        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
          Label
          <select
            className={SELECT_CLASS}
            value={filters.label}
            onChange={(e) => patch("label", e.target.value as LabelFilter)}
            aria-label="Filter by visa-risk label"
          >
            <option value="all">All labels</option>
            <option value="worth_applying">Worth applying</option>
            <option value="verify_first">Verify first</option>
            <option value="likely_blocked">Likely blocked</option>
            <option value="unknown">Unknown</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
          Source
          <select
            className={SELECT_CLASS}
            value={filters.source}
            onChange={(e) => patch("source", e.target.value)}
            aria-label="Filter by source"
          >
            <option value="all">All sources</option>
            {sources.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
          Freshness
          <select
            className={SELECT_CLASS}
            value={filters.freshness}
            onChange={(e) =>
              patch("freshness", e.target.value as FreshnessFilter)
            }
            aria-label="Filter by freshness"
          >
            <option value="all">Any age</option>
            <option value="fresh">Within stale threshold</option>
            <option value="stale">Stale</option>
            <option value="missing_date">No posting date</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
          Posted within
          <select
            className={SELECT_CLASS}
            value={filters.posted_within}
            onChange={(e) =>
              patch("posted_within", e.target.value as PostedWithinFilter)
            }
            aria-label="Filter by how recently the job was posted"
          >
            <option value="all">Any time</option>
            <option value="30">Past month</option>
            <option value="90">Past 3 months</option>
            <option value="180">Past 6 months</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
          Sort
          <select
            className={SELECT_CLASS}
            value={filters.sort}
            onChange={(e) => patch("sort", e.target.value as SortKey)}
            aria-label="Sort job list"
          >
            <option value="label_severity">Label severity</option>
            <option value="posted_at_desc">Newest first</option>
            <option value="posted_at_asc">Oldest first</option>
          </select>
        </label>
      </div>

      <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
        Location contains
        <input
          type="search"
          className={INPUT_CLASS}
          value={filters.location}
          onChange={(e) => patch("location", e.target.value)}
          placeholder="e.g. London, Remote"
          aria-label="Filter by location substring"
        />
      </label>

      <div className="flex items-center justify-between text-xs text-[hsl(var(--muted-foreground))]">
        <span>
          {visibleJobs} of {totalJobs} jobs
        </span>
        {filtersActive && (
          <button
            type="button"
            onClick={onReset}
            className="rounded-md border border-[hsl(var(--border))] px-2 py-0.5 text-[11px] hover:bg-[hsl(var(--muted))]"
          >
            Reset
          </button>
        )}
      </div>
    </div>
  );
}
