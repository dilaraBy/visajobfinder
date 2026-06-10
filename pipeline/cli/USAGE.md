# Pipeline And CLI Usage

Run all examples from the repository root in PowerShell.

These commands default to local fixture data. Reed and Adzuna live adapter modes
exist, but they require API credentials and report `source_runs[].status:
"error"` when the credentials are missing. Greenhouse and Lever are currently
fixture-backed only. Live GOV.UK register download is not implemented yet; pass
a parsed sponsor CSV explicitly when running the build, eval, or paste-check
commands.

## Sponsor-Register Load Check

Use this as the current sponsor-ingestion smoke check. It verifies that the CSV
can be loaded by the matcher and that an example employer returns visible match
evidence.

```powershell
python -c "from pathlib import Path; from pipeline.sponsor_register.matcher import SponsorMatcher; path=Path('data/sponsor_register/sample_sponsors.csv'); assert path.exists(), 'Missing sponsor-register CSV: ' + str(path); matcher=SponsorMatcher.from_csv(path); match=matcher.match('Example Ltd').to_dict(); print('Loaded', len(matcher.records), 'sponsor record(s). Example Ltd ->', match['matched_name'], '(' + match['confidence_band'] + ')')"
```

Expected shape:

```text
Loaded 6 sponsor record(s). Example Ltd -> Example UK Limited (high)
```

If it fails with `Missing sponsor-register CSV`, restore
`data\sponsor_register\sample_sponsors.csv` or pass a parsed sponsor CSV to the
commands below with `--sponsor-register`.

## Source Build

Build the static public jobs file from local source JSON:

```powershell
python -m pipeline.build_jobs --source-file .\data\sources\sample_jobs.json --sponsor-register .\data\sponsor_register\sample_sponsors.csv --output .\data\public\jobs.json
```

Build from fixture-backed source adapters:

```powershell
python -m pipeline.build_jobs --source-adapter reed --source-adapter adzuna --source-adapter greenhouse --source-adapter lever --sponsor-register .\data\sponsor_register\sample_sponsors.csv --output .\data\public\jobs.json
```

Run a live Reed or Adzuna adapter only when credentials are available:

```powershell
$env:REED_API_KEY = "<your Reed API key>"
python -m pipeline.build_jobs --source-adapter reed:live --sponsor-register .\data\sponsor_register\sample_sponsors.csv --output .\data\public\jobs.json
```

Expected shape:

```text
Wrote 4 deduplicated job(s) to .\data\public\jobs.json from 1 source run(s).
```

For a non-destructive verification run, write to a temporary workspace file:

```powershell
python -m pipeline.build_jobs --source-file .\data\sources\sample_jobs.json --sponsor-register .\data\sponsor_register\sample_sponsors.csv --output .\data\public\jobs.verify.json
Remove-Item -LiteralPath .\data\public\jobs.verify.json
```

Action notes:

- If `--sponsor-register` points to a missing CSV, the command fails while
  loading the matcher. Restore the CSV or pass the correct parsed register path.
- If `--source-file` points to a missing or invalid JSON file, the build can
  still write an output file with a `source_runs[].status` of `error` and zero
  jobs from that source. Inspect `data\public\jobs.json` before treating the
  build as successful.
- If an API-backed source adapter is missing an API key, the build still writes
  output for other sources and records the failure in `source_runs[]`.

## Sample Eval

Run the synthetic labelled evaluation set:

```powershell
python -m pipeline.eval.run_eval --dataset .\data\eval\labelled_jobs.sample.json --sponsor-register .\data\sponsor_register\sample_sponsors.csv
```

The sample eval should report 7 records and 14 classification cases. It is a
smoke test for labels, evidence extraction, and sponsor matching; it is not a
quality claim for real ads.

Use JSON output for scripts:

```powershell
python -m pipeline.eval.run_eval --dataset .\data\eval\labelled_jobs.sample.json --sponsor-register .\data\sponsor_register\sample_sponsors.csv --json
```

## Real-Seed Eval

Run the real public-ad seed evaluation set:

```powershell
python -m pipeline.eval.run_eval --dataset .\data\eval\labelled_jobs.real.json --sponsor-register .\data\sponsor_register\sample_sponsors.csv
```

The real seed eval should report 20 records and 40 classification cases. Publish
the false red, false green, verify-first, unknown, and evidence metrics with the
dataset size. Do not describe the engine as legally accurate.

If eval fails because the dataset path is missing, restore the relevant file in
`data\eval` or pass a reviewed labelled dataset with `--dataset`.

## Paste Checker

Classify a single pasted job description:

```powershell
python -m pipeline.cli.paste_check --title "Graduate Analyst" --employer "Example Ltd" --location "London" --salary "GBP 35,000 per year" --visa-situation graduate_route --needs-future-sponsorship --description "Graduate analyst role. Candidates must have the right to work in the UK." --sponsor-register .\data\sponsor_register\sample_sponsors.csv
```

Pipe a longer pasted description:

```powershell
Get-Content .\pipeline\fixtures\sample_job_description.txt | python -m pipeline.cli.paste_check --title "Graduate Analyst" --employer "Example Ltd" --visa-situation needs_sponsorship_before_start --salary "GBP 35,000 per year" --sponsor-register .\data\sponsor_register\sample_sponsors.csv
```

Use JSON only for scripts:

```powershell
python -m pipeline.cli.paste_check --title "Graduate Analyst" --employer "Example Ltd" --visa-situation graduate_route --description "Visa sponsorship available for suitable candidates." --sponsor-register .\data\sponsor_register\sample_sponsors.csv --output json
```

Use a file instead of inline text:

```powershell
python -m pipeline.cli.paste_check --title "Graduate Analyst" --employer "Example Ltd" --description-file .\pipeline\fixtures\sample_job_description.txt --visa-situation graduate_route --needs-future-sponsorship --sponsor-register .\data\sponsor_register\sample_sponsors.csv --output summary
```

Action notes:

- If no `--description`, `--description-file`, or piped stdin is provided, the
  CLI exits with: `Provide --description, --description-file, or pipe a description on stdin.`
- If `--sponsor-register` is missing, the CLI exits with:
  `Sponsor-register file not found: <path>`. Restore the CSV or pass the correct
  parsed sponsor-register file.
- If `--description-file` is missing, provide the correct local text-file path
  or use `--description`.

Labels are visa-risk triage signals, not legal eligibility decisions. Sponsor-register matches are employer-level evidence and do not prove a specific role will be sponsored.
