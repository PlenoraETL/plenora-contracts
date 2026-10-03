# Changelog

## Unreleased

### Changed

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
