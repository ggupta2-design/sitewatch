# Using SiteWatch

Install SiteWatch in a virtual environment:

```bash
python -m pip install -e .
```

Copy the public example to a private location:

```bash
cp examples/targets.json ~/private/sitewatch-targets.json
```

## Configuration format

SiteWatch requires a strict schema-version-1 JSON object with 1 to 100 targets.
Every target explicitly provides:

- a unique `name`;
- an HTTP or HTTPS `url`;
- 1 to 10 acceptable `expected_statuses`;
- `timeout_seconds` from 0.1 to 60;
- `max_bytes` from 1 to 10,000,000;
- an `expected_content_type` string or `null`;
- an `allow_redirects` boolean.

Unknown fields, unsupported versions, duplicate names, unsafe URLs, and values
outside these bounds are rejected.

## Validate without network access

```bash
sitewatch validate ~/private/sitewatch-targets.json
sitewatch validate ~/private/sitewatch-targets.json --json
```

Validation reads only the local configuration. It does not resolve hostnames or
make HTTP requests.

## Run health checks

```bash
sitewatch check ~/private/sitewatch-targets.json
sitewatch check ~/private/sitewatch-targets.json --json
```

Each target is resolved and checked sequentially. SiteWatch compares the
response status and optional content type, enforces redirect policy, reads no
more than the configured byte limit, and computes a SHA-256 fingerprint without
retaining the body.

Exit status 0 means every target is healthy, 1 means at least one target is
unhealthy or could not be checked, and 2 means the configuration or output
request is invalid.

## Track changes against a baseline

```bash
sitewatch snapshot ~/private/sitewatch-targets.json \
  --output ~/private/sitewatch-baseline.json

sitewatch validate-baseline ~/private/sitewatch-baseline.json

sitewatch compare \
  ~/private/sitewatch-targets.json \
  ~/private/sitewatch-baseline.json \
  --json --redact-urls
```

Snapshots retain body-free stable metadata and cannot replace an existing file.
Comparisons identify changed, new, missing, and unchanged targets. They ignore
volatile timing, byte-count, and timestamp data. A comparison exits 1 when the
current run is unhealthy or any drift is found.

See [baselines.md](baselines.md) for the strict schema, privacy model, and
intentional-change workflow.

## Audit links on a public page

```bash
sitewatch links https://example.com/docs/ \
  --max-links 50 \
  --max-page-bytes 1000000 \
  --timeout-seconds 10

sitewatch links https://example.com/docs/ \
  --json --redact-urls \
  --output ~/private/reports/links.json
```

Link audits are same-origin by default. Use `--include-external` only when
external requests are intended. SiteWatch resolves relative links, removes
fragments, deduplicates destinations, and checks them sequentially. Source-page
content is bounded and discarded after parsing; destination bodies are not read.

Status 0 means every checked link is healthy. Status 1 covers a source error,
empty audit, broken link, or destination error. Status 2 covers invalid options,
URLs, or output. See [link-audits.md](link-audits.md) for limits, privacy, and
interpretation guidance.

## Build availability history

```bash
sitewatch history-create ~/private/sitewatch-targets.json \
  --output ~/private/history/sitewatch-001.json

sitewatch history-append \
  ~/private/sitewatch-targets.json \
  ~/private/history/sitewatch-001.json \
  --output ~/private/history/sitewatch-002.json

sitewatch history-validate ~/private/history/sitewatch-002.json

sitewatch availability ~/private/history/sitewatch-002.json \
  --minimum-availability 99 \
  --json
```

History files contain bounded state, status, latency, error-code, name, and UTC
timestamp metadata. They omit URLs, fingerprints, content types, sizes, and
response bodies. Appending always writes a new file and requires strictly later
samples.

Availability reports aggregate healthy, unhealthy, and error counts plus
latency and observation windows. Status 0 means every target meets the selected
goal; status 1 means at least one does not; status 2 means an input or output is
invalid. See [history.md](history.md) for schema, retention, and interpretation
guidance.

## Review incidents and monitoring gaps

```bash
sitewatch incidents ~/private/history/sitewatch-002.json \
  --maximum-gap-seconds 900

sitewatch incidents ~/private/history/sitewatch-002.json \
  --json --fail-on-any-incident
```

Incident analysis is local and read-only. Consecutive unhealthy and error
samples become an incident until a later healthy sample records recovery.
Per-target intervals larger than the selected bound are reported as monitoring
gaps, preventing sparse evidence from being presented as continuous monitoring.

By default, status 1 indicates an open incident or monitoring gap. The optional
strict policy also returns 1 for fully recovered historical incidents. Reports
omit URLs, statuses, error details, fingerprints, and response content. See
[incidents.md](incidents.md) for definitions and interpretation limits.

## Redact and export

```bash
sitewatch check ~/private/sitewatch-targets.json \
  --json \
  --redact-urls \
  --output ~/private/reports/site-health.json
```

URL redaction removes configured and final URLs from reports. Exports are
created atomically and never replace an existing file. SiteWatch prints only the
new filename after a successful export.

Read [privacy-and-safety.md](privacy-and-safety.md) before checking untrusted
targets or sharing monitoring reports.
