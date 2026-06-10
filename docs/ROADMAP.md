# Roadmap

## Phase 0 - Problem Validation

Outcome: prove the problem and collect real examples.

- Interview 5 international students.
- Collect 15-25 job ads they were unsure about.
- Write down confusing phrases.
- Confirm target personas.
- Finalise v1 labels.

Exit criteria:

- at least 5 real users interviewed;
- at least 15 real job ads collected;
- label wording understood by users.

## Phase 1 - Visa Engine Prototype

Outcome: classify pasted job descriptions with evidence.

- Download and parse GOV.UK sponsor register.
- Implement employer-name normalisation.
- Implement fuzzy sponsor matching.
- Implement phrase scanner.
- Implement status-aware rules.
- Build CLI or simple local paste-checker.

Exit criteria:

- pasted job returns label, evidence, sponsor match, and what-to-verify notes;
- unit tests cover obvious blockers and ambiguous cases.

## Phase 2 - Credibility Lockdown

Outcome: engine quality is measurable on real labelled examples, not only synthetic smoke tests.

- Make the real seed dataset executable by the eval script.
- Expand deterministic phrase rules from real job-ad wording.
- Report sample metrics and real-seed metrics separately.
- Add sponsor-register source/version/date metadata to match outputs.
- Keep `worth_applying` conservative when salary or timing is unassessed.
- Create 150-200 item labelled dataset after the seed loop is working.
- Report false red, false green, unknown rate, and evidence accuracy.
- Add failure-case examples.

Exit criteria:

- metrics can be generated from one command;
- real-seed eval does not silently return zero cases;
- README can honestly describe engine quality and current limitations.

## Phase 3 - Paste Checker UI

Outcome: users can classify jobs they found anywhere.

- Build a browser UI for pasted job title, employer, description, location, salary, and URL.
- Show label, reason, exact evidence, missing evidence, sponsor match, confidence, limitations, and what to verify.
- Keep entered profile data local to the browser.
- Add exportable example outputs for the portfolio/demo.

Exit criteria:

- a user can paste a real job and understand the result in under 60 seconds;
- every label has visible evidence or a missing-evidence explanation;
- `worth_applying` is visibly framed as "no detected blocker; verify with employer."

## Phase 4 - Job Data Pipeline

Outcome: daily public job data exists.

- Add Reed source.
- Add Adzuna source.
- Add Greenhouse/Lever for selected known employers.
- Normalise fields.
- Deduplicate listings.
- Run visa engine on jobs.
- Write static `jobs.json`.

Exit criteria:

- pipeline produces a valid static data file;
- source failures do not break the full pipeline;
- stale/dead links are tracked.

## Phase 5 - Dashboard Frontend

Outcome: users can use the dashboard.

- Build setup profile.
- Build dashboard list.
- Build filters and sorting.
- Build job detail evidence panel.
- Build paste checker.
- Build local tracking.
- Build export/import.

Exit criteria:

- no login required;
- personal data stays local;
- every label has visible evidence or limitation.

## Phase 6 - Deployment

Outcome: public demo exists.

- Deploy static frontend.
- Schedule pipeline.
- Publish current `jobs.json`.
- Add visible update timestamp.
- Add clear limitation copy.

Exit criteria:

- public URL works;
- daily refresh works;
- users can verify source links.

## Phase 7 - User Test and Polish

Outcome: product is useful and presentable.

- Test with 5 users.
- Fix confusing label copy.
- Improve evidence visibility.
- Add README metrics.
- Record 60-second demo.

Exit criteria:

- users can explain labels correctly;
- README has metrics and limitations;
- demo shows real use, not only UI polish.

## Future Scope

Only after v1 works:

- CV/role matching;
- saved searches;
- email or Telegram digests;
- cross-device sync;
- broader sectors;
- JobBERT or small model distillation;
- employer alias database;
- advanced Skilled Worker salary/SOC inference.
