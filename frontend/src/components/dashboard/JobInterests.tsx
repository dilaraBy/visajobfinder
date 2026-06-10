/**
 * Job-interest personalization: category chips + a free-text keyword box. Both
 * drive the single `keyword` filter (a comma-separated phrase list) so the view
 * stays shareable via the URL and remembered via the saved profile. Matching is
 * purely for display ranking — it never touches visa classification.
 */
import { parseKeywords } from "@/lib/filters";
import { cn } from "@/lib/utils";

interface JobInterestsProps {
  categories: string[];
  keyword: string;
  onKeywordChange: (next: string) => void;
  onToggleCategory: (category: string) => void;
}

const INPUT_CLASS =
  "h-7 w-full rounded-md border border-[hsl(var(--border))] bg-transparent px-2 text-xs placeholder:text-[hsl(var(--muted-foreground))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--ring))]";

export function JobInterests({
  categories,
  keyword,
  onKeywordChange,
  onToggleCategory,
}: JobInterestsProps) {
  const selected = new Set(parseKeywords(keyword));

  return (
    <div className="space-y-2 border-b border-[hsl(var(--border))] px-3 py-2">
      <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
        Job interests
        <input
          type="search"
          className={INPUT_CLASS}
          value={keyword}
          onChange={(e) => onKeywordChange(e.target.value)}
          placeholder="e.g. psychology, economics, data analyst"
          aria-label="Filter and rank jobs by interest keywords (comma separated)"
        />
      </label>

      {categories.length > 0 && (
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Job categories">
          {categories.map((category) => {
            const isSelected = selected.has(category.toLowerCase());
            return (
              <button
                key={category}
                type="button"
                aria-pressed={isSelected}
                onClick={() => onToggleCategory(category)}
                className={cn(
                  "rounded-full border px-2 py-0.5 text-[11px] capitalize transition-colors",
                  isSelected
                    ? "border-[hsl(var(--ring))] bg-[hsl(var(--muted))] text-foreground"
                    : "border-[hsl(var(--border))] text-muted-foreground hover:text-foreground"
                )}
              >
                {category}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
