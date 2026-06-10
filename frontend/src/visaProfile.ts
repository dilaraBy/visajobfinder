/**
 * Shape of the user's visa profile, stored in localStorage only.
 * Nothing here is sent to any server.
 */
import type { UserContext, VisaSituation } from "./engine/types";

export interface VisaProfile {
  visa_situation: VisaSituation;
  needs_sponsorship_before_start: boolean;
  needs_future_sponsorship: boolean;
  visa_expiry_month: string;
  target_start_month: string;
}

export const DEFAULT_VISA_PROFILE: VisaProfile = {
  visa_situation: "unknown",
  needs_sponsorship_before_start: false,
  needs_future_sponsorship: false,
  visa_expiry_month: "",
  target_start_month: "",
};

export const VISA_PROFILE_STORAGE_KEY = "vjf_visa_profile_v1";

export const VISA_SITUATION_LABELS: Record<VisaSituation, string> = {
  graduate_route: "Graduate Route",
  needs_sponsorship_before_start: "Needs sponsorship before start",
  unknown: "Unknown / not set",
};

/** Map the browser-local profile to the engine's UserContext (single source of
 * truth so the dashboard and paste checker classify identically). */
export function userContextFromProfile(profile: VisaProfile): UserContext {
  return {
    visa_situation: profile.visa_situation,
    visa_expiry_month: profile.visa_expiry_month || null,
    needs_sponsorship_before_start: profile.needs_sponsorship_before_start,
    needs_future_sponsorship: profile.needs_future_sponsorship,
    target_start_month: profile.target_start_month || null,
  };
}
