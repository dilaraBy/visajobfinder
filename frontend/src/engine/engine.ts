// Port of pipeline/classifier/engine.py (classify_job + analyse_job and the
// evidence/limitations/what_to_verify builders).
//
// Rule order is identical to Python:
//   decisive blockers -> contradictory -> no_sponsorship branches ->
//   missing desc/employer -> future_sponsorship_risk -> security_clearance ->
//   unknown situation -> needs_sponsorship branch -> graduate_route branch ->
//   fallback unknown.
//
// All reason/limitation/verification strings are copied VERBATIM from Python.
// This file is a PORT and must stay in sync with the Python source of truth.

import type {
  ClassificationResult,
  EmployerMatch,
  EvidenceItem,
  JobInput,
  Label,
  PhraseSignal,
  UserContext,
} from "./types";
import {
  employerMatchToDict,
  normaliseJobInput,
  normaliseUserContext,
} from "./types";
import { scanDescription } from "./phraseScanner";
import { SponsorMatcher } from "./sponsorMatcher";

const DECISIVE_BLOCKERS = new Set([
  "citizenship_required",
  "permanent_right_to_work",
]);
// For Graduate Route users, only citizenship requirements are hard blockers.
// Permanent / unrestricted right-to-work phrases are form questions about RTW
// status, not citizenship mandates — they are verify_first for GR, not decisive.
const GRADUATE_ROUTE_DECISIVE_BLOCKERS = new Set(["citizenship_required"]);
const MONTH_RE = /^\d{4}-\d{2}$/;

function categories(signals: PhraseSignal[]): Set<string> {
  return new Set(signals.map((s) => s.category));
}

function phraseEvidence(signals: PhraseSignal[]): EvidenceItem[] {
  return signals.map((signal) => ({
    type: "phrase_signal",
    category: signal.category,
    severity: signal.severity,
    text: signal.text,
    start_index: signal.start_index,
    end_index: signal.end_index,
    rule_id: signal.rule_id,
  }));
}

function baseLimitations(match: EmployerMatch): string[] {
  const limitations = [
    "This is a visa-risk triage label, not legal or immigration advice.",
    "The engine only uses loaded sponsor-register data and phrases found in the job text.",
  ];
  if (match.is_match) {
    limitations.push(
      "Sponsor-register presence does not prove this specific role will be sponsored."
    );
  } else {
    limitations.push(
      "No reliable sponsor-register match in the loaded data does not prove the employer lacks a licence."
    );
  }
  return limitations;
}

function baseVerification(user: Required<UserContext>): string[] {
  const prompts = [
    "Verify the role-level right-to-work and sponsorship position with the employer.",
  ];
  if (user.visa_situation === "graduate_route") {
    prompts.push(
      "Ask whether this specific role can be sponsored before your current visa expires if you will need future sponsorship."
    );
  } else if (user.visa_situation === "needs_sponsorship_before_start") {
    prompts.push(
      "Ask whether sponsorship is available before the job start date for this specific role."
    );
  } else {
    prompts.push("Set the closest visa situation before relying on the label.");
  }
  return prompts;
}

function parseYearMonth(value: string | null | undefined): [number, number] | null {
  if (!value || !MONTH_RE.test(value)) {
    return null;
  }
  const [year, month] = value.split("-");
  const parsed: [number, number] = [parseInt(year, 10), parseInt(month, 10)];
  if (!(parsed[1] >= 1 && parsed[1] <= 12)) {
    return null;
  }
  return parsed;
}

function tupleGt(a: [number, number], b: [number, number]): boolean {
  // Replicate Python tuple comparison start > expiry.
  if (a[0] !== b[0]) return a[0] > b[0];
  return a[1] > b[1];
}

function targetStartAfterVisaExpiry(user: Required<UserContext>): boolean {
  const expiry = parseYearMonth(user.visa_expiry_month);
  const start = parseYearMonth(user.target_start_month);
  return Boolean(expiry && start && tupleGt(start, expiry));
}

function hasNumericSalary(job: Required<JobInput>): boolean {
  if (job.salary_min !== null && job.salary_min !== undefined) return true;
  if (job.salary_max !== null && job.salary_max !== undefined) return true;
  return /\d/.test(job.salary_text || "");
}

function employerEvidence(match: EmployerMatch): EvidenceItem {
  if (match.is_match) {
    return {
      type: "sponsor_register",
      category: "sponsor_match",
      text:
        `Sponsor-register match found: ${match.matched_name} ` +
        `(${match.confidence_band} confidence).`,
    };
  }
  if (match.matched_name) {
    return {
      type: "sponsor_register",
      category: "low_confidence_candidate",
      text:
        `Low-confidence sponsor-register candidate: ${match.matched_name} ` +
        `(${formatTwoDp(match.confidence)}).`,
    };
  }
  return {
    type: "missing_evidence",
    category: "sponsor_match",
    text: "No reliable sponsor-register match found in the loaded sponsor data.",
  };
}

