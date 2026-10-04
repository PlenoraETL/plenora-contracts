# 0008: Data-tools `data.run` version 3 on the runtime surface

Status: accepted

Date: 2026-10-04

## Context

Decision 0007 left `data.run` version 2 off the runtime surface: its result
names any number of outputs, Runtime Binding 1.0 carries one payload per
response, and binding version 2 with a one-output restriction would make the
same operation version validate differently across surfaces. Orchestrated
execution kept `data.run` version 1, which belongs to profile version 1 and
its plan formats. Runtime-tools, for operations that carry artifacts, waits
for an immutable payload schema owned by the contracts instead of inferring
fields from JSON.

## Decision

Add `data.run` version 3 to `data-tools-v2.json`, next to version 2:

- input `plenora-data-execution-input-v3`, a JSON request with the plan, one
  artifact source per plan input and one artifact sink per plan output, each
  an opaque reference (RT-013), with explicit `overwrite` on sinks and
  optional expected size and SHA-256 on sources;
- output `plenora-data-execution-result-v3`, a JSON manifest: every output in
  plan order with its reference, rows, columns, content type, byte size and
  calculated SHA-256, plus the per-step counts of version 2;
- `side_effect: remote`, because sinks may be remote and `local` would
  promise that they are not; `conditional`; surfaces Rust and runtime;
- the schemas are owned here, because the runtime and the component both
  read the references;
- the profile states the rules DT-RUN-001 to DT-RUN-008: exact names, opaque
  references resolved only by the application's resolver, integrity of
  sources, the semantics of version 2, nothing published before every
  output is encoded, ordered publication with atomic `overwrite: false`,
  `unknown` prevailing over `partial` when an outcome is unproven, and no
  resolved location in results or errors; the ordering guarantees are shown
  with an instrumented resolver;
- the runtime binding map adds `plenora.data-tools#data.run@3`; new vectors
  cover a request, its manifest, a partial and an unknown publication error;
- the validator looks operations and SDK bindings up by `(id, version)` in
  every component, so each version of an operation is checked and none
  hides another; coexisting versions stay allowed (COMPATIBILITY.md).

## Alternatives

- **One output per invocation.** The request would select one output and the
  result would be one Arrow stream. A plan with N outputs would run N times.
- **One Arrow container for every output.** One payload, but outputs with
  different schemas would be flattened into a discriminated table.
- **A new data-tools catalog version.** Adding an operation version under a
  new identity is compatible (COMPATIBILITY.md); no existing operation changes,
  so catalog version 2 grows instead.

## Change statement

- **Consumers affected:** runtime adopters that want plans with named
  outputs; none of the existing operation versions change.
- **Before:** orchestrated execution only through `data.run` version 1.
- **After:** `data.run` version 3 executes `plenora-data-plan-v1` plans on the
  runtime, from artifact sources to artifact sinks.
- **Compatibility:** compatible; a new operation identity
  `(data.run, 3)` and new contract identifiers. An artifact that adopted
  catalog version 2 without the runtime surface stays conforming:
  the operation is conditional.
- **Schemas:** new `data-execution-input-v3.schema.json` and
  `data-execution-result-v3.schema.json`; no existing schema changes.
- **Examples and vectors:** `data-run-request-v3.json`,
  `data-run-success-v3.json`, `data-run-partial-error-v3.json`,
  `data-run-unknown-error-v3.json`.
- **Adoption:** Data Tools adopts version 3 with a new pin, through a Rust
  entry point that takes resolver traits for sources and sinks (RT-015).
