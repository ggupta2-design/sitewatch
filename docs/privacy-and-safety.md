# Privacy and network safety

SiteWatch makes outbound HTTP requests, so configuration and target handling
must be treated as security-sensitive.

## Target safeguards

SiteWatch accepts only HTTP and HTTPS URLs. It rejects:

- embedded usernames or passwords;
- URL fragments and control characters;
- localhost and `.local` hostnames;
- loopback, private, link-local, reserved, and otherwise non-public IP literals;
- hostnames that resolve to any non-public address;
- redirect destinations that fail the same URL and DNS checks.

DNS can change between validation and connection. These checks reduce accidental
private-network access but are not a complete sandbox. Run SiteWatch from an
appropriately restricted network when checking untrusted configurations.

## Resource limits

Each target has an explicit timeout from 0.1 to 60 seconds and response limit
from 1 byte to 10 MB. A configuration contains at most 100 uniquely named
targets. Checks run sequentially for predictable network load. Response bodies
are read only within the configured bound, hashed when complete, and never
retained in result objects or reports.

Redirects are disabled by default and must be enabled per target. Redirects are
still subject to the public-destination checks.

## Credentials and private data

Do not put authentication tokens, cookies, passwords, private URLs, or customer
data in configuration files. SiteWatch sends no configured credentials and does
not expand environment variables. Keep real target configurations outside this
public repository; common local filenames are excluded by `.gitignore`.

Reports contain target names and URLs by default. Use `--redact-urls` when URLs
should not appear. Target names, status codes, timing, content types, sizes, and
fingerprints may also be sensitive, so review reports before sharing them.

## Baseline privacy

Baseline files contain target names, configured URLs, health states, statuses,
content types, and SHA-256 response fingerprints. They never contain response
bodies, durations, byte counts, final redirect URLs, or timestamps. Even without
a body, a fingerprint reveals equality between observations and may disclose
that content changed. Store baselines with the private configuration they
describe.

Comparison reports intentionally include changed field names rather than old
and new values. Use `--redact-urls` to omit configured URLs before sharing a
comparison. Target names and change patterns can still be sensitive. Redaction
does not make a report anonymous.

SiteWatch validates baselines without network access and never updates a trusted
baseline in place. Snapshot and report exports are created atomically and do not
replace existing files.

## Link-audit safety and privacy

Link audits default to the source page's origin and require explicit
`--include-external` permission before requesting external destinations. Both
source and destination URLs receive the same credential, local-address, public
DNS, timeout, and redirect protections as health checks. Discovery and checks
are bounded and sequential; link audits do not crawl recursively.

The bounded source HTML exists only long enough to extract links. It is not
stored in audit objects or reports. Destination response bodies are never read.
Reports contain URLs by default, along with statuses, timings, and error codes.
Use `--redact-urls` before sharing, while remembering that counts and status
patterns can still disclose information about a site.

Link checking sends network requests to every in-scope destination. This can
appear in server logs and may trigger rate limits or security controls. Keep
limits conservative, respect site policies, and run untrusted audits from an
appropriately restricted environment.

SiteWatch does not encrypt, upload, notify, schedule itself, or verify report
recipients.
