# 0006: Storage Python surface and conformance coverage

Status: accepted

Date: 2026-09-30

## Context

The storage v1 profile selected Rust, CLI and runtime while its Python binding
section was empty. Storage Tools publishes a Python SDK governed by the common
Python SDK contract; leaving the target map empty prevents consumers from
discovering the canonical operation-to-symbol mapping here.

## Decision

Select Python SDK as a required target for all seven storage v1 operations.
The `plenora-storage` distribution exposes the `plenora_storage` import,
`Engine` and `AsyncEngine`. Both classes bind the same seven operation names;
version and capability discovery are listed in the common Python binding map.

Keep provider-specific payload schemas and qualification evidence in the
component repository. Keep process-local Python file paths distinct from
opaque runtime artifact references. Remove implementation topology, cursor
cache sizing and development milestones from the normative profile.

Complete the runtime request fixtures for the seven operations and cover both
transfer directions and a partial result error. Exercise policy, artifact,
integrity and retry counterexamples in the existing spec-validation workflow.
These are contract checks, not live-provider or installed-wheel qualification.

## Compatibility and adoption

Consumers affected are SDK callers, runtime adopters and component maintainers
updating their pinned target catalog. Previously the Python surface had no
canonical storage symbols; now each operation names its sync and async methods.
Existing Rust, CLI and runtime entrypoints, operation versions, input/output
identifiers, defaults, error semantics and schema assertions remain unchanged.
Adding a surface is compatible under [COMPATIBILITY.md](../COMPATIBILITY.md).
No schema or operation major version is introduced.

The expanded target applies when adopting this revision. An adopter must record
the new immutable contracts pin, identify its Python wheel by version and digest,
and verify discovery, both API modes, lifecycle, typing and errors outside its
source checkout. Missing target behavior requires a scoped manifest deviation.

Storage Tools 2.1.0 adopted contracts revision
`f811f21f072b34896efdb6e110bee34d756153df` and the common Python SDK contract.
This decision does not retroactively repin or requalify that release. Its
manifests and receipts remain unchanged; adoption of this revision requires
component-owned evidence for the artifacts being claimed.
