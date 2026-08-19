# Public profile: io-tools

Profile identifier: `plenora-io-tools-profile-v1`

Normative target catalog: [`io-tools-v1.json`](../catalogs/io-tools-v1.json)

## Applicable contracts

- [Public Surfaces 1.0](../specs/surfaces/PUBLIC-SURFACES-1.0.md)
- [Capability Discovery 2.0](../specs/capabilities/CAPABILITY-DISCOVERY-2.0.md)
- [Typed Errors 1.0](../specs/errors/ERRORS-1.0.md)
- [Public Security 1.0](../specs/security/PUBLIC-SECURITY-1.0.md)
- [Arrow Interchange 1.0](../specs/data/ARROW-INTERCHANGE-1.0.md)
- [Row Diagnostics 1.0](../specs/diagnostics/ROW-DIAGNOSTICS-1.0.md)
- [CLI 2.0](../specs/cli/CLI-2.0.md)
- [Runtime Binding 1.0](../specs/runtime/RUNTIME-BINDING-1.0.md), when exposed
- [Surface Bindings 1.0](../specs/surfaces/SURFACE-BINDINGS-1.0.md)
- [Composition 1.0](../specs/composition/COMPOSITION-1.0.md)

## Public purpose

The component exposes discovery, inspection, reading, writing and conversion of
external datasets through format-aware public contracts.

## Required operation families

The stable public catalog includes:

- `io.catalog`;
- `io.inspect`;
- `io.layers`;
- `io.read`;
- `io.write`;
- `io.convert`.

A released artifact MAY omit an operation that is not part of that artifact,
but MUST NOT advertise it as available.

Format identifiers are typed inputs or capability attributes. Format-specific
behavior MUST NOT be selected by parsing file extensions when the operation
requires an explicit format.

## Public surfaces

- Rust API: required.
- CLI: required and governed by CLI 2.0.
- Python SDK: not required by this profile.
- Runtime: required for every I/O operation selected for orchestration.

## Interchange

`io.read` exposes tabular output through Arrow Interchange 1.0 when Arrow is
the declared representation. `io.write` and `io.convert` declare accepted
input and produced output content types.

Capability attributes expose externally relevant format behavior: read/write
availability, layer behavior, geometry and CRS support, fidelity constraints
and publish guarantees.

Loss, coercion or unsupported metadata that changes the public result MUST be
reported through a structured fidelity result or typed failure; it MUST NOT be
silent.

Row-scoped format or mapping failures use
`plenora-row-diagnostics-v1` when diagnostics are advertised.

## External outcomes

Write and convert operations declare local or remote side effects and distinguish
complete publication, rollback, partial publication and unknown durability where
those states are observable.

## Not specified here

This profile does not prescribe drivers, parsers, temporary files, spooling,
batch size, GDAL integration or publish algorithms.
