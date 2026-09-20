# Reliability policies and alert decisions

SiteWatch can turn bounded history evidence into a deterministic local decision.
It does not send notifications. Instead, it produces a privacy-safe result that
scripts, CI workflows, or reviewed notification systems can consume.

## Define a strict policy

A schema-version-1 policy contains exactly these fields:

```json
{
  "schema_version": 1,
  "name": "conservative-public-site",
  "minimum_availability": 99.0,
  "maximum_open_incidents": 0,
  "maximum_monitoring_gaps": 0,
  "maximum_errors": 0,
  "maximum_gap_seconds": 900
}
```

The availability bound is from 0 through 100. Count thresholds are integers from
0 through 10,000. The monitoring interval is an integer from 1 through
31,536,000 seconds. Unknown fields and unsupported schema versions are rejected.

The public example is intentionally conservative. Copy it to a private location
and choose thresholds that reflect the cadence and purpose of your checks.

## Validate locally

```bash
sitewatch policy-validate ~/private/sitewatch-policy.json
sitewatch policy-validate ~/private/sitewatch-policy.json --json
```

Validation reads only the policy file. It performs no DNS lookup or HTTP
request.

## Evaluate recorded evidence

```bash
sitewatch policy-check \
  ~/private/history/sitewatch-002.json \
  ~/private/sitewatch-policy.json

sitewatch policy-check \
  ~/private/history/sitewatch-002.json \
  ~/private/sitewatch-policy.json \
  --json --output ~/private/reports/decision.json
```

Four checks run in a stable order:

1. the lowest per-target availability meets the minimum;
2. open incidents do not exceed the limit;
3. per-target monitoring gaps do not exceed the limit;
4. error samples do not exceed the limit.

Status 0 means every check passed. Status 1 means an alert decision was produced.
Status 2 means the history, policy, or output request was invalid. Exports are
atomic and cannot replace an existing file.

## Interpret decisions carefully

Reports contain the policy name, aggregate sample and target counts, stable
finding codes, and observed-versus-limit values. They omit target names, URLs,
timestamps, HTTP statuses, error-code values, latency, fingerprints, and
response content.

A decision is only as current and complete as its history. SiteWatch does not
schedule checks, infer continuous state, contact recipients, or guarantee that a
notification system accepted a report. Treat the output as a bounded decision
input, not a contractual service-level assertion.
