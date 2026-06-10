# Dataset Collection Checklist

This is a concrete, reproducible process for a human collector to grow the real-seed evaluation set from 20 records to the 150–200 target.

**Do not fabricate job ads or invent source URLs.** Every record must be an excerpt from a real, publicly accessible job posting. Synthetic data belongs in `data/eval/synthetic_edge_cases.json` only.

---

## Before You Start

- Read `docs/EVALUATION_PLAN.md` for target mix and required fields.
- Read `docs/LABELLING_GUIDE.md` for label definitions and labelling rules.
- Read `data/eval/labelled_jobs.real.json` for an example of a complete record.
- Check the existing `eval_id` values so you can assign the next sequential ID (e.g. `real-021`).

---

## Target Mix (150–200 records total)

| Category | Target count |
|---|---|
| Sponsor-register matched + clearly sponsorship-positive | ~40 |
| Explicit no-sponsorship or hard right-to-work blockers | ~40 |
| Ambiguous (future-sponsorship question, case-by-case, no phrase) | ~40 |
| Graduate schemes and internships (title or description explicit) | ~30 |
| Varied source: Reed, Adzuna, Greenhouse, Lever, direct company pages | Spread evenly |

---

## Approved Public Sources

Collect from sources that produce stable, archivable URLs. Prefer sources where the application form or job description is directly readable without login.

### Lever
- URL pattern: `https://jobs.lever.co/{company-slug}/{uuid}/apply`
- The `/apply` page shows the application form, which often contains the right-to-work question.
- The main job page at `https://jobs.lever.co/{company-slug}/{uuid}` contains the job description.
- Both pages are publicly accessible without login.

### Greenhouse
- URL pattern: `https://boards.greenhouse.io/embed/job_app?for={company}&token={id}` (embedded) or `https://boards.greenhouse.io/{company}/jobs/{id}`
- The embedded form shows right-to-work questions.
- The job board page contains the description.

### Reed.co.uk
- URL pattern: `https://www.reed.co.uk/jobs/{slug}/{id}`
- The public snippet shown to non-logged-in users often includes right-to-work or sponsorship language.
- Only collect what is visible without login.

### Adzuna
- URL pattern: `https://www.adzuna.co.uk/jobs/details/{id}`
- Similar to Reed — collect the public snippet only.

### Direct company job pages (optional)
- Greenhouse and Lever embed pages directly on company career sites.
- Use only if the URL is stable and publicly accessible.

**Do not use:** Student Circus (login-walled), LinkedIn (requires login), Indeed (rate-limited and login-walled for full descriptions).

---

## What to Collect Per Record

Collect only a short excerpt, not the full job description. Aim for 200–600 characters of relevant text. The goal is to capture the visa-relevant phrases, not store full job descriptions (copyright and storage reasons).

Required fields (see `labelled_jobs.real.json` schema):

| Field | What to capture |
|---|---|
| `eval_id` | Sequential ID: `real-021`, `real-022`, etc. |
| `source` | `lever`, `greenhouse`, `reed`, `adzuna`, or `direct` |
| `source_url` | Full stable URL to the job or apply page |
| `title` | Exact job title from the posting |
| `employer_raw` | Employer name as shown (may differ from sponsor-register name) |
| `location` | Location as shown in the posting |
| `salary_text` | Salary text if shown, or `null` |
| `description_text` | Short excerpt (200–600 chars) containing visa-relevant phrases |
| `role_level` | One of: `internship`, `graduate`, `graduate_scheme`, `entry_level`, `junior`, `junior_or_mid`, `associate`, `mid`, `senior`, `graduate_to_senior` |
| `default_dashboard_fit` | `true` if role_level is in the target levels; `false` otherwise |
| `evidence_phrases` | Array of `{category, text}` objects for each visa-relevant phrase found |
| `expected_labels` | Object with `graduate_route` and `needs_sponsorship_before_start` labels |
| `sponsor_match_expected` | Object with `available`, `is_match`, `matched_name`, `notes` |
| `review_status` | Start as `needs_review`; change to `confirmed` after second-pass review |
| `eval_use` | `classification_and_evidence` (default) |
| `human_notes` | One or two sentences explaining the labelling decision |

