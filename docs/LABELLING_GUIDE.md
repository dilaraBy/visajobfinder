# Labelling Guide

Use this guide when manually reviewing real job ads.

## Public vs Local Data

Public repo files should store:

- source URL;
- title;
- employer;
- location;
- short excerpt;
- evidence phrase;
- labels;
- human notes;
- description hash if available.

Do not store full copied job descriptions in public repo files.

Local-only files may store full job descriptions for development and evaluation:

- `data/eval/full_jds.local.json`
- `data/eval/full_jds.local.jsonl`
- `data/raw/`

These paths are ignored by `.gitignore`.

## Why Not Full JDs in the Public Label File?

Full job descriptions are third-party text and may change or disappear. Keeping full copies in the public repo creates avoidable copyright, freshness, and maintenance problems.

Use the labelled set as evaluation truth, not as a training corpus in v1.

The engine should learn from:

- explicit rules;
- labelled expected outputs;
- evidence categories;
- sponsor-register matching;
- measured errors.

It should not depend on memorising full job descriptions.

## Labelling Fields

For each job, confirm:

- `role_level`;
- `graduate_route` expected label;
- `needs_sponsorship_before_start` expected label;
- evidence phrase;
- whether the job belongs in the default dashboard;
- whether the record is useful only for visa-phrase testing.

## Career-Level Labels

Use:

- `graduate`
- `internship`
- `graduate_scheme`
- `entry_level`
- `junior`
- `junior_or_mid`
- `associate`
- `mid`
- `senior`
- `graduate_to_senior`
- `unclear`

Senior jobs can remain in the eval set if they contain useful visa wording, but they should not appear in the default v1 dashboard.

## Visa Labels

Use:

- `worth_applying`
- `verify_first`
- `likely_blocked`
- `unknown`

## Label Rules

### Graduate Route

Usually `worth_applying` when:

- the user has current right to work;
- there is no citizenship-only, security-clearance-only, permanent right-to-work, or explicit future-sponsorship blocker;
- the role timing appears covered by the visa.

Usually `verify_first` when:

- the ad says "right to work now and in the future";
- the ad says "without sponsorship";
- the ad asks sponsorship questions but does not reject sponsorship;
- future sponsorship may be needed later.

Usually `likely_blocked` when:

- the ad says no sponsorship now or in the future;
- the ad requires permanent/unrestricted right to work;
- citizenship/security wording is a hard blocker.

### Needs Sponsorship Before Start

Usually `likely_blocked` when:

- the ad says no sponsorship;
- the ad requires right to work without sponsorship;
- the ad says sponsorship cannot be provided.

Usually `verify_first` when:

- the employer is a sponsor or asks sponsorship questions, but does not confirm this role can be sponsored;
- salary or Skilled Worker fit is missing;
- role-level sponsorship is unclear.

Usually `worth_applying` only when:

- sponsorship is explicitly available for the role;
- no blocker appears;
- salary/skill level looks plausible or is stated.

## Review Statuses

Use these during manual review:

- `needs_review`
- `confirmed`
- `change_recommended`
- `remove_from_eval`

## Default Dashboard Rule

Show by default:

- internships;
- graduate schemes;
- entry-level roles;
- junior roles;
- relevant associate roles.

Hide by default:

- senior;
- lead;
- principal;
- staff;
- director;
- head-of roles.

These hidden jobs can still be useful in the eval set for phrase scanning.
