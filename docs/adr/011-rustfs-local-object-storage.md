# ADR-011: Use RustFS for local S3-compatible object storage

Status: Accepted with conditions (tech lead review, 8 Nov 2026). Final acceptance requires the
integration test in "Conditions" to pass.

## Context

The Architecture Specification named MinIO as the local object store. MinIO stopped publishing
community container images in October 2025 and its repository has since been archived, so the
pinned image can no longer be pulled. AITMS needs S3-compatible storage for signed uploads,
artifact persistence and downloads.

## Decision

- Use RustFS (`rustfs/rustfs`, pinned version) as the default local object store in Docker Compose.
- Application code speaks only the standard S3 API. No RustFS-specific SDK or API is used.
- Cloud environments keep using a managed S3-compatible service. This ADR does not choose
  production storage.

## Conditions

1. Configuration contract unchanged: `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`.
2. Persistent named volume (`s3data`). A named volume avoids the ownership problems a bind mount
   would cause, because the RustFS container runs as a non-root user.
3. Credentials come only from the environment. Compose has no fallback credentials, so it refuses to
   start without them. Values in `.env.example` are placeholders for isolated local use only.
4. A storage health check gates dependent services.
5. An integration test, run in CI against the Compose service, must cover every operation AITMS uses:
   bucket creation, presigned POST upload (including its size, empty-file, content-type and key
   restrictions), download, delete, and an unchanged SHA-256 and metadata after a round trip.
   Downloads are streamed through the API by design (permission and RLS checks on every download),
   so AITMS issues no presigned download URLs. Test: `apps/api/tests/integration/test_s3_storage.py`,
   run with `scripts/dev.ps1 test-integration`.
6. The local setup is documented in the README.

## Consequences

Positive: no dependency on the discontinued MinIO images; the same S3 integration locally and in the cloud.

Trade-offs: RustFS is a different implementation, so S3 compatibility is verified per operation
(condition 5). Single-node, single-disk local storage is not a high-availability configuration.
