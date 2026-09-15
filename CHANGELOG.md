# Changelog

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