function missingPhraseEvidence(descriptionText: string): EvidenceItem {
  let text: string;
  if (descriptionText) {
    text =
      "No visa-risk phrase matched the current deterministic phrase rules.";
  } else {
    text =
      "Job description is missing, so phrase evidence could not be scanned.";
  }
  return {
    type: "missing_evidence",
    category: "jd_phrase",
    text,
  };
}

function hasFutureNoSponsor(signals: PhraseSignal[]): boolean {
  for (const signal of signals) {
    if (signal.category !== "no_sponsorship") continue;
    const text = signal.text.toLowerCase();
    if (
      text.includes("future") ||
      text.includes("must not require sponsorship")
    ) {
      return true;
    }
  }
  return false;
}

function formatTwoDp(value: number): string {
  // Python f"{x:.2f}" — fixed 2 decimal places.
  return value.toFixed(2);
}

function makeResult(
  job: Required<JobInput>,
  label: Label,
  reason: string,
  evidence: EvidenceItem[],
  match: EmployerMatch,
  whatToVerify: string[],
  limitations: string[]
): ClassificationResult {
  return {
    job_id: job.job_id,
    label,
    reason,
    evidence,
    employer_match: employerMatchToDict(match),
    what_to_verify: whatToVerify,
    limitations,
  };
}

export interface ClassifyOptions {
  phraseSignals?: PhraseSignal[];
  employerMatch?: EmployerMatch;
}

