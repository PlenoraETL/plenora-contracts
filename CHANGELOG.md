# Changelog

## Unreleased

### Fixed

- Erratum to `data.run` version 3, before any adoption or release used it:
  `rows_in` in `data-execution-result-v3.schema.json` is the list of the
  rows of each step input, as in the version 2 result (an integer could not
  describe a step with several inputs), and the success vector follows it;
  DT-RUN-006 allows `never`, `quarantine` or `requires_recovery` for an
  unproven publication outcome, as ERR-006 does. The schema is corrected in
  place because no artifact had adopted it; see
  [decision 0008](decisions/0008-data-run-runtime.md).
- Validator defect classes. A REST boundary example is matched by
  `(operation, version)` and must name its version (with one catalog version
  the version was ignored, so version 99 passed). A null `artifact_source` no
  longer counts as an upload source, a null forbidden artifact member is
  still forbidden (REST and storage), and a null attribute dropped by a later
  catalog is a change. Every JSON document is read rejecting repeated object
  keys. Two `data.run` 3 requests with one correlation id, two binding
  sections for one component and two REST capability entries for one
  identity are rejected instead of overwritten. Storage vector coverage and
  the data-tools catalog checks name the operation version. A null where an
  object is expected is a validation error instead of a crash. The REST
  boundary examples now state `version: 1`.

### Added

- `data.run` version 3 in `data-tools-v2.json`: the runtime representation of
  a `plenora-data-plan-v1` plan with named outputs, from artifact sources to
  artifact sinks, with a JSON manifest result. Conditional, Rust and runtime
  surfaces, `side_effect: remote`. New schemas
  `data-execution-input-v3.schema.json` and
  `data-execution-result-v3.schema.json`, profile rules DT-RUN-001 to
  DT-RUN-008, runtime selector `plenora.data-tools#data.run@3` and four
  runtime vectors. No existing operation, schema or vector changes. The
  validator checks every version of an operation and of its SDK bindings
  (it looked some up by identifier, letting one version hide another), and
  rejects runtime vectors that use an idempotency key the operation does
  not accept (RT-006, ERR-008). See
  [decision 0008](decisions/0008-data-run-runtime.md).

### Changed

- Replaced the runtime vector `database-transaction-commit-success.json`
  with `database-query-success.json`: the database-tools catalog selects the
  `database.transaction.*` operations only on the Rust and Python surfaces,
  and the runtime binding map has no transaction selector, so the vector
  exercised an operation the runtime does not carry. The runtime vector
  matrix no longer lists transaction references. The validator now rejects a
  runtime vector whose operation version does not select the runtime surface,
  for every component. No catalog, binding or schema changes.

- Published data-tools version 2 next to version 1: profile
  `plenora-data-tools-profile-v2` and catalog `data-tools-v2.json`, with
  `data.catalog`, `data.validate` and `data.run` at operation version 2 and
  new input and output contract identifiers; `data.run` declares `local`,
  returns named outputs and is not bound on the runtime surface; Python SDK
  is a conditional surface bound by `plenora-data` / `plenora_data`. New Data
  Plan 1.0 (`plenora-data-plan-v1`, `data-plan-v1.schema.json`) without plan
  hash; registry `data-kernels-v2.json` with the same 146 kernels at their
  semantic versions; Arrow rules for the version 2 operations in the profile
  (DT-ARROW-001 to DT-ARROW-004). Bindings, composition edges and runtime
  vectors add version 2 entries; every version 1 entry and file is
  unchanged. No existing schema changes. See
  [decision 0007](decisions/0007-data-tools-v2.md).

- Selected the storage Python SDK surface with canonical sync/async bindings
  for all seven v1 operations. Existing operation contracts and schema assertions
  are unchanged; adoption requires a new immutable pin and wheel evidence.
  See [decision 0006](decisions/0006-storage-python-surface.md).
- Removed implementation topology and obsolete development milestones from the
  storage profile. Added complete storage runtime request coverage and regression
  checks for artifact boundaries, explicit policies, integrity and unsafe retry.
- Added semantic conformance checks for capability identities and surfaces,
  adoption identities and deviation references, with counterexamples exercised
  in CI. Retained versioned JSON Schemas are unchanged.
- Made example registration exhaustive and added a CI guard against changes
  to published schema assertions, removals and duplicate schema identifiers.
- Documented the retained component-version grammar and a separate, unratified
  SemVer successor proposal.
- Corrected the IO-tools first conforming release from the `2.x` line to
  `4.0.0`. The `2.x` and `3.x` lines shipped without claiming the profile and
  are now listed as historical alongside `1.x`. No contract, schema or
  requirement identifier changes.
- Promoted the database-tools public profile and operation catalog from
  provisional to normative. Component release status and evidence remain in
  the component-owned adoption manifest.

### Added

- Public-surface contract and profiles for the five domain libraries.
- Operation-level capability discovery v2.
- Shared Arrow/GeoArrow interchange and row-diagnostics contracts.
- Runtime binding for serialized public operation invocation.
- Governance, compatibility and black-box adoption guidance.
- Common CLI protocol v2.
- Common Python SDK contract v1.
- Shared error, CLI envelope, capability and adoption-manifest schemas.
- Valid and invalid examples for the machine-readable contracts.
- Scope, stream-selection and cutover decisions.
- Machine-readable target catalogs for all five libraries and the exact 146-kernel data registry.
- Canonical CLI, Python SDK and runtime binding maps.
- Cross-component Arrow composition matrix.
- Closed Arrow metadata vocabulary with valid and invalid interoperability vectors.
- Runtime request, success and typed-error conformance vectors.
- Semantic validation across catalogs, bindings, composition and vectors.
- Plan Budget 1.0: `max_domain_memory_bytes`, plan format v6 and the plan
  identity boundary, with schema, examples and a semantic budget check.
