# Product Spec

## Product Name

Working name: Visa-Aware Job Triage Dashboard.

## Goal

Help international students in the UK decide faster whether a graduate or junior role is worth applying to, needs verification, is likely blocked by visa constraints, or cannot be judged from available evidence.

## Product Boundary

This product provides visa-risk signals. It does not provide legal advice, immigration advice, or definitive eligibility decisions.

## Primary Users

### Graduate Route Holder

Can usually work in most jobs now, but may need Skilled Worker sponsorship later if they want to stay beyond their Graduate visa.

Needs to know:

- Is there an immediate blocker?
- Does the role ask for permanent or unrestricted right to work?
- Does the employer have sponsor-register presence for future conversion?
- Is the role likely to meet Skilled Worker salary/occupation constraints later?

### Needs Sponsorship Before Start

Cannot start the role unless sponsorship is available before employment begins.

Needs to know:

- Is the employer on the sponsor register?
- Does the job ad explicitly mention sponsorship?
- Does the job ad explicitly reject sponsorship?
- Is salary/occupation information missing?

## v1 Screens

Build order:

1. Paste Checker with evidence and missing-evidence panels.
2. Job Detail evidence view.
3. Dashboard list and filters.
4. Local tracking, notes, and export/import.

The paste checker comes first because dashboard coverage will never be complete, and it is the fastest way for a user to test a real job they already found.

### Setup

Fields:

- target role keywords;
- target locations;
- visa situation;
- visa expiry month;
- future sponsorship needed: yes/no/unsure;
- preferred freshness window.

Store setup data in browser local storage only.

### Dashboard

Job list columns/cards:

- label;
- title;
- employer;
- location;
- source;
- posted or fetched date;
- one-line reason;
- sponsor-register badge;
- save/track action.

Filters:

- search;
- location;
- source;
- freshness;
- label;
- sponsor-register status;
- remote/hybrid/on-site if available;
- salary shown/missing if available.

Sorts:

- newest;
- label priority;
- best keyword match;
- deadline soonest if available.

### Job Detail

Show:

- full label and reason;
- exact evidence phrase;
- sponsor-register match and confidence;
- raw employer name from job source;
- matched sponsor-register organisation name;
- salary and start-date notes;
- what to verify with employer;
- original apply link;
- local tracking controls.

Every detail view must show found evidence and missing evidence. A sponsor-register match must be labelled as employer-level evidence, not proof that the specific role will be sponsored.

### Paste Checker

Inputs:

- job title;
- employer;
- job description;
- location optional;
- salary optional;
- source URL optional.

Outputs:

- same label system as dashboard;
- evidence;
- sponsor-register match;
- what to verify.

This feature is the first usable MVP surface because dashboard coverage will never be complete.

### Tracking

Local fields:

- saved;
- status: interested, applied, interview, rejected, offer, archived;
- note;
- deadline;
- last checked date.

Must support export/import as JSON.

## Copy Rules

Use:

- "No detected blocker"
- "Verify this with the employer"
- "Sponsor-register match"
- "Evidence found"
- "Evidence missing"
- "Likely blocked for your selected visa situation"

Avoid:

- "Eligible"
- "Guaranteed"
- "Safe"
- "Can sponsor"
- "Will sponsor"
- "Visa approved"

## Success Metrics

Product usefulness:

- users understand labels without explanation;
- users can decide what to do with a job in under 60 seconds;
- users report fewer wasted applications;
- users trust the evidence panel more than a black-box score.

Technical credibility:

- sponsor matching is measured;
- false red and false green rates are reported;
- stale/dead-link rate is reported;
- limitations are visible.

Portfolio credibility:

- the README separates implemented features from planned features;
- real-seed metrics are shown separately from synthetic smoke-test metrics;
- failure modes are described plainly;
- the demo shows evidence, missing evidence, and what to verify, not only polished UI.

## v1 Non-Goals

- employer accounts;
- user accounts;
- CV upload;
- auto-apply;
- cover-letter generation;
- scraping LinkedIn or Indeed;
- immigration-law completeness;
- sponsorship guarantee.
