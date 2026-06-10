# Project Decisions

This document records the current product and engineering decisions for making VisaJobFinder useful to international students and credible as a portfolio project.

## Product Direction

The product should be positioned as:

> Evidence-backed visa-risk triage for UK international students.

The wedge is not job-board breadth. The wedge is status-aware interpretation of employer sponsorship signals, right-to-work phrases, missing evidence, and user visa situation.

## MVP Order

1. Make the real seed evaluation set executable.
2. Improve deterministic phrase coverage using real job-ad wording.
3. Build a paste-checker web UI with evidence, missing evidence, limitations, and what-to-verify prompts.
4. Add a small dashboard only after the engine can report honest metrics on real labels.
5. Add local-only tracking/export once users can already classify and review jobs.

## Senior Engineering Decisions

- Keep deterministic rules as the primary business logic.
- Use an LLM only later for ambiguous cases, and only if it cites exact phrases.
- Treat missing salary, missing timing, and low-confidence sponsor matches as verification work, not green lights.
- Keep sponsor-register confidence visible.
- Avoid high-confidence sponsor matches for subset names with extra entity context unless the score independently earns that confidence.
- Make real evaluation files fail tests if they silently produce zero cases.

## Product Management Decisions

- Build the paste checker first because users can bring jobs from any source.
- Defer dashboard polish until the engine has measured real-seed performance.
- Do not add accounts, CV upload, auto-apply, email digests, or cover-letter generation in v1.
- Do not scrape LinkedIn or Indeed.
- Make "Worth applying" visually and verbally tied to "No detected blocker; verify with employer."
- Show missing evidence as prominently as found evidence.

## LinkedIn / Portfolio Narrative

Use this story:

> I found that international students waste time on UK roles where visa constraints become clear too late. I built a conservative triage engine that combines sponsor-register matching, exact job-description evidence, and status-aware rules for Graduate Route and sponsorship-before-start users. I measured false red, false green, verify-first, unknown, and evidence extraction rates on labelled examples, then used those results to guide the product.

Do not claim:

- "This tells users if they are eligible."
- "These jobs are safe."
- "This employer will sponsor."
- "The engine is accurate" without the dataset and metric.

## Current Known Gaps

- No frontend exists yet.
- GOV.UK sponsor-register ingestion is not implemented yet; current sponsor data is a fixture.
- Public `jobs.json` is sample data, not live listings.
- Real seed evidence extraction is still below the v1 target and should guide the next phrase-rule pass.
- Salary and Skilled Worker occupation-code fit are not fully assessed.
- Source freshness and dead-link metrics are not implemented yet.
