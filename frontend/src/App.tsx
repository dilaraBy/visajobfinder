/**
 * App router + shell.
 *
 * Routes:
 *   /        Dashboard (job list + evidence detail), reads jobs.json.
 *   /check   Paste-a-Job Checker.
 *
 * All personal data (visa profile, theme) stays in localStorage. The only
 * network requests are static fetches of /jobs.json and /sponsors.json.
 */
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { DashboardPage } from "@/components/dashboard/DashboardPage";
import { CheckPage } from "@/components/CheckPage";

export function App() {
  return (
    // BASE_URL is "/" in dev and the configured base (e.g. "/visajobfinder/")
    // in deployed builds; the router needs it without the trailing slash.
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, "")}>
      <AppShell>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/check" element={<CheckPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}
