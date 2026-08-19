# Plenora Public Interface Contracts

This repository defines the public contracts through which Plenora components
expose functionality to callers, orchestrators and other components.

It specifies what is observable at a boundary: operation identity, capability
discovery, accepted inputs, returned outputs, typed failures, CLI behavior,
SDK behavior and shared interchange formats. It does not prescribe how a
component is implemented.

## Boundary rule

A requirement belongs here only when an external consumer can verify it
without inspecting component internals.

This repository may require that `io.read` is discoverable, accepts a
versioned input contract and returns a declared output contract. It must not
require a particular Rust trait, module layout, executor, dependency or
algorithm.

## Reading path

A component adopter reads:

1. its target profile in [profiles](profiles/README.md);
2. its machine-readable target catalog in [catalogs](catalogs/);
3. the normative specifications and exact surface bindings linked by that profile;
4. the versioned schemas and conformance vectors referenced by those specifications;
5. [ADOPTION.md](ADOPTION.md) to publish a pinned conformance declaration.

An adopter does not need to read the implementation of the other components.

## Normative sources

The normative sources are:

- [public surface contract](specs/surfaces/PUBLIC-SURFACES-1.0.md);
- [public catalogs contract](specs/catalogs/PUBLIC-CATALOGS-1.0.md);
- [exact surface bindings](specs/surfaces/SURFACE-BINDINGS-1.0.md);
- [capability discovery contract](specs/capabilities/CAPABILITY-DISCOVERY-2.0.md);
- [typed error contract](specs/errors/ERRORS-1.0.md);
- [Arrow interchange contract](specs/data/ARROW-INTERCHANGE-1.0.md);
- [Arrow metadata vocabulary and vectors](specs/data/ARROW-VOCABULARY-1.0.md);
- [row diagnostics contract](specs/diagnostics/ROW-DIAGNOSTICS-1.0.md);
- [public security contract](specs/security/PUBLIC-SECURITY-1.0.md);
- [runtime binding contract](specs/runtime/RUNTIME-BINDING-1.0.md);
- [runtime conformance vectors](specs/runtime/RUNTIME-VECTORS-1.0.md);
- [cross-component composition contract](specs/composition/COMPOSITION-1.0.md);
- [CLI contract](specs/cli/CLI-2.0.md);
- [Python SDK contract](specs/sdk/PYTHON-SDK-1.0.md);
- the versioned JSON Schemas in [schemas](schemas/README.md);
- the applicability rules in [profiles](profiles/README.md).

Black-box verification guidance is collected in
[conformance](conformance/README.md).
Component-owned operation specifications can start from the
[public operation template](templates/OPERATION-CONTRACT.md).

Examples illustrate the normative sources but do not override them. Decisions
explain why a rule exists and are not a second specification.

## Scope

This repository owns cross-component public behavior:

- stable component, operation and contract identifiers;
- exact target operation catalogs and CLI, Python and runtime spellings;
- discovery of operations actually exposed by a released artifact;
- public input, output and error semantics;
- common CLI and Python SDK behavior;
- Arrow and GeoArrow metadata exchanged between components;
- bounded row-level diagnostics exposed to callers;
- compatibility and adoption declarations;
- reviewed direct and adapter-required composition edges.

An operation-specific input or output contract belongs here when two or more
components exchange it directly. A contract used by only one component remains
component-owned and is referenced by its stable identifier.

## Explicit exclusions

This repository does not own:

- crate, package, module or directory layout;
- Rust traits, private types, executors, pools, threads or async runtimes;
- algorithms, query planners, parsers, drivers or provider implementations;
- database dialect internals, storage engines or file-format internals;
- dependency selection or implementation performance techniques;
- snapshots of the current implementation status of a component.

Profiles define the target public surface. Actual status, verification commands
and temporary deviations live in the adopting component's manifest.

## Components

The initial profiles cover:

- `plenora-database-tools`;
- `plenora-data-tools`;
- `plenora-io-tools`;
- `plenora-rest-tools`;
- `plenora-storage-tools`.

`runtime-tools` is a consumer and transport binding for these public contracts;
it is not one of the five domain libraries.

## Versioning

Contract identifiers are immutable. Compatible clarification may update prose.
Any change that alters accepted machine data or observable meaning requires a
new schema or contract version. See [COMPATIBILITY.md](COMPATIBILITY.md).

## Adoption

Conformance is explicit and pinned to an immutable revision. A project cannot
claim conformance merely because its internal types look similar. It must expose
the required behavior and verify it through its public boundary as described in
[ADOPTION.md](ADOPTION.md).
