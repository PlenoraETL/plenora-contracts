# Changelog

The repository versions are described in
[COMPATIBILITY.md](COMPATIBILITY.md#repository-releases). Components pin the
full commit SHA; a release tag names one of those commits.

## Unreleased

### Added

- Arrow Geometry Semantics 1.0 (`plenora-arrow-geometry-semantics-v1`), an
  opt-in contract next to Arrow Vocabulary 1.0 that changes neither keys,
  values nor `plenora.contract.version` (GEO-000 to GEO-018): input
  conformance, component support and operation applicability are distinct
  verdicts; `axis_order` is the stored order, declared by the producer;
  `crs_id` is normative, a contradictory top-level identifier is `crs`, and a
  component verifies a definition before computing with one conservative
  subset (exact decimals, two spellings of the degree, closed aliases, units
  by quantity, datum and conversion); both `wkb` and `ewkb` are accepted;
  several types and geometry fields are valid; identity and precision of
  produced fields. Arrow Vocabulary 1.0 keeps its published text, with an
  informative pointer. New schema `arrow-data-vector-v1` and 42 vectors in
  `vectors/arrow-data-v1`. No existing schema, catalog, binding or vector
  changes. See
  [decision 0013](decisions/0013-geometry-vocabulary-semantics.md).
- ERR-016 (Typed Errors 1.0, a clarification): an unknown outcome does not
  decide the category; a lost commit confirmation is `io`, an elapsed
  deadline `timeout`, `internal` only a defect of the component, always with
  `remote_effect: unknown` and normally `requires_recovery`. New runtime
  vector `database-write-commit-io-error.json`; Runtime Vectors 1.0 states
  the scope of the published `database-write-error.json`, unchanged. See
  [decision 0019](decisions/0019-category-of-an-unknown-commit-outcome.md).

### Changed

- The validation gates use `jsonschema` 4.26.0 (was 4.23.0). The lock stays
  universal from Python 3.10: `rpds-py` keeps 0.30.0, its last release for
  Python 3.10, under `python_full_version < '3.11'` and 2026.9.1 above; the
  other transitive dependencies are unchanged. Every schema check and every
  validation of the schemas, examples and vectors gives the same result,
  error messages and paths included, on Python 3.10 and 3.14. No contract
  document changes.

## 1.1.0 - 2026-10-06

Tag `v1.1.0` on the commit of `main` that merges this section. A minor
release (COMPATIBILITY.md, "Repository releases"): new contract versions,
rules, schemas, catalogs and vectors next to the published ones; no
published document changes. Every revision pinned before it, including
`v1.0.0`, is an ancestor.

### Added

- Rejection before invocation, result identity and execution controls on the
  runtime, ratified as clarifications of Runtime Binding 1.0 and Typed Errors
  1.0: RT-016 to RT-023 (one category order, `validate`/`none`/`never` for
  every rejection, reflection of well-formed metadata only, a new result
  message identity with the request's as causation, UTC-only deadlines and
  elapsed deadlines as `timeout`, malformed or unsupported idempotency keys,
  one deadline channel) and ERR-014, ERR-015 (unknown after an unproven
  remote effect; cleanup after a proven publication). New schema
  `runtime-probe-v1.schema.json` and 21 probes in `vectors/runtime-probes-v1`,
  whose expected results the validator derives from the rules; two
  `storage.put` cleanup error vectors. The deadline spelling beyond `Z` and
  unknown `plenora.*` keys stay as 1.0 states them: narrowing them is
  incompatible. No existing schema, catalog, binding or vector changes. See
  [decision 0010](decisions/0010-runtime-rejection-and-identity.md).
- rest-tools CLI as an optional surface: the catalog selects the CLI as
  `conditional` and lists it for the five operations; `bindings/cli-v1.json`
  names the `plenora-rest` command, its discovery entrypoints and
  `<operation> --input REQUEST.json --format json`; the profile makes the
  command optional. The validator lets a REST capability document omit a
  conditional surface (it required the catalog's surfaces exactly). See
  [decision 0012](decisions/0012-rest-cli-optional.md). No schema or vector
  changes.
- IO-tools profile version 2 (`plenora-io-tools-profile-v2`, catalog
  `io-tools-v2.json`) next to version 1: `io.read` and `io.write` version 2
  with `plenora-io-read-result-v2` and `plenora-io-write-result-v2`, whose
  results name the serialization actually delivered or received, IPC stream
  or file (IO-SER-001; the version 1 schemas fix the file container and
  cannot change in place); `io.catalog` version 2 with
  `plenora-io-catalog-v2`, where every writable format states
  `requires_declared_geometry_types` (IO-CAT-001), so a sink's refusal of
  `types_declaration: unresolved` is predictable from the catalog; null in IO
  success results means "not applicable" (IO-NULL-001). CLI and runtime
  binding maps and the composition matrix add version 2 entries; version 1
  and every published document are unchanged. The three `-v2` schemas are
  IO-owned and published by IO-tools, not here. See
  [decision 0011](decisions/0011-io-tools-v2.md).
- Surface Bindings 1.0, SB-001: a surface that cannot return a result in
  process (a CLI whose machine stream carries one JSON document) writes it
  only to a destination the caller named and declares the effect it adds in
  the shared capability attribute `plenora.surface_side_effects`, an object
  from the operation's surfaces to `local` or `remote`, stricter than the
  operation's `side_effect`. Capability Discovery 2.0 reserves attribute keys
  beginning with `plenora.` for shared contracts. The validator checks SB-001
  on capability examples. See
  [decision 0009](decisions/0009-surface-materialization-and-established-absence.md),
  which also records why an established absence of geometry needs a
  successor Arrow vocabulary rather than an optional key in the closed 1.0
  vocabulary. No schema, catalog, binding or vector changes.

### Fixed

- The immutability gate in CI compared a push to any branch with the
  branch's previous tip. After merging `main` into a long-lived branch that
  tip predated changes `main` had made by decision, so the merge looked like
  removing a published vector (PR #6). Only a push to `main`, forced or not,
  is now compared with the previous tip; a release tag `v*` must point to a
  commit of `main` and is compared with it; a pull request or a push to
  another branch is compared with the commit where it leaves `main`, and
  every document it changed is also compared with the current `origin/main`,
  so an old branch cannot rewrite a document published after it forked
  (`tools/ci_comparison_base.py`). In CI `origin/main` is fetched first and
  must equal the remote's main, or the check fails. Tests on temporary Git
  repositories with a bare origin cover the merged branch, the old branch,
  the forced push, an obsolete `origin/main`, annotated and lightweight
  tags, tags on merge commits and on older commits of main, and a synthetic
  pull-request merge. No
  contract document changes.

## 1.0.0

First release, tag `v1.0.0`. It names the commit of `main` that merges this
section and contains everything published since the repository replacement
of 2026-08-18. Every revision pinned by a component before this release is an
ancestor of it: a pin includes exactly the changes in the history up to its
SHA (`git log <sha>`), and an entry below merged after that SHA does not
apply to it.

### Added

- `LICENSE`: the proprietary license of the other Plenora repositories. The
  repository had no license file. No contract document changes.
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

### Changed

- The validation gates run on Linux and Windows with Python 3.10 and 3.14
  (they ran only on Linux with Python 3.12). Their dependencies are installed
  from complete hashed locks (`requirements-*.txt`, generated from
  `requirements-*.in`) with `--require-hashes`; only `jsonschema` was pinned
  before. A weekly `supply-chain` workflow audits the locks with pip-audit and
  reruns the gates; Dependabot proposes action and lock updates; the coverage
  of the gate logic has a budget in `.coveragerc`. No contract document
  changes.
- Replaced the runtime vector `database-transaction-commit-success.json`
  with `database-query-success.json`: the database-tools catalog selects the
  `database.transaction.*` operations only on the Rust and Python surfaces,
  and the runtime binding map has no transaction selector, so the vector
  exercised an operation the runtime does not carry. The runtime vector
  matrix no longer lists transaction references. The validator now rejects a
  runtime vector whose operation version does not select the runtime surface,
  for every component. No catalog, binding or schema changes.
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

### Fixed

- The README's normative sources omitted Data Plan 1.0. The validator now
  rejects a specification under `specs/` that the list does not name.
- CUTOVER.md is marked as a historical record: it said storage-tools did not
  require Python (decision 0006 selected the Python SDK surface) and kept a
  snapshot of component status, which belongs to the adoption manifests. The
  snapshot is removed; the decisions it recorded are kept. No contract
  document changes.
- Erratum to `data.run` version 3, before any adoption or release used it:
  `rows_in` in `data-execution-result-v3.schema.json` is the list of the
  rows of each step input, as in the version 2 result (an integer could not
  describe a step with several inputs), and the success vector follows it;
  DT-RUN-006 allows `never`, `quarantine` or `requires_recovery` for an
  unproven publication outcome, as ERR-006 does. The schema is corrected in
  place because no artifact had adopted it; see
  [decision 0008](decisions/0008-data-run-runtime.md).
- The immutability gate protected only `schemas/`: a published catalog,
  operation registry, binding map or normative vector could change in place
  unnoticed. It now compares them with the same bases and admits only the
  additions COMPATIBILITY.md lists (a new operation identity, a new surface,
  a new binding or kernel, a new vector file). The ratified floor moves to the
  merge of PR #12, and a branch is also compared with the commit where it left
  `origin/main`, so documents published after the floor are protected on its
  first push. A declared erratum is admitted only while its decision exists
  and names the file, and only against a base that still published the error;
  the success vector of `data.run` 3, corrected by the same erratum, is now
  declared too. No contract document changes.
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
  object is expected is a validation error instead of a crash: a structural
  failure stops the gate before the semantic checks, any other exception is
  reported as an internal validator error without a traceback, and a null
  fuzz over every member of every vector and example guards the class. The REST
  boundary examples now state `version: 1`.
- The private-path and inline-credential guards of the validator missed
  `./x`, `~/x`, `C:relative\x`, `%TEMP%\x` and `$HOME/x`, and recognized
  credentials only by exact member name (`apiKey`, `client_secret` and
  `access_token` passed). A REST artifact reference must now be an opaque
  `scheme:` / `scheme://` reference; member names are compared lower-case
  without `_`, `-`, `.` and spaces, by substring, a `*_ref` member must hold
  an opaque reference, and authorization or PEM values are recognized under
  any name. A string that is a valid opaque reference (the `reference`
  grammar of `data-execution-input-v3.schema.json`) is never judged as a
  path, so `artifact://tenant/$HOME/report` stays valid; a backslash marks a
  path; member names are NFKC-folded. The residual limit of the heuristic is
  declared in the validator and in the REST and storage profiles. No contract document changes.
- The summary line of `tools/validate_specs.py` wrote the error-bound probes
  and the binding maps as literals (`7`, `3`); both are now counted from what
  the run checked.
