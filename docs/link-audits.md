# Bounded broken-link audits

SiteWatch can discover and check links from one public HTML page without keeping
the page or destination bodies.

## Audit same-origin links

```bash
sitewatch links https://example.com/docs/ \
  --max-links 50 \
  --max-page-bytes 1000000 \
  --timeout-seconds 10
```

Same-origin scope is the default. Relative links are resolved against the final
source-page URL, fragments are removed, duplicate destinations are checked once,
and links are checked sequentially in document order.

The source must return `text/html`. SiteWatch temporarily reads no more than
`max-page-bytes` for link extraction and discards that content after parsing.
Destination checks inspect response metadata without reading response bodies.

## Include external destinations

```bash
sitewatch links https://example.com/docs/ \
  --include-external \
  --max-links 100
```

External links are skipped unless explicitly enabled. Every discovered HTTP or
HTTPS destination still receives URL validation, public DNS validation, timeout
protection, and safe redirect validation. Mail, telephone, script, data, local,
credential-bearing, and other unsupported destinations are not requested.

The maximum link limit applies to unique, in-scope destinations. Reports state
when discovery was truncated so a partial audit cannot be mistaken for a full
site review.

## Redact and export

```bash
sitewatch links https://example.com/docs/ \
  --json \
  --redact-urls \
  --output ~/private/reports/links.json
```

Redaction removes source, destination, and final URLs. It retains aggregate
counts, health states, status codes, durations, and stable error codes. Exports
are atomic and cannot replace existing files.

Exit status 0 means at least one link was checked and every checked destination
was healthy. Status 1 means the source failed, no links were checked, or a link
was broken or could not be checked. Status 2 means an option, URL, or output
request was invalid.

## Scope and interpretation

This command audits one HTML page; it does not crawl linked pages recursively.
HTTP statuses from 200 through 399 are healthy. Other statuses are broken.
Network, timeout, and unsafe-destination failures are errors.

A successful run does not prove that a page is semantically correct or that a
link will work for every user. Authentication, geography, rate limits, bot
policies, and transient network conditions can affect results.
