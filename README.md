# SiteWatch

SiteWatch is a local-first command-line tool for running predictable, bounded
website health checks.

The first release focuses on safe monitoring fundamentals:

- validate strict, versioned JSON target configurations;
- accept only explicit HTTP and HTTPS targets;
- reject embedded credentials, localhost names, and private IP literals;
- bound timeouts, response sizes, redirects, and target counts;
- evaluate expected status codes and optional content-type rules;
- calculate SHA-256 response fingerprints without storing response bodies;
- produce deterministic text or JSON reports;
- write reports atomically without replacing existing files;
- distinguish healthy, unhealthy, and invalid runs through exit codes;
- require no account, API key, hosted service, or third-party dependency.

SiteWatch is being built as part of an eight-week automation project challenge.
Real monitoring targets should remain in private configuration files.

## Quick start

```bash
python -m pip install -e .
sitewatch validate examples/targets.json
sitewatch check examples/targets.json --json
sitewatch check examples/targets.json \
  --json \
  --redact-urls \
  --output sitewatch-output.json
```

Validation never makes a network request. Health checks resolve each destination,
enforce configured bounds, and run sequentially. Exit status 0 means healthy, 1
means attention is required, and 2 means invalid input or output.

See the [usage guide](docs/usage.md) and
[privacy and safety guide](docs/privacy-and-safety.md) before monitoring
untrusted targets or sharing reports.

## Status

SiteWatch 0.1.0 provides the first complete monitoring workflow.
