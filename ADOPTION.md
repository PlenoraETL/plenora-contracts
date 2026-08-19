# Adopting the public contracts

Adoption demonstrates public behavior. It is not an instruction for organizing
component internals.

## Adoption sequence

1. Select the component profile under `profiles/`.
2. Pin an immutable revision of this repository.
3. Identify the public artifacts covered by the profile: binaries, packages,
   crates or runtime endpoints.
4. Verify each applicable contract through those public artifacts.
5. Record the pin, verification commands and deviations in a component-owned
   adoption manifest that validates against the
   [adoption manifest v3 schema](schemas/adoption-manifest-v3.schema.json).

The adopting project decides how to implement the required behavior.

## Black-box evidence

Verification should exercise the same boundary used by a real consumer:

- launch the released binary for CLI checks;
- import an installed wheel outside the source checkout for Python SDK checks;
- call only documented public Rust exports for Rust checks;
- send serialized requests through the public transport for runtime checks;
- validate emitted JSON and Arrow artifacts without inspecting private state.

Tests that read private fields or call private helpers are useful component
tests but are not sufficient adoption evidence.

## Capability truthfulness

The capability document must describe the exact artifact under test. An
operation disabled by build features or unavailable for the selected provider
must not be advertised as available.

## Deviations

A deviation records:

- the exact requirement identifier;
- the externally observable difference;
- the affected public artifact or surface;
- a tracking reference;
- whether consumers can detect the difference before invocation.

A deviation does not redefine the common contract and does not count as
conformance for that requirement.

## No central implementation harness

This repository provides schemas, examples and black-box vectors. Each
component owns the executable harness needed to invoke its artifact because
build systems, provider fixtures and release environments differ.

Manifest v1 remains available for the former CLI/SDK-only scope. Manifest v2
remains immutable for existing cross-surface declarations. New adoption uses
manifest v3, which records `api_modes` for every Python SDK artifact.
