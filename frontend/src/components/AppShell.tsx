import { NavLink } from "react-router-dom";
import { Moon, Sun } from "lucide-react";

import { useTheme } from "@/hooks/useTheme";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import {
  DEFAULT_VISA_PROFILE,
  VISA_PROFILE_STORAGE_KEY,
  VISA_SITUATION_LABELS,
  type VisaProfile,
} from "@/visaProfile";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function navClass({ isActive }: { isActive: boolean }) {
  return cn(
    "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
    isActive
      ? "bg-[hsl(var(--accent))] text-[hsl(var(--accent-foreground))]"
      : "text-muted-foreground hover:text-foreground"
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [theme, toggleTheme] = useTheme();
  const [profile] = useLocalStorage<VisaProfile>(
    VISA_PROFILE_STORAGE_KEY,
    DEFAULT_VISA_PROFILE
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-10 flex h-14 items-center gap-3 border-b border-[hsl(var(--border))] bg-card px-4">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold">VisaJobFinder</span>
          <span className="hidden text-xs text-muted-foreground sm:inline">
            visa-risk triage — not immigration advice
          </span>
        </div>

        <nav className="ml-2 flex items-center gap-1">
          <NavLink to="/" className={navClass} end>
            Dashboard
          </NavLink>
          <NavLink to="/check" className={navClass}>
            Paste Checker
          </NavLink>
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <span
            className="hidden rounded-full bg-[hsl(var(--muted))] px-3 py-1 text-xs text-muted-foreground md:inline"
            title="Your visa situation (stored only in this browser)"
          >
            {VISA_SITUATION_LABELS[profile.visa_situation]}
          </span>
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>
        </div>
      </header>

      <main>{children}</main>
    </div>
  );
}
