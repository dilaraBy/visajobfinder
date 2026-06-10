// Port of pipeline/classifier/phrase_scanner.py.
// PHRASE_RULES are copied VERBATIM (same rule_id, category, severity, pattern,
// priority). Python uses re.IGNORECASE; here we compile each pattern with the
// "gi" flags. Patterns use the same regex constructs (\b, [^.]{0,80}, etc.)
// which behave equivalently between Python `re` and JS RegExp for this corpus.
//
// IMPORTANT: this file is a PORT and must stay in sync with the Python source
// of truth. See frontend/README.md.

import type { PhraseSignal } from "./types";

export interface PhraseRule {
  rule_id: string;
  category: string;
  severity: string;
  pattern: string;
  priority: number;
}

export const PHRASE_RULES: PhraseRule[] = [
  {
    rule_id: "citizenship_uk_nationals_only_001",
    category: "citizenship_required",
    severity: "red",
    pattern: String.raw`\b(?:uk|british)\s+national[s]?\s+only\b`,
    priority: 40,
  },
  {
    rule_id: "citizenship_british_required_001",
    category: "citizenship_required",
    severity: "red",
    pattern: String.raw`\b(?:british|uk)\s+citizenship\s+(?:is\s+)?required\b`,
    priority: 40,
  },
  {
    rule_id: "citizenship_british_citizen_001",
    category: "citizenship_required",
    severity: "red",
    pattern: String.raw`\bmust\s+be\s+(?:a\s+)?british\s+citizen\b`,
    priority: 40,
  },
  {
    rule_id: "rtw_permanent_001",
    category: "permanent_right_to_work",
    severity: "red",
    pattern: String.raw`\bpermanent\s+right\s+to\s+work\b`,
    priority: 40,
  },
  {
    rule_id: "rtw_unrestricted_001",
    category: "permanent_right_to_work",
    severity: "red",
    pattern: String.raw`\bunrestricted\s+right\s+to\s+work\b`,
    priority: 40,
  },
  {
    rule_id: "rtw_without_restriction_001",
    category: "permanent_right_to_work",
    severity: "red",
    pattern: String.raw`\bright\s+to\s+work\s+in\s+the\s+uk\s+without\s+restriction\b`,
    priority: 40,
  },
  {
    rule_id: "rtw_ilr_001",
    category: "permanent_right_to_work",
    severity: "red",
    pattern: String.raw`\bindefinite\s+leave\s+to\s+remain\b`,
    priority: 40,
  },
  {
    rule_id: "no_sponsor_now_future_001",
    category: "no_sponsorship",
    severity: "red",
    pattern: String.raw`\bmust\s+not\s+require\s+(?:visa\s+)?sponsorship(?:\s+now)?(?:\s+(?:or|and)\s+in\s+the\s+future)?\b`,
    priority: 40,
  },
  {
    rule_id: "no_sponsor_unable_001",
    category: "no_sponsorship",
    severity: "red",
    pattern: String.raw`\b(?:we\s+)?(?:cannot|can't|unable\s+to|will\s+not|won't|do\s+not|don't)\s+(?:provide\s+|offer\s+)?(?:visa\s+)?sponsorship\b`,
    priority: 40,
  },
  {
    rule_id: "no_sponsor_available_001",
    category: "no_sponsorship",
    severity: "red",
    pattern: String.raw`\bno\s+(?:visa\s+)?sponsorship\s+(?:is\s+)?(?:available|provided|offered)\b`,
    priority: 40,
  },
  {
    rule_id: "no_sponsor_select_no_001",
    category: "no_sponsorship",
    severity: "red",
    pattern: String.raw`\b(?:please\s+)?select\s+['"]?no['"]?\s+if[^.]{0,80}\b(?:require|requires|required)\s+(?:visa\s+)?sponsorship\b`,
    priority: 40,
  },
  {
    rule_id: "no_sponsor_select_no_passive_001",
    category: "no_sponsorship",
    severity: "red",
    pattern: String.raw`\b(?:please\s+)?select\s+['"]?no['"]?\s+if[^.]{0,80}\b(?:visa\s+)?sponsorship\s+would\s+be\s+required\b`,
    priority: 40,
  },
  {
    rule_id: "no_sponsor_without_001",
    category: "no_sponsorship",
    severity: "red",
    pattern: String.raw`\b(?:full\s+|legal\s+)?right\s+to\s+(?:work(?:\s+and\s+live)?|live\s+and\s+work)[^.]{0,80}\bwithout\s+(?:requiring\s+)?(?:visa\s+)?sponsorship\b`,
    priority: 40,
  },
  {
    rule_id: "no_sponsor_without_requiring_001",
    category: "no_sponsorship",
    severity: "red",
    pattern: String.raw`\bwithout\s+requiring\s+(?:visa\s+)?sponsorship\b`,
    priority: 40,
  },
  {
    rule_id: "no_sponsor_unable_to_sponsor_001",
    category: "no_sponsorship",
    severity: "red",
    pattern: String.raw`\b(?:we\s+|the\s+employer\s+)?(?:cannot|can't|unable\s+to|will\s+not|won't|do\s+not|don't)\s+sponsor\b[^.]{0,80}`,
    priority: 40,
  },
  {
    rule_id: "no_sponsor_unable_employees_future_001",
    category: "no_sponsorship",
    severity: "red",
    pattern: String.raw`\bunable\s+to\s+sponsor\s+employees(?:,)?\s+either\s+now\s+or\s+in\s+the\s+future\b`,
    priority: 41,
  },
  {
    rule_id: "rtw_now_or_future_001",
    category: "future_sponsorship_risk",
    severity: "amber",
    pattern: String.raw`\b(?:right\s+to\s+work|work\s+authori[sz]ation)[^.]{0,80}\bnow\s+(?:and|or)\s+in\s+the\s+future\b`,
    priority: 30,
  },
  {
    rule_id: "sponsorship_future_unclear_001",
    category: "future_sponsorship_risk",
    severity: "amber",
    pattern: String.raw`\b(?:require|need|needing|might\s+need)[^.]{0,30}(?:visa\s+)?sponsorship[^.]{0,40}\b(?:now|soon|future)\b`,
    priority: 30,
  },
  {
    rule_id: "sponsorship_temporary_future_001",
    category: "future_sponsorship_risk",
    severity: "amber",
    pattern: String.raw`\btemporary\s+right\s+to\s+work\s+in\s+the\s+uk[^.]{0,80}\b(?:need|require)[^.]{0,30}(?:visa\s+)?sponsorship\s+in\s+the\s+future\b`,
    priority: 32,
  },
  {
    rule_id: "sponsorship_temporary_status_needs_001",
    category: "future_sponsorship_risk",
    severity: "amber",
    pattern: String.raw`\btemporary\s+right[-\s]+to[-\s]+work\s+status[^.]{0,100}\bsponsorship\s+needs\b`,
    priority: 32,
  },
  {
    rule_id: "sponsorship_temporary_work_needs_001",
    category: "future_sponsorship_risk",
    severity: "amber",
    pattern: String.raw`\btemporary\s+right\s+to\s+work[^.]{0,100}\bsponsorship\s+needs\b`,
    priority: 32,
  },
  {
    rule_id: "sponsorship_future_question_001",
    category: "future_sponsorship_risk",
    severity: "amber",
    pattern: String.raw`\b(?:will\s+(?:you\s+)?(?:now\s+or\s+in\s+the\s+future\s+)?require|(?:visa\s+)?sponsorship\s+will\s+be\s+required)(?:\s+(?:visa\s+)?sponsorship)?(?:\s+at\s+any\s+point)?\b`,
    priority: 32,
  },
  {
    rule_id: "sponsorship_future_before_require_001",
    category: "future_sponsorship_risk",
    severity: "amber",
    pattern: String.raw`\b(?:now\s+or\s+in\s+the\s+future|at\s+any\s+point)[^.]{0,80}\brequire\s+(?:visa\s+)?sponsorship\b`,
    priority: 32,
  },
  {
    rule_id: "sponsor_positive_visa_available_001",
    category: "sponsorship_positive",
    severity: "green",
    pattern: String.raw`\b(?:skilled\s+worker\s+)?visa\s+sponsorship\s+(?:is\s+)?available\b`,
    priority: 25,
  },
  {
    rule_id: "sponsor_positive_registered_001",
    category: "sponsorship_positive",
    severity: "green",
    pattern: String.raw`\bregistered\s+visa\s+sponsor\b`,
    priority: 25,
  },
  {
    rule_id: "sponsor_positive_cos_001",
    category: "sponsorship_positive",
    severity: "green",
    pattern: String.raw`\bcertificate\s+of\s+sponsorship\b`,
    priority: 25,
  },
  {
    rule_id: "sponsor_positive_can_sponsor_001",
    category: "sponsorship_positive",
    severity: "green",
    pattern: String.raw`\bwe\s+(?:can|are\s+able\s+to)\s+sponsor\b`,
    priority: 25,
  },
  {
    rule_id: "sponsor_positive_considered_001",
    category: "sponsorship_positive",
    severity: "green",
    pattern: String.raw`\bsponsorship\s+(?:(?:is|may\s+be)\s+)?considered\b`,
    priority: 25,
  },
  {
    rule_id: "sponsor_positive_case_by_case_001",
    category: "sponsorship_positive",
    severity: "green",
    pattern: String.raw`\bconsider[s]?\s+sponsorship\s+(?:on\s+a\s+)?case\s+by\s+case(?:\s+basis)?\b`,
    priority: 25,
  },
  {
    rule_id: "sponsorship_case_by_case_ambiguous_001",
    category: "ambiguous",
    severity: "amber",
    pattern: String.raw`\bcase\s+by\s+case(?:\s+basis)?\b`,
    priority: 24,
  },
  {
    rule_id: "sponsorship_not_every_role_001",
    category: "ambiguous",
    severity: "amber",
    pattern: String.raw`\b(?:not\s+able\s+to|cannot)\s+offer\s+(?:it|sponsorship)\s+for\s+every\s+role\b`,
    priority: 25,
  },
  {
    rule_id: "security_sc_001",
    category: "security_clearance",
    severity: "amber",
    pattern: String.raw`\b(?:sc|dv)\s+clearance\b`,
    priority: 20,
  },
  {
    rule_id: "security_cleared_001",
    category: "security_clearance",
    severity: "amber",
    pattern: String.raw`\bsecurity\s+cleared\b`,
    priority: 20,
  },
  {
    rule_id: "security_uk_eyes_001",
    category: "security_clearance",
    severity: "amber",
    pattern: String.raw`\buk\s+eyes\s+only\b`,
    priority: 20,
  },
  {
    rule_id: "security_residency_001",
    category: "security_clearance",
    severity: "amber",
    pattern: String.raw`\b(?:5|five)\s+years?\s+uk\s+residency\b`,
    priority: 20,
  },
  {
    rule_id: "rtw_ambiguous_001",
    category: "ambiguous",
    severity: "amber",
    pattern: String.raw`\bmust\s+have\s+(?:the\s+)?right\s+to\s+work\s+in\s+the\s+uk\b`,
    priority: 10,
  },
  {
    rule_id: "rtw_all_applicants_001",
    category: "ambiguous",
    severity: "amber",
    pattern: String.raw`\ball\s+applicants\s+must\s+have\s+(?:the\s+)?right\s+to\s+work\s+in\s+the\s+uk\b`,
    priority: 11,
  },
  {
    rule_id: "rtw_legal_question_001",
    category: "ambiguous",
    severity: "amber",
    pattern: String.raw`\b(?:do\s+you\s+have\s+(?:the\s+)?)?legal\s+right\s+to\s+work\s+in\s+(?:the\s+uk|uk|london|england|scotland|wales|northern\s+ireland)(?:\?)?`,
    priority: 10,
  },
  {
    rule_id: "sponsorship_needed_option_001",
    category: "ambiguous",
    severity: "amber",
    pattern: String.raw`\b(?:i\s+)?(?:will\s+)?(?:need|require)\s+(?:visa\s+)?sponsorship(?:\s+soon|\s+to\s+start\s+this\s+role)?\b`,
    priority: 10,
  },
  {
    rule_id: "rtw_generic_001",
    category: "ambiguous",
    severity: "amber",
    pattern: String.raw`\bright\s+to\s+work\s+in\s+(?:the\s+uk|uk|london|england|scotland|wales|northern\s+ireland)\b`,
    priority: 5,
  },
  {
    rule_id: "rtw_eligible_generic_001",
    category: "ambiguous",
    severity: "amber",
    pattern: String.raw`\b(?:eligible|eligibility)\s+to\s+work\s+in\s+(?:the\s+uk|uk|london|england|scotland|wales|northern\s+ireland)\b`,
    priority: 5,
  },
  {
    rule_id: "rtw_must_be_eligible_001",
    category: "ambiguous",
    severity: "amber",
    pattern: String.raw`\bmust\s+be\s+eligible\s+to\s+work\s+in\s+(?:the\s+uk|uk|london|england|scotland|wales|northern\s+ireland)\b`,
    priority: 6,
  },
];

