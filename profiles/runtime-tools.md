# Transport consumer profile: runtime-tools

Profile identifier: `plenora-runtime-tools-profile-v1`

Normative runtime selectors: [`runtime-v1.json`](../bindings/runtime-v1.json)

## Role

`runtime-tools` is the common transport consumer for the five domain-library
profiles. It is not a sixth domain library and does not own their operation
schemas, capability truth, domain errors or business semantics.

## Applicable contracts

- [Runtime Binding 1.0](../specs/runtime/RUNTIME-BINDING-1.0.md)
- [Runtime Conformance Vectors 1.0](../specs/runtime/RUNTIME-VECTORS-1.0.md)
- [Typed Errors 1.0](../specs/errors/ERRORS-1.0.md), for serialized public failures
- [Public Security 1.0](../specs/security/PUBLIC-SECURITY-1.0.md)
- [Surface Bindings 1.0](../specs/surfaces/SURFACE-BINDINGS-1.0.md)

## Required public behavior

The released Rust and runtime artifacts MUST:

- preserve the request, success and error metadata defined by Runtime Binding
  1.0 without interpreting domain payloads;
- reject malformed routing, operation version, contract identity, content type
  or envelope identity before domain invocation;
- preserve payload bytes, advertised content type, supported execution controls
  and originating correlation identity;
- return serialized output for result-producing operations rather than reducing
  success to an acknowledgement;
- expose terminal public failures as bounded `plenora-error-v1` values while
  keeping retry settlement and remote-effect certainty conservative;
- exercise the pinned runtime vectors through a public codec or transport
  boundary.

`runtime-tools` validates the envelope, routing and compatibility with
registered capabilities. The black-box component validates its own payload and
operation semantics. No provider adapter belongs to `runtime-tools`.

## Public surfaces

- Rust API: required.
- Runtime transport: required for a conformance claim.
- CLI: not required by this profile.
- Python SDK: not required by this profile.

## Adoption

`runtime-tools` records a full immutable `plenora-contracts` revision and
black-box verification commands in adoption manifest v3. It MUST NOT mark
Runtime Binding 1.0 conforming while request, success or terminal-error vector
coverage is incomplete. Temporary gaps are documented as deviations and do not
count as conformance.

## Not specified here

This profile does not prescribe worker engines, brokers, queues, handler
registries, retry schedulers, result topics or internal Rust module boundaries.
