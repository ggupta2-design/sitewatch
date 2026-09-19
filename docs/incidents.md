# Incident timelines and monitoring gaps

SiteWatch can analyze an existing availability history without making network
requests. The analysis identifies observed incident sequences, recoveries, open
incidents, and intervals where monitoring evidence is too sparse.

## Analyze a history locally

```bash
sitewatch incidents ~/private/history/sitewatch-002.json
sitewatch incidents ~/private/history/sitewatch-002.json --json
```

An incident begins with an unhealthy or error sample and continues through
consecutive non-healthy samples for the same target. The first later healthy
sample records a recovery. If no later healthy sample exists, the incident is
open.

The report contains target names, incident timestamps, affected-sample counts,
unhealthy and error counts, maximum observed request duration, and observed
recovery spans. It omits URLs, HTTP statuses, error-code values, fingerprints,
content types, response sizes, and bodies.

## Require a monitoring cadence

```bash
sitewatch incidents ~/private/history/sitewatch-002.json \
  --maximum-gap-seconds 900
```

SiteWatch compares adjacent samples separately for each target. An interval
strictly greater than the selected bound is reported as a monitoring gap. The
limit must be an integer from 1 second through 31,536,000 seconds.

Gaps matter because a long interval without observations cannot establish what
happened between checks. They are reported independently from incidents and do
not manufacture failure or recovery samples.

## Use exit statuses in automation

By default, status 1 means the history contains an open incident or a monitoring
gap. A history containing only recovered incidents returns 0, allowing current
attention to be distinguished from past recovery.

Use strict history review when any incident should fail automation:

```bash
sitewatch incidents ~/private/history/sitewatch-002.json \
  --fail-on-any-incident
```

Status 2 means the history, gap bound, or output request is invalid.

## Export safely

```bash
sitewatch incidents ~/private/history/sitewatch-002.json \
  --maximum-gap-seconds 900 \
  --json \
  --output ~/private/reports/incidents.json
```

Exports are atomic and cannot replace an existing file. Keep reports private
when target names, timestamps, incident patterns, latency, or monitoring cadence
could disclose operational details.

Incident spans are observation-based. A recovery time is the first healthy
sample after failures, not proof of the exact moment service recovered. An open
incident means no recovery was observed in the supplied history; it does not
prove the service remains unavailable now.
