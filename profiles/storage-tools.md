# Public profile: storage-tools

Profile identifier: `plenora-storage-tools-profile-v1`

Status: provisional

Provisional empty catalog:
[`storage-tools-v1.json`](../catalogs/storage-tools-v1.json)

## Applicable contracts

- [Public Surfaces 1.0](../specs/surfaces/PUBLIC-SURFACES-1.0.md)
- [Capability Discovery 2.0](../specs/capabilities/CAPABILITY-DISCOVERY-2.0.md)
- [Typed Errors 1.0](../specs/errors/ERRORS-1.0.md)
- [Public Security 1.0](../specs/security/PUBLIC-SECURITY-1.0.md)
- [Arrow Interchange 1.0](../specs/data/ARROW-INTERCHANGE-1.0.md), when advertised
- [CLI 2.0](../specs/cli/CLI-2.0.md), when exposed
- [Python SDK 1.0](../specs/sdk/PYTHON-SDK-1.0.md), when exposed
- [Runtime Binding 1.0](../specs/runtime/RUNTIME-BINDING-1.0.md), when exposed

## Current contract boundary

No stable storage operation catalog is defined yet. This profile deliberately
does not invent get, put, list, delete, copy, multipart or provider semantics.

Before the first public release, storage-tools MUST publish:

- its stable component identifier;
- the public surfaces included in the artifact;
- stable operation identifiers and versions;
- versioned input and output contract identifiers;
- content types and artifact-reference semantics;
- side-effect classification;
- deadline, cancellation and idempotency-key support;
- typed error and ambiguous-outcome behavior;
- Capability Discovery 2.0 output.

## Reserved namespace

Public storage operations use the `storage.*` namespace. The existence of the
namespace does not reserve or standardize any particular action.

## Interchange

Storage operations that accept or return tabular Arrow data follow Arrow
Interchange 1.0. Operations that expose opaque objects preserve declared content
type and integrity metadata.

The representation of storage locations, credentials, object versions and
atomic publication requires a separate reviewed public specification before
stable release.

## Public surfaces

Rust, CLI, Python SDK and runtime applicability are currently undecided. Once a
surface is published, it follows the corresponding common contract and appears
truthfully in capability discovery.

## Not specified here

This profile does not select providers, clients, consistency mechanisms,
multipart strategies, caches or credential implementations.
