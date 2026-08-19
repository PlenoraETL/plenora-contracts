# Decision 0004: Specify public functionality across all surfaces

Status: accepted

## Context

CLI and Python conventions alone do not tell Plenora components how to expose
the same operation to Rust callers, runtime orchestration and other libraries.
The five domain projects need a common, self-contained description of what is
public and how a consumer discovers and interprets it.

The contracts must not become an architecture manual for the implementations.

## Decision

This repository governs every shared, externally observable Plenora boundary:
operation identity, capability discovery, input/output contract references,
typed failures, interchange artifacts, CLI and SDK behavior.

Component profiles define target public capability families and applicable
surfaces. They do not report implementation status.

A requirement is admitted only when it can be verified without inspecting
component internals. Traits, modules, dependencies, algorithms and execution
mechanisms remain component-owned.

## Consequences

- An adopter can align its public surface without reading the other four
  implementations.
- Rust, CLI, Python and runtime bindings can expose the same operation with
  idiomatic types while preserving common semantics.
- Shared Arrow metadata and row diagnostics have one normative authority.
- Operation-specific domain contracts remain component-owned until they become
  a cross-component interchange boundary.
- Conformance evidence remains black-box and component-owned.
