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
