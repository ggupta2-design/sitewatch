# Baselines and change detection

SiteWatch baselines record the stable metadata from one completed health-check run.
They make later changes visible without storing response bodies.

## Create a baseline

Keep baselines with private monitoring data, outside a public repository:

```bash
sitewatch snapshot ~/private/sitewatch-targets.json \
  --output ~/private/sitewatch-baseline.json
```

SiteWatch checks every configured target before creating the file. The command
returns 0 when the snapshot is healthy, 1 when it captured an unhealthy run,
and 2 for invalid input or output. It never replaces an existing file.

A baseline contains the schema version and, for each target:

- name and configured URL;
- evaluated health state;
- response status;
- normalized content type;
- SHA-256 response fingerprint.

It excludes response bodies, timings, byte counts, final redirect URLs, and
check timestamps. A fingerprint can still reveal whether two bodies are equal,
so treat baseline files as private monitoring records.

## Validate without network access

```bash
sitewatch validate-baseline ~/private/sitewatch-baseline.json
sitewatch validate-baseline ~/private/sitewatch-baseline.json --json
```

Validation is strict and local. Unknown fields, unsupported schema versions,
duplicate names, unsafe URLs, malformed statuses, and invalid digests are
rejected without resolving a hostname or making an HTTP request.

## Compare a current run

```bash
sitewatch compare \
  ~/private/sitewatch-targets.json \
  ~/private/sitewatch-baseline.json

sitewatch compare \
  ~/private/sitewatch-targets.json \
  ~/private/sitewatch-baseline.json \
  --json --redact-urls \
  --output ~/private/reports/site-changes.json
```

Comparisons match unique target names case-insensitively. They classify each
target as unchanged, changed, new, or missing. Changed targets list only field
names—such as `status`, `content_type`, or `sha256`—rather than old and new
values. Volatile timings, byte counts, and timestamps do not cause drift.

Exit status 0 means the current run is healthy and unchanged. Status 1 means
the current run is unhealthy or drift exists. Status 2 means configuration,
baseline, or output validation failed.

## Intentional changes

SiteWatch does not overwrite or update a trusted baseline in place. After
reviewing an intentional change, create a new baseline at a new path, retain or
remove the old file according to your own retention policy, and update any
automation to use the reviewed file.
