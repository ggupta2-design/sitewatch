# Availability history and reliability goals

SiteWatch can retain bounded health metadata across checks and summarize
availability without storing URLs, fingerprints, content types, or response
bodies.

## Create an immutable history

```bash
sitewatch history-create ~/private/sitewatch-targets.json \
  --output ~/private/history/sitewatch-001.json
```

The command performs the configured health checks and creates a strict
schema-version-1 history. Each sample contains only:

- target name;
- UTC check timestamp;
- evaluated state;
- HTTP status or `null`;
- request duration in milliseconds;
- stable error code or `null`.

A history contains from 1 to 10,000 samples. Target names and timestamps must be
unique together. The command returns 0 for a healthy run, 1 when the run was
unhealthy, and 2 for invalid input or output.

## Append without rewriting trusted history

```bash
sitewatch history-append \
  ~/private/sitewatch-targets.json \
  ~/private/history/sitewatch-001.json \
  --output ~/private/history/sitewatch-002.json
```

SiteWatch reads the previous history, performs a new check, and writes a new
file. It never alters or replaces the input. New samples must be strictly later
than the existing history, preventing accidental replay or reordering.

Use distinct output names and manage retention according to your own security
and audit requirements.

## Validate without network access

```bash
sitewatch history-validate ~/private/history/sitewatch-002.json
sitewatch history-validate ~/private/history/sitewatch-002.json --json
```

Validation is local and strict. Unknown fields, unsupported versions, invalid
states or timestamps, duplicate samples, and values outside documented bounds
are rejected without making a network request.

## Summarize availability

```bash
sitewatch availability ~/private/history/sitewatch-002.json \
  --minimum-availability 99

sitewatch availability ~/private/history/sitewatch-002.json \
  --minimum-availability 99 \
  --json \
  --output ~/private/reports/availability.json
```

Summaries include healthy, unhealthy, and error counts; availability percentage;
average and maximum observed duration; and the first and last timestamps for
each target. Targets are sorted deterministically by name.

Exit status 0 means every target meets the requested goal. Status 1 means at
least one target is below it. Status 2 means the history, goal, or output is
invalid.

Availability is calculated as healthy samples divided by all samples, so
unhealthy and transport-error samples both reduce the percentage. These metrics
describe only the recorded checks. They are not proof of continuous uptime and
should not be presented as a contractual service-level measurement.
