# Public profile: storage-tools

Profile identifier: `plenora-storage-tools-profile-v1`

Status: normative

Normative operation catalog:
[`storage-tools-v1.json`](../catalogs/storage-tools-v1.json)

## Applicable contracts

- [Public Surfaces 1.0](../specs/surfaces/PUBLIC-SURFACES-1.0.md)
- [Capability Discovery 2.0](../specs/capabilities/CAPABILITY-DISCOVERY-2.0.md)
- [Typed Errors 1.0](../specs/errors/ERRORS-1.0.md)
- [Public Security 1.0](../specs/security/PUBLIC-SECURITY-1.0.md)
- [CLI 2.0](../specs/cli/CLI-2.0.md)
- [Runtime Binding 1.0](../specs/runtime/RUNTIME-BINDING-1.0.md)

## Current contract boundary

The v1 profile selects seven operations: `storage.test`, `storage.list`,
`storage.stat`, `storage.get`, `storage.put`, `storage.copy` and
`storage.delete`. Every operation uses immutable component-owned JSON input
and output identifiers, operation version 1, cancellation and deadline. No v1
operation accepts an idempotency key.

This normative selection is not an artifact conformance claim. Capability
records emitted by unreleased storage artifacts remain `experimental` until a
qualified release exists.

## Operation semantics

`test`, `list` and `stat` declare `side_effect: none`. `put`, `copy` and
`delete` declare `remote`. `get` also uses the conservative `remote` class:
the storage read is non-mutating, but its authorized artifact sink may be
externally visible.

`get` and `put` carry no bytes inside the JSON envelope. Runtime requests use
opaque `artifact://` references; a consumer-owned adapter resolves them into
a sink or source through application-owned resolver traits. Source, sink and
transfer result carry bounded metadata for content type, size and optional
SHA-256. Persisted runtime envelopes contain neither local paths nor inline
credentials. Every destination requires an explicit `overwrite` value, put
and copy require an explicit `publication_policy`, and delete requires an
explicit missing-object policy.

`overwrite=false` is permitted only when the provider guarantees atomic
create-if-absent for that specific operation; put and copy support are
advertised separately. Otherwise it is rejected before mutation. S3 uses a
qualified native conditional primitive for put and rejects conditional copy
when that primitive is unavailable. SFTP can publish through temporary-name plus
rename when the connection qualifies that primitive. FTP does not advertise
atomic create-if-absent, rejects `overwrite=false`, documents non-atomic
publication and rejects `atomic_required`. There is no check-then-write
fallback.

Timeout and cancellation are cooperative and do not prove rollback. If a
write, copy, delete or artifact publication may have started, an unproven
outcome reports `remote_effect: unknown` with conservative retry or recovery.
A definitely partial sink may report `partial` and still forbids automatic
retry.

## Public surfaces

Rust, CLI and runtime are selected. Python SDK is not required for v1. The
component-owned Rust binding maps each operation to `Engine`; the common CLI
and runtime maps define the other entrypoints. Capability Discovery reports
only the surface of the answering artifact and only providers and operations
that are actually present. Experimental operations require explicit opt-in.

The runtime adapter belongs to the final consumer. Core `runtime-tools` crates
do not depend on the storage library, and storage core does not depend on a
runtime handler implementation. The transport-neutral binding validates the
route and security boundary, resolves artifacts and secret authority, invokes
the Engine with deadline/cancellation, and returns a complete versioned result
or `plenora-error-v1` while preserving correlation and contract identity.

## Pagination and integrity

The `storage.list` cursor is opaque, bounded to 512 bytes and scoped to
provider, connection, prefix and request parameters. Reuse under another scope
fails closed. The reference implementation keeps at most 1024 process-local
cursors for 15 minutes; expiration, eviction, close or restart invalidates a
cursor. Pagination does not provide snapshot isolation during concurrent
mutations.

ETag, provider version ID and SHA-256 remain distinct optional fields. Neither
ETag nor version is defined as a digest, missing values are not synthesized,
and end-to-end integrity is asserted only through the separate SHA-256 field
when it was actually calculated.

## Interchange and composition

The JSON contracts describe control and result metadata, not the transferred
object's semantic content. Therefore no direct composition edge is declared
from an artifact reference alone. An edge may be added only after producer and
consumer share a reviewed contract for the transferred content. No storage
composition edge is selected by this profile.

## Provider-independent decisions

- Rust and CLI are required.
- Runtime Binding 1.0 is required for all seven operations.
- Python SDK is not required.
- Idempotency keys are unsupported in v1.
- Timeout or cancellation after mutation begins does not imply rollback and
  reports `remote_effect: unknown` with `retry: requires_recovery` when the
  provider cannot prove the result.

The profile does not select providers, clients, multipart strategies, caches
or credential implementations. Manifest v4, artifact digests and a qualified
release are point 30 work and are outside this profile ratification.