const RULE_BY_ID = new Map(PHRASE_RULES.map((rule) => [rule.rule_id, rule]));

function cleanText(value: string): string {
  // Equivalent to " ".join(value.split()) in Python.
  return value.split(/\s+/).filter(Boolean).join(" ");
}

function overlaps(
  left: PhraseSignal,
  rightStart: number,
  rightEnd: number
): boolean {
  return left.start_index < rightEnd && rightStart < left.end_index;
}

function keepSignal(
  existing: PhraseSignal,
  candidate: PhraseSignal
): PhraseSignal {
  const existingRule = RULE_BY_ID.get(existing.rule_id)!;
  const candidateRule = RULE_BY_ID.get(candidate.rule_id)!;
  if (candidateRule.priority > existingRule.priority) {
    return candidate;
  }
  if (candidateRule.priority === existingRule.priority) {
    const existingLen = existing.end_index - existing.start_index;
    const candidateLen = candidate.end_index - candidate.start_index;
    if (candidateLen > existingLen) {
      return candidate;
    }
  }
  return existing;
}

export function scanDescription(descriptionText: string): PhraseSignal[] {
  if (!descriptionText) {
    return [];
  }

  const signals: PhraseSignal[] = [];
  for (const rule of PHRASE_RULES) {
    const regex = new RegExp(rule.pattern, "gi");
    for (const match of descriptionText.matchAll(regex)) {
      const start = match.index;
      const matched = match[0];
      // Guard against zero-length matches causing infinite progress issues;
      // Python re.finditer also skips empty matches by advancing, but none of
      // these patterns can match empty strings.
      const candidate: PhraseSignal = {
        category: rule.category,
        severity: rule.severity,
        text: cleanText(matched),
        start_index: start,
        end_index: start + matched.length,
        rule_id: rule.rule_id,
      };

      let overlapIndex: number | null = null;
      for (let index = 0; index < signals.length; index += 1) {
        if (
          overlaps(signals[index], candidate.start_index, candidate.end_index)
        ) {
          overlapIndex = index;
          break;
        }
      }

      if (overlapIndex === null) {
        signals.push(candidate);
      } else {
        signals[overlapIndex] = keepSignal(signals[overlapIndex], candidate);
      }
    }
  }

  return signals.sort((a, b) => {
    if (a.start_index !== b.start_index) {
      return a.start_index - b.start_index;
    }
    return a.end_index - b.end_index;
  });
}

export function hasCategory(
  signals: Iterable<PhraseSignal>,
  category: string
): boolean {
  for (const signal of signals) {
    if (signal.category === category) {
      return true;
    }
  }
  return false;
}
