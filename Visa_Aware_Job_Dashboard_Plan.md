# Visa-Aware Job Triage Dashboard - v1 Plan

Working title: Visa-Aware Job Dashboard. Better product names can wait.

## 1. One-Line Description

A public, no-login dashboard that helps international students in the UK triage graduate and junior job listings using visa-risk signals tailored to their situation. It does not tell users "you are eligible"; it tells them whether a role looks worth applying to, what to verify, and why.

## 2. The Real Problem

International students waste time because UK job search information is fragmented and visa signals are unclear.

- Job listings are spread across job boards, ATS pages, university platforms, and employer career sites.
- Many postings do not clearly say whether sponsorship is available.
- Sponsor-register lookup alone is not enough: a company can be licensed but still not sponsor a specific role.
- Sponsor-only job boards can over-filter Graduate Route holders, because many can work now without sponsorship.
- Students often need a fast triage answer: "Apply now, verify first, or skip?"

The product should reduce wasted applications without pretending to provide legal advice.

## 3. Brutal Product Thesis

This is not a novel category. The portfolio value comes from execution:

- turning a painful student problem into a focused tool;
- grounding signals in official sponsor data;
- handling Graduate Route nuance better than sponsor-only tools;
- showing exact evidence for every label;
- measuring mistakes honestly.

The project fails if it becomes another generic job board.

## 4. Target Users

Primary users:

- international students and recent graduates in the UK;
- non-technical or semi-technical users;
- people applying to graduate schemes, internships, entry-level, and junior roles;
- fields such as business, economics, management, psychology, marketing, HR, operations, consulting, finance-adjacent, policy, and social science.

Primary v1 visa situations:

- Graduate Route holder who can work now but may need Skilled Worker sponsorship later.
- Student or applicant who needs sponsorship before starting the job.

Do not optimise v1 for:

- senior professionals;
- technical-only hiring;
- global relocation roles;
- auto-apply workflows;
- CV scoring;
- immigration-law completeness.

## 5. Product Positioning

Use this positioning:

> A visa-risk triage tool for international students: fresh job listings, official sponsor-register matching, and evidence-backed labels based on your visa situation.

Avoid these claims:

- "This tells you whether you are legally eligible."
- "All jobs shown are safe for international students."
- "This replaces GOV.UK, careers advisers, immigration advisers, or employer verification."
- "Student Circus is stale" unless backed by your own dated evidence.

Competitor language should be factual and restrained:

- Student Circus publicly positions itself as a university-partnered platform with pre-filtered visa-sponsored roles.
- Sponsor-checker tools usually answer whether an employer is licensed, not whether a specific role fits a user's visa situation.
- This project's wedge is status-aware triage, not guaranteed sponsorship.

## 6. Labels

The dashboard must use conservative labels.

| Label | Meaning | Example |
|---|---|---|
| Worth applying | No detected visa blocker for this user's situation. Still verify with employer. | Graduate Route user, no citizenship/security-clearance blocker, role starts within visa period. |
| Verify first | Potentially viable, but a key fact is missing or ambiguous. | Sponsor exists but JD says "must have right to work now and in future". |
| Likely blocked | Strong evidence suggests the user should not spend time applying. | "UK nationals only", "cannot sponsor", "permanent right to work required". |
| Unknown | Not enough evidence to judge. | Missing employer name, inaccessible JD, low-confidence sponsor match. |

Every label must show:

- the user status used;
- matched employer name and confidence;
- sponsor-register evidence if found;
- exact job-description phrase if a phrase drove the decision;
- a short "what to verify" note.

## 7. User Journey

1. User opens a public URL. No login.
2. User selects field, target cities, visa situation, visa expiry month, and whether they need future sponsorship.
3. Dashboard shows live jobs with label, reason, source, date, employer, and location.
4. User filters by city, field, source, freshness, sponsor-register status, and label.
5. User opens a job detail view with evidence, sponsor-register match, phrase highlights, salary/start-date notes, and original application link.
6. User tracks jobs locally with status, note, deadline, and export/import.
7. Optional v1 feature: paste any job description into a "Check this job" box to classify jobs not in the dashboard.

The paste checker is important because no scraper/API coverage will ever be complete.

## 8. Core Visa Engine

The visa engine is the showpiece, but it must be built as a signal engine, not a legal eligibility engine.

Inputs:

- job title;
- employer name from source;
- job description;
- location;
- salary if available;
- start date if available;
- source URL;
- user visa status;
- user visa expiry month;
- whether the user needs sponsorship now or later.

Layers:

1. Employer matching against the official GOV.UK Register of Licensed Sponsors.
2. Job-description phrase scan for sponsorship, right-to-work, citizenship, security clearance, and "now or in future" requirements.
3. Status-aware decision rules.
4. Optional LLM judge only for ambiguous cases, with exact evidence required.
5. Conservative fallback to Verify first or Unknown.

Non-negotiable:

- Deterministic facts override the LLM.
- The engine must cite evidence.
- The engine must never silently invent sponsor status.
- Low confidence must remain visible.

## 9. Data Sources for v1

Use sources that can be maintained.

In v1:

- GOV.UK Register of Licensed Sponsors for official sponsor data.
- Reed API for job listings.
- Adzuna API for job listings.
- Greenhouse Job Board API for known employer boards.
- Lever Postings API for known employer boards.

Out of v1:

- LinkedIn scraping.
- Indeed scraping.
- automated application submission.
- CV upload.
- user accounts.
- employer outreach.

