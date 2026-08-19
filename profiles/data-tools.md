# Public profile: data-tools

Profile identifier: `plenora-data-tools-profile-v1`

## Applicable contracts

- [Public Surfaces 1.0](../specs/surfaces/PUBLIC-SURFACES-1.0.md)
- [Capability Discovery 2.0](../specs/capabilities/CAPABILITY-DISCOVERY-2.0.md)
- [Typed Errors 1.0](../specs/errors/ERRORS-1.0.md)
- [Public Security 1.0](../specs/security/PUBLIC-SECURITY-1.0.md)
- [Arrow Interchange 1.0](../specs/data/ARROW-INTERCHANGE-1.0.md)
- [Row Diagnostics 1.0](../specs/diagnostics/ROW-DIAGNOSTICS-1.0.md)
- [CLI 2.0](../specs/cli/CLI-2.0.md)
- [Runtime Binding 1.0](../specs/runtime/RUNTIME-BINDING-1.0.md), when exposed

## Public purpose

The component exposes versioned table and geospatial transformations over
declared tabular contracts.

## Required operation families

Every operation in the released public transformation catalog MUST retain its
stable identifier and appear in Capability Discovery 2.0. The catalog may use
domain namespaces such as `table.*` and `geo.*`.

The public surface MUST also make these functions discoverable:

- catalog inspection;
- plan validation or explanation when plans are accepted publicly;
- transformation execution;
- required backend capability selection.

Catalog attributes expose externally relevant operation properties such as
input arity, result shape, determinism, required backend and CRS requirement.
They do not expose executor internals.

## Public surfaces

- Rust API: required.
- CLI: required and governed by CLI 2.0.
- Python SDK: not required by this profile.
- Runtime: required for every transformation selected for orchestration.

## Interchange

Tabular and geospatial operations accept and return Arrow according to Arrow
Interchange 1.0. Operation-specific contracts define logical columns and
operation parameters.

Row-scoped validation or mapping failures use
`plenora-row-diagnostics-v1` when diagnostics are advertised.

## External behavior

Unavailable backends, unsupported CRS states and incompatible schemas fail
closed with typed errors. A catalog entry MUST NOT claim availability when the
released artifact lacks a required backend.

## Not specified here

This profile does not prescribe DAG representation, kernel implementation,
fusion, scheduling, memory accounting or cancellation-token design.
