# Changelog

## 0.6.0 — 2026-09-20

- Added strict, named, schema-versioned reliability policies.
- Added bounded thresholds for availability, incidents, gaps, and errors.
- Added local-only policy validation without DNS or HTTP requests.
- Evaluated minimum availability using the least-reliable target.
- Added stable checks for open incidents, monitoring gaps, and error samples.
- Added deterministic notification-ready alert decisions and finding codes.
- Added readable and JSON reports containing aggregate evidence only.
- Omitted target names, URLs, timestamps, statuses, error details, and bodies.
- Added atomic non-overwriting decision report exports.
- Added automation-friendly clear, alert, and invalid exit statuses.
- Added a conservative public policy example and private-file exclusions.
- Added tests for schemas, evaluation, privacy, CLI, exports, and status codes.
- Documented policy workflows, evidence limits, and notification boundaries.

## 0.5.0 — 2026-09-19

- Added read-only incident timelines from bounded availability histories.
- Grouped consecutive unhealthy and error observations by stable target name.
- Recorded recovery only when a later healthy observation is present.
- Distinguished recovered incidents from incidents still open in the history.
- Added affected, unhealthy, error, latency, and observed-span metrics.
- Added per-target monitoring-gap detection with a strict configurable bound.
- Added readable and JSON reports without URLs, statuses, or error-code values.
- Added local-only incident analysis that never performs network requests.
- Added default and strict automation exit policies for incident reviews.
- Added atomic non-overwriting exports for incident analysis reports.
- Added tests for recovery boundaries, gaps, privacy, CLI, and exit statuses.
- Documented evidence limits, operational privacy, and safe interpretation.

## 0.4.0 — 2026-09-17

- Added strict, versioned availability histories capped at 10,000 samples.
- Added URL-free samples containing state, status, duration, time, and error code.
- Added immutable append workflows that always create a new history file.
- Added chronological and duplicate-sample safeguards for history extensions.
- Added local history validation that performs no network requests.
- Added per-target healthy, unhealthy, error, and availability metrics.
- Added average and maximum latency plus recorded observation windows.
- Added configurable availability goals with automation-friendly exit statuses.
- Added readable and JSON summaries without URLs, fingerprints, or bodies.
- Added atomic non-overwriting exports for histories and reliability reports.
- Added tests for schemas, privacy, appends, metrics, goals, reports, and CLI.
- Documented retention, privacy, and non-contractual interpretation boundaries.

## 0.3.0 — 2026-09-16

- Added bounded link discovery for one public HTML source page.
- Added same-origin auditing by default with explicit external-link opt in.
- Added relative-link resolution, fragment removal, and destination deduplication.
- Added explicit source-byte, link-count, and request-timeout limits.
- Added public URL, DNS, and redirect validation for every destination.
- Added sequential destination checks that never read response bodies.
- Added healthy, broken, and stable transport-error classifications.
- Added readable and JSON link reports with full URL redaction.
- Added atomic non-overwriting link report exports and automation exit statuses.
- Added tests for discovery, limits, transport, privacy, reporting, and CLI flows.
- Documented network side effects, scope limits, and interpretation boundaries.

## 0.2.0 — 2026-09-15

- Added strict, versioned baseline snapshots with bounded unique targets.
- Added deterministic baseline serialization and local-only validation.
- Added body-free snapshots containing stable health metadata and fingerprints.
- Added value-free comparisons for changed, new, missing, and unchanged targets.
- Excluded volatile duration, byte-count, and timestamp data from drift checks.
- Added readable and JSON drift reports with optional URL redaction.
- Added non-overwriting baseline creation and comparison report exports.
- Added automation-friendly exit statuses for unhealthy or changed sites.
- Added tests for schema validation, comparisons, privacy, CLI, and exports.
- Documented baseline retention, disclosure boundaries, and reviewed updates.

## 0.1.0 — 2026-09-14

- Added strict, versioned monitoring configurations with bounded target counts.
- Added HTTP and HTTPS URL validation with credential and local-address rejection.
- Added DNS resolution checks that reject non-public destinations.
- Added optional redirect handling with destination revalidation.
- Added bounded timeouts and response reads with SHA-256 fingerprints.
- Added deterministic status, content-type, redirect, and transport findings.
- Added readable and JSON health reports with optional URL redaction.
- Added configuration validation that performs no network activity.
- Added atomic report exports that never overwrite existing files.
- Added automation-friendly healthy, unhealthy, and invalid exit statuses.
- Added unit and CLI tests across Python 3.10 through 3.13.
- Added public examples, workflow documentation, and security boundaries.
