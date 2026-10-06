# 0007: Data-tools version 2: plan format, kernel versions and Python surface

Status: accepted

Date: 2026-10-03

## Context

Data Tools was rebuilt as a lighter successor of the release that profile
version 1 described. The new artifact (CLI `plenora-data`, crate
`plenora-cli`, Python SDK `plenora-data`) adopted the contracts at revision
`ade868cf89c6652cffe20019e7194b383384ee78` and recorded every difference as
an adoption deviation instead of editing the contracts piecemeal:

- it accepts one plan format, `"version": 1` with single-assignment steps,
  and rejects plan formats `4`, `5` and `6`; it publishes no plan hash;
- it reports each kernel at its semantic version (from 1 to 6), while
  `data-kernels-v1` declares version `1` for all 146 kernels;
- `data.run` writes its outputs to local files on the CLI, so it advertises
  `side_effect: local` where the catalog says `none`;
- a plan may name several outputs, which `run` takes as `--output NAME=PATH`;
- it ships a Python SDK, while the v1 catalog selects Python as
  `not_applicable`;
- it reads and writes Parquet as a declared extension content type;
- its Arrow boundary resolves cases the vocabulary leaves open: field
  identity in collisions and row concatenation, geometry fields that omit
  vocabulary keys, and spatial semantics or axis orders a kernel cannot
  compute with.

No consumer depends on plan formats `4` to `6` or on a persisted plan hash of
this component.

## Decision

Publish data-tools version 2 next to version 1, as COMPATIBILITY.md requires
for incompatible changes:

- [Data Plan 1.0](../specs/data/DATA-PLAN-1.0.md) (`plenora-data-plan-v1`)
  and its schema define the plan format, without identity or migration;
- [`data-kernels-v2.json`](../catalogs/data-kernels-v2.json)
  (`plenora-data-kernel-catalog-v2`) lists the same 146 kernels at their
  semantic versions;
- [`data-tools-v2.json`](../catalogs/data-tools-v2.json) with profile
  [`plenora-data-tools-profile-v2`](../profiles/data-tools-v2.md):
  `data.catalog` 2 (result `plenora-data-catalog-result-v2`: the registry
  the artifact implements plus a descriptor with status for every kernel,
  DT-001), `data.validate` 2 and `data.run` 2 (plan format above; `data.run`
  declares `local` and returns named outputs), `data.describe` stays at
  version 1; Python SDK is a conditional target surface for all four
  operations;
- `data.run` 2 is not bound on the runtime surface: Runtime Binding 1.0
  carries one payload per response and the result names several outputs, so
  a runtime binding would accept fewer plans than the other surfaces.
  Orchestrated execution keeps `data.run` 1;
- the CLI, Python and runtime binding maps, the composition edges and the
  runtime vectors **add** the version 2 entries next to the version 1 ones,
  which stay unchanged: `run --output NAME=OUTPUT.arrow`, the
  `plenora-data` / `plenora_data` SDK, runtime selectors `@2` for catalog and
  validate, composition edges for `data.run` 2, a `data.validate` 2 request
  vector;
- the Arrow cases the shared contracts leave to each operation are decided
  for the version 2 operations in the profile (DT-ARROW-001 to
  DT-ARROW-004): identity in collisions and row concatenation, with explicit
  precedence, geometry fields that omit vocabulary keys, and spatial
  semantics, edges and axis orders a planar kernel cannot compute with.

Version 1 stays available and unchanged: its catalog, registry, profile,
bindings, composition edges, vectors and Plan Budget 1.0 keep their meaning,
and an artifact that adopts it at this revision finds every expectation it
had. The validator checks every catalog version, each against its own
expectations, and binds each binding, edge and vector to the catalog version
that declares its operation.

## Alternatives

- **Edit version 1 in place.** Fewer files, but it changes accepted input,
  side-effect classification and kernel versions under the same identities,
  which COMPATIBILITY.md forbids.
- **Keep the differences as permanent deviations.** The contracts would keep
  describing an artifact that no longer exists.
- **Arrow rules in Arrow Interchange 1.0.** They would add obligations to
  every component selecting that contract (io-tools, database-tools) under an
  unchanged identity; they belong to the operations that need them.
- **Bind `data.run` 2 on the runtime with a one-output restriction.** The
  same operation version would validate differently across surfaces, which
  Public Catalogs 1.0 forbids.
- **A semantics-version field in the registry.** It needs a new registry
  schema; the existing integer `version` already is the semantic identity
  (PUBLIC-CATALOGS-1.0, section 3).

## Change statement

- **Consumers affected:** callers of `data.catalog`, `data.validate` and
  `data.run`; runtime adopters of the data selectors; composition users of
  `data.run`.
- **Before:** plans in formats `4` to `6` with a plan hash, every kernel at
  version `1`, `data.run` without side effect and with one output, no Python
  surface.
- **After:** version 2 operations take `plenora-data-plan-v1`, report kernels
  at their semantic versions, declare `local` and name their outputs; Python
  is selectable.
- **Compatibility:** incompatible for the three operations, hence new
  operation versions and contract identifiers; compatible for the added
  surface. The Arrow rules bind only the version 2 operations; other
  components and data-tools version 1 are unaffected.
- **Schemas:** new `data-plan-v1.schema.json`; no existing schema changes.
- **Examples and vectors:** new valid and invalid plan examples, among them
  raw-text number counterexamples; a new `data.validate` 2 runtime vector; the
  version 1 vectors are unchanged.
- **Adoption:** Data Tools adopts version 2 at the revision that merges this
  decision; its deviations for the plan format, kernel versions, side effect,
  multiple outputs, Parquet and the Python surface close. Bounded
  materialization stays declared by attribute (ARROW-011).

## Consequences

Plan Budget 1.0 governs only profile version 1. A future isolated execution
profile for data-tools would extend Data Plan 1.0 with a new format version,
not reuse plan format `6`.
