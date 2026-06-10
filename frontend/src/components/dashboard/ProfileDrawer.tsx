/**
 * Left slide-in drawer holding the visa profile + data export/import. It is
 * presentation only: all state lives in DashboardPage and arrives via props.
 * Closed by default so the dashboard's main area is the job list, not settings.
 */
import { useEffect, useRef } from "react";
import { X } from "lucide-react";

import { VisaProfileForm } from "@/components/VisaProfileForm";
import { DataPanel } from "@/components/dashboard/DataPanel";
import type { VisaProfile } from "@/visaProfile";
import type { TrackingState } from "@/lib/tracking";

interface ProfileDrawerProps {
  open: boolean;
  onClose: () => void;
  profile: VisaProfile;
  onProfileChange: (profile: VisaProfile) => void;
  onProfileReset: () => void;
  tracking: TrackingState;
  onImport: (profile: VisaProfile | null, tracking: TrackingState) => void;
}

export const PROFILE_DRAWER_ID = "profile-drawer";

export function ProfileDrawer({
  open,
  onClose,
  profile,
  onProfileChange,
  onProfileReset,
  tracking,
  onImport,
}: ProfileDrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  // Esc closes; focus moves into the drawer on open.
  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        id={PROFILE_DRAWER_ID}
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Visa profile and saved data"
        className="fixed inset-y-0 left-0 z-50 w-[min(22rem,90vw)] overflow-y-auto border-r border-[hsl(var(--border))] bg-background p-3 shadow-lg"
      >
        <div className="mb-2 flex items-center justify-between">
          <span className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            Your settings
          </span>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close settings"
            className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <VisaProfileForm
          profile={profile}
          onChange={onProfileChange}
          onReset={onProfileReset}
        />
        <DataPanel profile={profile} tracking={tracking} onImport={onImport} />
      </aside>
    </>
  );
}
