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

Format identifiers are typed operation inputs and entries in the versioned
`io.catalog` result. Format-specific behavior MUST NOT be selected by parsing
file extensions when the operation requires an explicit format.

## Component-owned wire contracts

Before an artifact claims this profile, IO-tools MUST publish immutable schemas
and conformance examples for all six operation pairs named by the target
catalog:

- `plenora-io-catalog-query-v1` and `plenora-io-catalog-v1`;
- `plenora-io-inspect-input-v1` and `plenora-io-inspect-v1`;
- `plenora-io-layers-input-v1` and `plenora-io-layers-v1`;
- `plenora-io-read-input-v1` and `plenora-io-read-result-v1`;
- `plenora-io-write-input-v1` and `plenora-io-write-result-v1`;
- `plenora-io-convert-input-v1` and `plenora-io-convert-v1`.

These schemas remain owned by IO-tools. The shared repository fixes their
public identifiers, roles and cross-component meaning, not their internal
implementation.

When an IO error includes `details`, the value MUST conform to the
component-owned `plenora-io-error-details-v1` schema. IO-tools MUST publish that
schema and bounded valid and invalid examples. Omitting `details` remains valid
when the four common error axes and optional `code` completely express the
failure.

## Public surfaces

- Rust API: required.
- CLI: required and governed by CLI 2.0.
- Python SDK: not required by this profile.
- Runtime: required for every I/O operation selected for orchestration.

## Interchange

`io.read` exposes tabular output through Arrow Interchange 1.0 when Arrow is
the declared representation. `io.write` and `io.convert` declare accepted
input and produced output content types.

The versioned `plenora-io-catalog-v1` result is the sole normative source for
format identifiers, accepted options, read/write availability, layer behavior,
geometry and CRS support, fidelity constraints and publish guarantees.
Capability `attributes` MUST NOT duplicate this matrix. Capability discovery
describes whether `io.catalog` exists and how to invoke it.

Loss, coercion or unsupported metadata that changes the public result MUST be
reported through a structured fidelity result or typed failure; it MUST NOT be
silent.

Row-scoped format or mapping failures use
`plenora-row-diagnostics-v1` when diagnostics are advertised.

## External outcomes

Write and convert operations declare local or remote side effects and distinguish
complete publication, rollback, partial publication and unknown durability where
those states are observable.

## First conforming release and cutover

The first release claiming this profile is IO-tools `2.0.0` or a later `2.x`
release. It is a breaking component release.

CLI protocol v1 and v2 JSON MUST NOT coexist in the same artifact. In the
conforming release, every `--format json` response uses CLI protocol v2.
Historical command spellings MAY remain only as deprecated aliases declared in
the surface bindings; an alias invokes the same operation and emits the same v2
contract. Consumers MUST NOT receive an automatic fallback to the former error
stream or exit-code mapping. The existing `1.x` line remains historical and
does not claim this profile.

## Not specified here

This profile does not prescribe drivers, parsers, temporary files, spooling,
batch size, GDAL integration or publish algorithms.
