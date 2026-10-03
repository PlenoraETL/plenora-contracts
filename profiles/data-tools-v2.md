# Public profile: data-tools, version 2

Profile identifier: `plenora-data-tools-profile-v2`

Normative target catalog:
[`data-tools-v2.json`](../catalogs/data-tools-v2.json), with the exact
[`data kernel registry v2`](../catalogs/data-kernels-v2.json).

It supersedes [profile version 1](data-tools.md) as the current target
([decision 0007](../decisions/0007-data-tools-v2.md)). Version 1 remains an
available identity: its catalog, registry and plan formats keep their meaning.

## Applicable contracts

- [Public Surfaces 1.0](../specs/surfaces/PUBLIC-SURFACES-1.0.md)
- [Capability Discovery 2.0](../specs/capabilities/CAPABILITY-DISCOVERY-2.0.md)
- [Typed Errors 1.0](../specs/errors/ERRORS-1.0.md)
- [Public Security 1.0](../specs/security/PUBLIC-SECURITY-1.0.md)
- [Arrow Interchange 1.0](../specs/data/ARROW-INTERCHANGE-1.0.md)
- [Data Plan 1.0](../specs/data/DATA-PLAN-1.0.md)
- [Row Diagnostics 1.0](../specs/diagnostics/ROW-DIAGNOSTICS-1.0.md)
- [CLI 2.0](../specs/cli/CLI-2.0.md)
- [Python SDK 1.0](../specs/sdk/PYTHON-SDK-1.0.md), when exposed
- [Runtime Binding 1.0](../specs/runtime/RUNTIME-BINDING-1.0.md), when exposed
- [Surface Bindings 1.0](../specs/surfaces/SURFACE-BINDINGS-1.0.md)
- [Composition 1.0](../specs/composition/COMPOSITION-1.0.md)

[Plan Budget 1.0](../specs/data/PLAN-BUDGET-1.0.md) does not apply to this
profile: its plan formats `4`, `5` and `6` belong to profile version 1.

## Public purpose

The component exposes versioned table and geospatial transformations over
declared tabular contracts.

## Required operation families

Every kernel in the registry MUST retain its stable identifier. Its `version`
is the version of its observable semantics: a change of output, defaults,
accepted configuration or error axes raises it.

**DT-001** — The result of `data.catalog` version 2
(`plenora-data-catalog-result-v2`) is a JSON object with:

- `registry`: the kernel registry the artifact implements, as
  [`data-kernels-v2.json`](../catalogs/data-kernels-v2.json) shapes it
  (`plenora-operation-registry-v1`), listing every kernel the artifact can
  execute at the registry's `id` and `version`;
- `kernels`: one component-owned descriptor per registered kernel, with at
  least `id`, `version` (equal to the registry's), `family` and `status`
  (`available` or `unavailable`); an `unavailable` kernel carries a `reason`
  and is absent from `registry`;
- `plan_format`: `plenora-data-plan-v1`.

A kernel the artifact cannot execute is never reported available, and a plan
using it fails with `unsupported` (DPLAN-006). Kernel status is distinct from
the status of the `data.catalog` operation in Capability Discovery 2.0.

The public surface MUST also make these functions discoverable:

- catalog inspection;
- plan validation;
- transformation execution.

Catalog attributes expose externally relevant operation properties such as
input arity, result shape, determinism, required backend and CRS requirement.
They do not expose executor internals.

## Public surfaces

- Rust API: required.
- CLI: required and governed by CLI 2.0.
- Python SDK: optional; when published it is governed by Python SDK 1.0 and
  binds all four operations in both API modes.
- Runtime: conditional. `data.catalog` version 2, `data.describe` version 1
  and `data.validate` version 2 list it. `data.run` version 2 does not: its result names any
  number of outputs, and Runtime Binding 1.0 carries one payload per
  response. Orchestrated execution uses `data.run` version 1 until a later
  `data.run` version defines a named-output runtime representation.

## Interchange

Tabular and geospatial operations accept and return Arrow according to Arrow
Interchange 1.0. Operation-specific contracts define logical columns and
operation parameters.

Parquet is an extension content type declared in the operation attributes
(`extension_content_types`), outside the Arrow interchange contract: a
consumer that does not recognize it MUST NOT send it.

`describe`, `validate` and `run` declare `bounded_materialization`: tables are
materialized within the plan memory budget (ARROW-011).

Row-scoped validation or mapping failures use
`plenora-row-diagnostics-v1` when diagnostics are advertised.

## Arrow boundary of version 2 operations

These rules bind the version 2 operations of this profile. They decide cases
Arrow Interchange 1.0 and the vocabulary leave to the operation contract; they
do not change those contracts for other components.

**DT-ARROW-001** — Within one output schema no identifier appears on two
fields, and identifiers declared by different plan inputs are independent:
the same number may name different fields. A field whose identifier is
carried by another field of the output (a duplicated column, a self-join), or
is declared by more than one plan input, receives a new identifier, as a newly
derived field; the component MUST NOT keep the identifier on one of those
fields by choice. The consumer loses that field's identity and never finds
another field under it.

**DT-ARROW-002** — An operation that concatenates the rows of several inputs
into one output field (`table.concat`, `table.concat_by_name`,
`table.union_distinct`) takes that field's metadata, identifier included,
from the corresponding field of the first input. DT-ARROW-001 then applies
to the published output: when the inputs declare the same identifier for the
concatenated column, the published field receives a new identifier.

**DT-ARROW-003** — An input schema whose `geoarrow.wkb` field omits
vocabulary keys that producers MUST declare is accepted, and each missing key
is read without asserting more than the field carries: `encoding` as the
extension name reads (`wkb`), `dimensions` `unknown`, `types_declaration`
`unresolved`, `spatial_semantics` `geometry` (the GeoArrow default),
`precision` `float64` (the WKB coordinate width), and the CRS state from the
CRS representations present (`missing` when there are none). Contradictory
keys still fail (ARROW-006), and every output geometry field declares every
key.

**DT-ARROW-004** — A geometry operation rejects, before computing, a field
whose `spatial_semantics` is `geography` or whose GeoArrow extension metadata
declares non-planar `edges` (category `unsupported`), and a field whose
`axis_order` puts north first (`lat_lon`, `northing_easting`; category
`crs`). An operation that only passes the field through carries it unchanged
(ARROW-008).

## Outputs and side effects

`data.run` returns the outputs a plan names, in the order it names them
(`plenora-data-execution-result-v2`). A surface that takes output paths
writes each output to its local file, which `side_effect: local` declares; a
surface that returns the tables in memory writes nothing outside the process.

Every surface of `data.run` version 2 names each output (CLI
`--output NAME=OUTPUT.arrow`, Rust and Python mappings), so each accepts any
number of outputs; on the CLI the unnamed `--output OUTPUT.arrow` is accepted
for a plan with exactly one output.

## External behavior

Unavailable kernels, unsupported CRS states and incompatible schemas fail
closed with typed errors. A catalog entry MUST NOT claim availability when the
released artifact cannot execute it.

## Plan identity

[Data Plan 1.0](../specs/data/DATA-PLAN-1.0.md) defines no plan hash and no
canonical form (DPLAN-012), and no migration from plan formats `4`, `5` or `6`
(DPLAN-013).

## Not specified here

This profile does not prescribe kernel implementation, scheduling, memory
accounting or cancellation-token design.
