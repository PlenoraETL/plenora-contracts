# Public operation contract template

Use this template in the component repository for an operation-specific public
contract. Delete instructional text before publishing.

## Identity

- Operation identifier: `<domain>.<action>`
- Operation version: `1`
- Input contract: `plenora-<name>-input-v1`
- Output contract: `plenora-<name>-output-v1`

State whether the operation is stable, experimental or deprecated.

## Public purpose

Describe what a caller asks the component to do and what observable result it
receives. Do not describe internal modules, dependencies or algorithms.

## Surfaces

List each public surface that exposes this operation:

- Rust:
- CLI:
- Python SDK:
- Runtime:

For each surface, show only the public entry point and its mapping to the common
operation identifier.

## Input

Define:

- required and optional public fields;
- field types, units and defaults;
- accepted content types;
- validation and unknown-field behavior;
- connection, provider, format or resource references;
- deadline, cancellation and idempotency-key support.

Link the versioned input schema or typed public definition.

## Output

Define:

- successful result fields and meaning;
- output content types;
- empty, streaming or artifact-reference behavior;
- partial-result semantics;
- Arrow schema and metadata when applicable.

Link the versioned output schema or typed public definition.

## Side effects and outcome

State whether the operation has no side effect, a local side effect or a remote
side effect. Define what complete success, rollback, partial completion and
unknown outcome mean to a caller.

## Public errors

List the common error categories and phases the caller may observe. For every
mutating phase, state the possible `remote_effect` and permitted `retry`
dispositions.

Document domain-specific machine codes without relying on message text.

## Capability attributes

List the typed attributes a consumer needs to select this operation safely,
such as provider, format, geometry, transfer or fidelity constraints.

Do not expose internal feature topology unless it changes artifact availability.

## Security

State:

- how secret and connection references cross the boundary;
- secure network defaults;
- explicit access opt-ins;
- redaction and output bounds.

## Compatibility

Describe additions that are compatible and changes that require a new operation
contract version.

## Black-box examples

Provide at least:

1. one valid request and result;
2. one invalid input rejected before side effects;
3. one unsupported capability;
4. one typed operational failure;
5. one partial or unknown outcome when the operation can mutate state.

## Explicit non-contract

List implementation details intentionally excluded from the public contract.
