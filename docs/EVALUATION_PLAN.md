# Evaluation Plan

## Goal

Assess whether the visa-risk engine is useful enough to trust as a triage tool, while clearly exposing its limitations.

## Evaluation Set

Create a labelled dataset of 150-200 real job-ad records.

Before the full set, maintain a smaller real seed set that can run through the
same evaluator. The seed set is allowed to be uncomfortable: it should expose
phrase misses, over-conservative labels, and evidence extraction gaps before
the frontend is polished.

Target mix:

- 50 obvious sponsor-positive or sponsor-register-matched roles;
- 50 obvious no-sponsorship or right-to-work blockers;
- 50 ambiguous roles;
- 25-50 graduate schemes and internships;
- include multiple sources: Reed, Adzuna, Greenhouse, Lever, and manually pasted roles.

For each item, store:

- source;
- URL;
- title;
- employer_raw;
- short source-permitted description excerpt or evidence snippet;
- location;
- salary_text if available;
- labelled sponsor-register match result;
- labelled phrase evidence;
- expected label for Graduate Route user;
- expected label for needs-sponsorship-before-start user;
- notes.

## Human Labelling Rules

Labels are based on evidence in the job ad and sponsor register, not private employer knowledge.

Use `unknown` when a human cannot reasonably judge from public evidence.

Each labelled item should include a short explanation:

- why this is likely blocked;
- why this is worth applying;
- what must be verified;
- why unknown is appropriate.

## Metrics

### Sponsor Matching

- precision of high-confidence matches;
- recall against obvious sponsor-register names;
- number of low-confidence matches;
- examples of false matches.

### Classification

Report separately for each visa situation:

- false red rate;
- false green rate;
- verify-first rate;
- unknown rate;
- exact evidence extraction accuracy.

Definitions:

- False red: engine says Likely blocked, human label says Worth applying or Verify first.
- False green: engine says Worth applying, human label says Likely blocked.
- Evidence miss: engine gives the right label but cites the wrong phrase or no phrase.

## Acceptance Targets for v1

These are targets, not promises:

- high-confidence sponsor match precision: at least 95%;
- Graduate Route false red rate: below 5%;
- sponsorship-needed false green rate: below 10%;
- evidence extraction accuracy: at least 85%;
- unknown/verify-first allowed when evidence is genuinely missing.

If these targets are not met, publish the gap and keep labels more conservative.

## User Testing

Test with at least 5 international students.

Tasks:

1. Set up your profile.
2. Find 3 jobs you would apply to.
3. Find 2 jobs you would verify before applying.
4. Paste a job you recently found elsewhere.
5. Explain what the label means.
6. Explain what evidence made you trust or distrust the label.

Observe:

- confusion around labels;
- whether users overtrust green labels;
- whether users understand sponsor-register limitations;
- whether evidence reduces uncertainty;
- whether the tool changes application choices.

## Reporting

The README/demo should report:

- dataset size;
- source mix;
- label distribution;
- main metrics;
- known failure modes;
- examples where the engine is intentionally conservative.

Do not claim "accurate" without showing what accuracy means.

Report synthetic smoke-test metrics separately from real-seed metrics. Synthetic
100% results show the harness works; they do not prove the product works on
real job ads.
