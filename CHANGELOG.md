# Changelog

## Unreleased

### Changed

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