Scrapers are a maintenance treadmill. The portfolio will look stronger if the pipeline is reliable and measured rather than broad and broken.

## 10. Architecture

Split the system into a central public-data pipeline and a local-only personalisation layer.

Central scheduled pipeline:

- fetch job data;
- normalise source fields;
- deduplicate jobs;
- match employer to sponsor register;
- scan job-description signals;
- classify base visa-risk signals;
- write static public `jobs.json`;
- write eval/debug metadata for development.

Frontend:

- fetches static `jobs.json`;
- stores profile and tracking data in browser local storage;
- applies user-status decision rules client-side where possible;
- lets users export/import their local data;
- sends no profile/CV data to the server.

Privacy claim:

> Your profile and tracked jobs stay in your browser unless you export them.

Do not claim GDPR disappears entirely. Hosting logs, analytics, and feedback forms still need care.

## 11. Stack

Recommended v1 stack:

| Layer | Choice | Reason |
|---|---|---|
| Frontend | React + TypeScript + Vite | Fast static app, easy deployment. |
| Styling | Tailwind CSS or simple CSS modules | Keep UI controlled and maintainable. |
| Pipeline | Python | Strong CSV, text, data, and eval tooling. |
| Entity matching | RapidFuzz | Transparent fuzzy matching and confidence scores. |
| Data output | Static JSON | Cheap, cacheable, no account system. |
| Scheduler | GitHub Actions | Daily refresh without server management. |
| Hosting | Cloudflare Pages or GitHub Pages | Static hosting is enough. |
| LLM judge | Optional, only ambiguous cases | Avoid cost and hallucination dependence. |

## 12. Evaluation

The project is not credible without evaluation.

Build a labelled set of 150-200 real job descriptions before the public demo.

Measure:

- sponsor match precision;
- false red rate, especially for Graduate Route users;
- false green rate, especially for sponsorship-needed users;
- unknown/ambiguous rate;
- evidence extraction accuracy;
- stale/dead-link rate;
- time saved in user testing.

The most harmful error is wrongly blocking a job a student could apply to. The second most harmful error is presenting a risky job as safe.

Publish metrics plainly in the README.

## 13. User Research

Before building the full dashboard, speak to at least 5 international students.

Ask them:

- What visa status are you on?
- How do you currently decide whether to apply?
- Which phrases in job ads confuse you?
- Which job boards do you check daily?
- What would make you trust or distrust a visa label?
- Show me 3 roles you were unsure about.

During testing, measure:

- can they understand the labels without explanation?
- do they trust the evidence panel?
- does the tool help them decide faster?
- which labels feel too strong or too vague?

This user research is part of the portfolio story. It shows problem discovery, not just implementation.

## 14. Build Sequence

Realistic estimate: 6-10 focused weekends.

1. User research: interview 5 students and collect real uncertain job ads.
2. Label taxonomy: finalise Worth applying, Verify first, Likely blocked, Unknown.
3. Sponsor-register matcher: download GOV.UK CSV, normalise names, produce confidence-scored matches.
4. JD phrase scanner: implement deterministic phrase categories and evidence spans.
5. Paste checker: classify one pasted job description before building the dashboard.
6. Evaluation set: label 150-200 descriptions and create metric scripts.
7. Job pipeline: Reed + Adzuna first, then Greenhouse/Lever for selected employers.
8. Static dashboard: search, filters, job detail, evidence, local tracking.
9. Daily refresh: GitHub Actions writes public `jobs.json`.
10. Student testing: 5 users, one week, fix confusion.
11. README + demo: explain problem, architecture, metrics, limitations, and failure cases.

## 15. Definition of Done

v1 is done when:

- a student can open one URL with no login;
- set visa status and expiry month;
- see fresh jobs with conservative visa-risk labels;
- inspect evidence behind each label;
- paste an external job description for checking;
- track jobs locally;
- export/import tracking data;
- understand that labels are signals, not legal advice;
- see public accuracy/error metrics from a labelled test set.

## 16. Key Risks

- Visa/legal complexity: reduce by using signal language and GOV.UK links.
- Bad labels can harm users: use conservative defaults and measure false red/false green rates.
- Job aggregation maintenance: start with APIs and known ATS feeds only.
- Sponsor matching errors: always expose match confidence and raw names.
- Too much scope: paste checker plus one or two sources is better than five unreliable sources.
- Weak portfolio story: avoid generic dashboard features; highlight user research, engine design, and evaluation.

## 17. Portfolio Story

Use this:

> I built a visa-risk triage dashboard for international students in the UK after finding that sponsor-only job search tools miss the Graduate Route nuance. The system combines official sponsor-register matching, job-description evidence extraction, and status-aware rules, then reports its own false-positive and false-negative rates on real job ads.

This story shows:

- problem identification;
- domain understanding;
- data engineering;
- applied AI restraint;
- product design for trust;
- evaluation discipline.

## 18. Current Reference Links

Checked on 2026-06-04:

- GOV.UK Register of Licensed Sponsors: https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers
- GOV.UK Skilled Worker visa job rules: https://www.gov.uk/skilled-worker-visa/your-job
- GOV.UK Graduate visa overview: https://www.gov.uk/graduate-visa
- Reed Jobseeker API: https://www.reed.co.uk/developers/jobseeker
- Adzuna API: https://developer.adzuna.com/
- Greenhouse Job Board API: https://developers.greenhouse.io/job-board
- Lever Postings API: https://github.com/lever/postings-api
- Student Circus public marketplace listing: https://marketplace.student.com/partners/student-circus