---

## How to Write the Excerpt

1. Open the job posting or apply page.
2. Search for any of these phrase types: right to work, sponsorship, visa, clearance, citizenship, restriction.
3. Copy the surrounding sentence(s) that contain the phrase — not more than 2–3 sentences.
4. Remove personal data if any appears (unlikely on job postings, but check).
5. Do not modify the wording of the excerpt — copy it as-is.
6. If the posting has no visa-related language at all, note that in `human_notes` and record the absence.

Maximum excerpt length: 1200 characters. If longer, the validator will warn.

---

## How to Assign Labels

Use the definitions in `docs/LABELLING_GUIDE.md`. Short summary:

| Label | When to use |
|---|---|
| `worth_applying` | No detected blocker for the visa situation; user can apply and verify |
| `verify_first` | Potentially viable but material information is ambiguous or missing |
| `likely_blocked` | Strong public evidence the user should not apply for this situation |
| `unknown` | Too little evidence to judge |

Label independently for each visa situation (`graduate_route`, `needs_sponsorship_before_start`).

A Graduate Route user has current legal right to work. The main concerns are:
- Phrases that explicitly require citizenship or permanent/unrestricted RTW → `likely_blocked`
- "Without sponsorship" phrases → `verify_first` (they can work now, future sponsorship blocked)
- "Must not require sponsorship now or in the future" → `likely_blocked` (future blocked)
- No blocking phrase, employer on sponsor register, sponsorship-positive wording → `worth_applying`

A needs-sponsorship-before-start user requires sponsorship from day one. The main concerns:
- Any no-sponsorship phrase → `likely_blocked`
- Sponsor-register match + sponsorship-positive phrase + salary → `worth_applying`
- Sponsor-register match without confirmed role-level sponsorship → `verify_first`
- No sponsor-register match → `verify_first` at best

---

## Sponsor-Register Match Expected

For each record, indicate whether you expect the engine to match the employer on the sponsor register:

```json
"sponsor_match_expected": {
  "available": true,
  "is_match": true,
  "matched_name": "Octopus Energy Group",
  "notes": "Employer confirmed on GOV.UK register as of 2026-06-04."
}
```

If you are unsure whether the employer is on the register, check `https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers`. If the employer is not in the current engine fixture, set `is_match: false` and note it. The test fixture only contains a small sample; the real GOV.UK register is separate.

---

## Review Workflow

1. **Collector** creates the record with `review_status: "needs_review"`.
2. **Reviewer** (second person, or same person after 24 hours) reads the excerpt and labels, checks the source URL still resolves, and sets `review_status: "confirmed"` or `review_status: "change_recommended"` with a note.
3. If the URL is dead or the posting has been removed, set `review_status: "remove_from_eval"`.
4. Records with `review_status: "remove_from_eval"` are excluded from metrics automatically.

---

## Running the Evaluator

After adding records, validate and run:

```bash
python -m pipeline.eval.run_eval \
  --dataset ./data/eval/labelled_jobs.real.json \
  --sponsor-register ./data/sponsor_register/sample_sponsors.csv
```

Check for validation errors before reporting metrics. Run `python -m pytest -q` to confirm no regressions.

---

## What NOT to Do

- Do not copy full job descriptions — use short excerpts of visa-relevant phrases only.
- Do not invent a URL or employer name. If you cannot find a real example, skip it.
- Do not label a job based on assumptions about the employer — label only what the public ad says.
- Do not set `is_match: true` in `sponsor_match_expected` unless you have checked the actual GOV.UK register or the engine fixture.
- Do not include any personal data (candidate names, email addresses, etc.) in any field.
- Do not report synthetic dataset metrics as real-seed results.
