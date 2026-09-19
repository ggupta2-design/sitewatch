# SiteWatch

SiteWatch is a local-first command-line tool for running predictable, bounded
website health checks and detecting reviewed changes over time.

SiteWatch provides safe monitoring fundamentals:

- validate strict, versioned JSON target configurations;
- accept only explicit HTTP and HTTPS targets;
- reject embedded credentials, localhost names, and private IP literals;
- bound timeouts, response sizes, redirects, and target counts;
- evaluate expected status codes and optional content-type rules;
- calculate SHA-256 response fingerprints without storing response bodies;
- create strict, body-free baseline snapshots without overwriting files;
- compare current results with a baseline by stable target name;
- report changed, new, missing, and unchanged targets without old/new values;
- discover and check bounded same-origin links from public HTML pages;
- opt in to external link checks while preserving destination safeguards;
- create immutable, bounded availability histories without URLs or bodies;
- summarize reliability goals and latency across recorded health samples;
- reconstruct observed incident timelines, recoveries, and monitoring gaps;
- produce deterministic text or JSON reports with optional URL redaction;
- distinguish healthy, drifted, unhealthy, and invalid runs through exit codes;
- require no account, API key, hosted service, or third-party dependency.

SiteWatch is being built as part of an eight-week automation project challenge.
Real monitoring targets and baselines should remain in private files.

## Quick start

```bash
python -m pip install -e .
sitewatch validate examples/targets.json
sitewatch check examples/targets.json --json

sitewatch snapshot examples/targets.json --output sitewatch-baseline.json
sitewatch validate-baseline sitewatch-baseline.json
sitewatch compare examples/targets.json sitewatch-baseline.json \
  --json --redact-urls

sitewatch links https://example.com/ --max-links 25 --redact-urls

sitewatch history-create examples/targets.json --output history-001.json
sitewatch availability history-001.json --minimum-availability 99
sitewatch incidents history-001.json --maximum-gap-seconds 900
```

Configuration and baseline validation never make network requests. Health checks
resolve each destination, enforce configured bounds, and run sequentially.
Snapshot and report exports are atomic and non-overwriting.

Exit status 0 means the requested check is healthy and, for comparisons,
unchanged. Status 1 means attention is required because health failed or drift
was detected. Status 2 means invalid input or output.

See the [usage guide](docs/usage.md),
[baseline guide](docs/baselines.md),
[link-audit guide](docs/link-audits.md),
[availability-history guide](docs/history.md),
[incident-analysis guide](docs/incidents.md), and
[privacy and safety guide](docs/privacy-and-safety.md) before monitoring
untrusted targets or sharing reports.

## Status

SiteWatch 0.5.0 adds read-only incident timelines, recovery insights, and monitoring-gap detection.
