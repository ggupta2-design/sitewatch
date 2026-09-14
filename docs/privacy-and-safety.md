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

SiteWatch does not encrypt, upload, notify, schedule itself, or verify report
recipients.
