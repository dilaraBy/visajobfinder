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
    "px-1.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] transition-colors",
    "border-b-[2px] border-transparent",
    isActive
      ? "border-b-[hsl(var(--ring))] text-foreground"
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
      <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b border-[hsl(var(--border))] bg-background px-4">
        <div className="flex items-baseline gap-3">
          <span className="font-display text-[1.35rem] font-semibold leading-none tracking-tight">
            VisaJobFinder
          </span>
          <span className="hidden text-[10px] uppercase tracking-[0.16em] text-muted-foreground sm:inline">
            Visa-risk triage · not immigration advice
          </span>
        </div>

        <nav className="ml-3 flex items-center gap-4 border-l border-[hsl(var(--border))] pl-4">
          <NavLink to="/" className={navClass} end>
            Dashboard
          </NavLink>
          <NavLink to="/check" className={navClass}>
            Paste Checker
          </NavLink>
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <span
            className="hidden border-l border-[hsl(var(--border))] pl-3 text-[10px] uppercase tracking-[0.12em] text-muted-foreground md:inline"
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
