# Contract governance

## Purpose

These contracts make independently implemented Plenora components
interoperable. They govern public boundaries, not component architecture.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY in normative documents
describe requirement strength.

## Boundary test

A proposed requirement is in scope only if all of the following are true:

1. a caller, orchestrator or another component can observe it at a public
   boundary;
2. at least one consumer needs it to invoke, interpret or safely compose a
   component;
3. it can be verified through a public API, process boundary or serialized
   artifact;
4. it does not require a particular internal design.

Requirements that fail this test stay in the implementing repository.

## Ownership

This repository owns shared identifiers, shared wire shapes and shared
observable semantics. A component owns its domain algorithms and any public
contract used only by that component.

When an operation-specific contract becomes an interchange boundary between
components, it can be promoted here through a versioned specification. Promotion
does not transfer ownership of the implementation.

## Normative and informative material

- Files under `specs/`, `schemas/` and the applicability statements under
  `profiles/` are normative.
- Machine-readable test vectors explicitly marked normative are normative.
- `examples/`, `decisions/` and explanatory text marked as rationale are
  informative.
- Component status and release evidence are never normative here.

If prose and a referenced schema disagree for a serialized document, the schema
controls validation and the disagreement is a specification defect to fix.

## Requirement references

New requirements use stable identifiers such as `SURF-001`, `CAP-006`,
`ARROW-004`, `DIAG-003`, `CLI-2.4` or `SDK-1.6`. Adoption manifests and
deviations cite these identifiers or an unambiguous document section.

An identifier is never reused for different semantics.

## Change process

Every contract change states:

- the affected public consumer;
- the observable behavior before and after the change;
- whether the change is compatible;
- the schemas, examples and profiles affected;
- the adoption impact for each applicable component.

An incompatible change adds a new contract version. Existing versioned schemas
and identifiers remain available for consumers pinned to them.

## Profiles and status

A profile answers only:

- which public capability families a component is expected to expose;
- through which public surfaces they may be reached;
- which shared contracts apply to those boundaries.

A profile must not describe the component's internal architecture or claim its
current completion status. The component-owned adoption manifest is the source
for conformance status and deviations.
