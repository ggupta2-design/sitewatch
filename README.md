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

## Status

SiteWatch 0.1.0 is under active development.