export function classifyJob(
  jobInput: JobInput,
  userInput: UserContext,
  matcher: SponsorMatcher,
  options: ClassifyOptions = {}
): ClassificationResult {
  const job = normaliseJobInput(jobInput);
  const user = normaliseUserContext(userInput);

  const match = options.employerMatch ?? matcher.match(job.employer_raw);
  const signals =
    options.phraseSignals !== undefined
      ? options.phraseSignals
      : scanDescription(job.description_text);
  const cats = categories(signals);

  const evidence = phraseEvidence(signals);
  if (evidence.length === 0) {
    evidence.push(missingPhraseEvidence(job.description_text));
  }
  evidence.push(employerEvidence(match));

  const limitations = baseLimitations(match);
  const whatToVerify = baseVerification(user);

  if (!job.employer_raw.trim()) {
    limitations.push(
      "Employer name is missing, so sponsor-register matching could not run."
    );
  }
  if (!job.description_text.trim()) {
    limitations.push(
      "Job description is missing, so phrase scanning could not run."
    );
  }
  if (!job.salary_text) {
    limitations.push(
      "Salary is missing; Skilled Worker salary and occupation requirements were not assessed."
    );
  } else if (!hasNumericSalary(job)) {
    limitations.push(
      "Salary text is present but no numeric salary could be assessed."
    );
  }
  if (targetStartAfterVisaExpiry(user)) {
    limitations.push(
      "Target start month appears after the visa expiry month; sponsorship timing needs direct verification."
    );
  }

  // Graduate Route users have current legal right to work; only citizenship
  // mandates are decisive for them. All other visa situations treat
  // permanent / unrestricted RTW phrases as decisive blockers too.
  const activeDecisiveBlockers =
    user.visa_situation === "graduate_route"
      ? GRADUATE_ROUTE_DECISIVE_BLOCKERS
      : DECISIVE_BLOCKERS;
  if (setIntersects(activeDecisiveBlockers, cats)) {
    return makeResult(
      job,
      "likely_blocked",
      "The job ad contains a citizenship or permanent right-to-work requirement that is a strong blocker for the selected visa situation.",
      evidence,
      match,
      whatToVerify.concat([
        "Ask whether the requirement is mandatory and whether any visa route is accepted.",
      ]),
      limitations
    );
  }

  if (cats.has("no_sponsorship") && cats.has("sponsorship_positive")) {
    return makeResult(
      job,
      "verify_first",
      "The job ad contains contradictory sponsorship wording, so the role-level position needs direct verification.",
      evidence,
      match,
      whatToVerify.concat([
        "Ask the employer to clarify whether the no-sponsorship wording or sponsorship-positive wording applies to this role.",
      ]),
      limitations
    );
  }

  if (cats.has("no_sponsorship")) {
    if (
      user.visa_situation === "needs_sponsorship_before_start" ||
      user.needs_sponsorship_before_start
    ) {
      return makeResult(
        job,
        "likely_blocked",
        "The job ad says sponsorship is not available, which is a strong blocker for someone needing sponsorship before starting.",
        evidence,
        match,
        whatToVerify,
        limitations
      );
    }
    if (user.visa_situation === "graduate_route" && user.needs_future_sponsorship) {
      const label: Label = hasFutureNoSponsor(signals)
        ? "likely_blocked"
        : "verify_first";
      const reason =
        label === "likely_blocked"
          ? "The job ad says candidates must not require sponsorship now or in the future."
          : "The job ad says sponsorship is not available; a Graduate Route user may be able to work now, but future sponsorship needs verification.";
      return makeResult(job, label, reason, evidence, match, whatToVerify, limitations);
    }
    return makeResult(
      job,
      "verify_first",
      "The job ad says sponsorship is not available; verify whether that affects your selected visa situation.",
      evidence,
      match,
      whatToVerify,
      limitations
    );
  }

  if (!job.description_text.trim()) {
    return makeResult(
      job,
      "unknown",
      "The job description is missing, so the engine cannot scan for visa-risk wording.",
      evidence,
      match,
      whatToVerify,
      limitations
    );
  }

  if (!job.employer_raw.trim()) {
    return makeResult(
      job,
      "unknown",
      "Employer name is missing, so the sponsor-register signal cannot be assessed.",
      evidence,
      match,
      whatToVerify,
      limitations
    );
  }

  if (cats.has("security_clearance")) {
    return makeResult(
      job,
      "verify_first",
      "The job ad mentions security clearance or residency requirements, but the exact visa impact is unclear.",
      evidence,
      match,
      whatToVerify.concat([
        "Ask whether clearance requires UK citizenship, indefinite leave to remain, or a fixed UK residency history.",
      ]),
      limitations
    );
  }

  if (user.visa_situation === "unknown") {
    return makeResult(
      job,
      "unknown",
      "The selected visa situation is unknown, so status-aware rules cannot be applied reliably.",
      evidence,
      match,
      whatToVerify,
      limitations
    );
  }

  if (
    user.visa_situation === "needs_sponsorship_before_start" ||
    user.needs_sponsorship_before_start
  ) {
    // Ambiguous future-sponsorship question with no positive signal is a
    // blocker for someone who needs sponsorship before starting.
    if (
      cats.has("future_sponsorship_risk") &&
      !cats.has("sponsorship_positive")
    ) {
      return makeResult(
        job,
        "verify_first",
        "The job ad asks about right to work now and in the future, which is ambiguous for someone who needs sponsorship before starting.",
        evidence,
        match,
        whatToVerify.concat([
          "Ask whether needing Skilled Worker sponsorship before the start date would prevent progressing for this role.",
        ]),
        limitations
      );
    }
    if (match.confidence_band === "low") {
      return makeResult(
        job,
        "unknown",
        "Only a low-confidence sponsor-register candidate was found, so the employer signal is not reliable enough.",
        evidence,
        match,
        whatToVerify,
        limitations
      );
    }
    if (match.confidence_band === "medium") {
      return makeResult(
        job,
        "verify_first",
        "Only a medium-confidence sponsor-register match was found, so sponsorship availability for this role needs direct verification.",
        evidence,
        match,
        whatToVerify.concat([
          "Confirm the exact hiring entity and whether it can sponsor this specific vacancy before the start date.",
        ]),
        limitations
      );
    }
    if (!match.is_match) {
      return makeResult(
        job,
        "verify_first",
        "No reliable sponsor-register match was found in the loaded data for an applicant who needs sponsorship before starting.",
        evidence,
        match,
        whatToVerify,
        limitations
      );
    }
    if (!cats.has("sponsorship_positive")) {
      return makeResult(
        job,
        "verify_first",
        "Employer appears on the sponsor register, but the job ad does not clearly say this role offers sponsorship.",
        evidence,
        match,
        whatToVerify.concat([
          "Ask whether sponsorship is available for this specific vacancy, not only whether the employer has a licence.",
        ]),
        limitations
      );
    }
    if (!job.salary_text) {
      return makeResult(
        job,
        "verify_first",
        "The employer appears on the sponsor register and the ad mentions sponsorship, but salary is missing.",
        evidence,
        match,
        whatToVerify.concat([
          "Ask for the salary range and check it against current Skilled Worker salary and occupation rules.",
        ]),
        limitations
      );
    }
    if (!hasNumericSalary(job)) {
      return makeResult(
        job,
        "verify_first",
        "The employer appears on the sponsor register and the ad mentions sponsorship, but the salary is not numeric enough to assess.",
        evidence,
        match,
        whatToVerify.concat([
          "Ask for the salary range and check it against current Skilled Worker salary and occupation rules.",
        ]),
        limitations
      );
    }
    return makeResult(
      job,
      "worth_applying",
      "No detected blocker for the selected visa situation; sponsor-register and sponsorship-positive signals are present.",
      evidence,
      match,
      whatToVerify.concat([
        "Confirm the sponsor route, salary, occupation code, and start-date timing before treating the role as viable.",
      ]),
      limitations
    );
  }

  if (user.visa_situation === "graduate_route") {
    if (targetStartAfterVisaExpiry(user)) {
      return makeResult(
        job,
        "verify_first",
        "The target start month appears after the visa expiry month, so timing must be checked before treating the role as viable.",
        evidence,
        match,
        whatToVerify.concat([
          "Confirm whether sponsorship would be needed before the role starts.",
        ]),
        limitations
      );
    }
    // Permanent / unrestricted RTW phrasing is not a citizenship mandate, but it
    // does signal the employer expects unrestricted RTW; verify whether the
    // Graduate Route visa satisfies that requirement for this role.
    if (cats.has("permanent_right_to_work")) {
      return makeResult(
        job,
        "verify_first",
        "The job ad mentions unrestricted or permanent right-to-work wording; verify whether the Graduate Route visa satisfies that requirement for this role.",
        evidence,
        match,
        whatToVerify.concat([
          "Ask the employer whether a Graduate Route visa is accepted for this role.",
        ]),
        limitations
      );
    }
    // Graduate Route users have current right to work; a future-sponsorship
    // question in the JD is verify_first UNLESS the employer is on the sponsor
    // register AND the JD contains sponsorship-positive wording, which together
    // give sufficient signal that the role may accommodate future sponsorship.
    if (cats.has("future_sponsorship_risk")) {
      if (cats.has("sponsorship_positive") && match.is_match) {
        // fall through to worth_applying below
      } else {
        return makeResult(
          job,
          "verify_first",
          "The job ad asks about right to work now and in the future, which is ambiguous for visa-risk triage.",
          evidence,
          match,
          whatToVerify.concat([
            "Ask whether needing Skilled Worker sponsorship later would prevent progressing for this role.",
          ]),
          limitations
        );
      }
    }
    if (user.needs_future_sponsorship && match.confidence_band === "low") {
      return makeResult(
        job,
        "unknown",
        "A low-confidence sponsor-register candidate was found, which is not enough to judge future sponsorship risk.",
        evidence,
        match,
        whatToVerify,
        limitations
      );
    }
    if (user.needs_future_sponsorship && match.confidence_band === "medium") {
      return makeResult(
        job,
        "verify_first",
        "A medium-confidence sponsor-register match was found, which needs verification before relying on future sponsorship prospects.",
        evidence,
        match,
        whatToVerify.concat([
          "Confirm the exact sponsoring entity and whether it maps to the employer named in the job ad.",
        ]),
        limitations
      );
    }
    // No sponsor match is only a verify_first signal when the JD itself raises
    // a future-sponsorship question; if the JD has no explicit blocker the
    // Graduate Route user has current right to work and can apply.
    if (
      user.needs_future_sponsorship &&
      !match.is_match &&
      cats.has("future_sponsorship_risk")
    ) {
      return makeResult(
        job,
        "verify_first",
        "No reliable sponsor-register match was found, which matters if future Skilled Worker sponsorship may be needed.",
        evidence,
        match,
        whatToVerify,
        limitations
      );
    }
    return makeResult(
      job,
      "worth_applying",
      "No detected blocker for the selected Graduate Route situation based on the current job text and sponsor-register signal.",
      evidence,
      match,
      whatToVerify,
      limitations
    );
  }

  return makeResult(
    job,
    "unknown",
    "The engine did not have enough reliable evidence to classify this job for the selected visa situation.",
    evidence,
    match,
    whatToVerify,
    limitations
  );
}

function setIntersects(a: Set<string>, b: Set<string>): boolean {
  for (const x of a) {
    if (b.has(x)) return true;
  }
  return false;
}

export interface AnalyseResult {
  classification: ClassificationResult;
  phrase_signals: PhraseSignal[];
  employer_match: EmployerMatch;
}

/**
 * Mirror of analyse_job() in Python, returning the classification plus the raw
 * phrase signals and employer match. (The full data-contract job record from
 * build_job_record is not needed for the engine port / paste checker, so it is
 * intentionally omitted here.)
 */
export function analyseJob(
  job: JobInput,
  user: UserContext,
  matcher: SponsorMatcher
): AnalyseResult {
  const normalisedJob = normaliseJobInput(job);
  const employerMatch = matcher.match(normalisedJob.employer_raw);
  const phraseSignals = scanDescription(normalisedJob.description_text);
  const classification = classifyJob(job, user, matcher, {
    phraseSignals,
    employerMatch,
  });
  return {
    classification,
    phrase_signals: phraseSignals,
    employer_match: employerMatchToDict(employerMatch),
  };
}
