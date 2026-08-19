# Plenora Runtime Binding Contract 1.0

Status: normative

Contract identifier: `plenora-runtime-binding-v1`

This contract maps public operations to the transport-neutral capability
boundary exposed by runtime-tools. It governs serialized requests and results,
not adapters, handlers, queues or worker implementation.

## 1. Applicability

An operation follows this contract only when its capability descriptor lists the
`runtime` surface.

## 2. Capability identity

**RT-001** — The runtime capability name for component
`plenora-<domain>-tools` is `plenora.<domain>-tools`.

**RT-002** — Capability version `1` identifies this runtime binding version.
It is independent from component release and operation contract versions.

**RT-003** — The runtime operation selector carries the complete stable public
operation identifier, for example `database.read` or `geo.buffer`.

## 3. Request metadata

A runtime request carries these reserved metadata values:

| Key | Meaning |
|---|---|
| `plenora.capability.name` | runtime capability identity |
| `plenora.capability.version` | runtime binding version |
| `plenora.capability.operation` | stable public operation identifier |
| `plenora.operation.version` | operation contract version |
| `plenora.input.contract` | versioned input contract identifier |

**RT-004** — Routing and contract metadata MUST agree with one available
operation advertised by Capability Discovery 2.0. Mismatch fails before
invocation with `protocol` or `unsupported`.

**RT-005** — The serialized payload content type MUST be one of the input
content types advertised for that operation version.

Message identity, correlation identity and optional causation identity are
carried by the runtime message envelope and remain observable to the caller.

## 4. Execution controls

When advertised by the operation, the request MAY also carry:

- `plenora.execution.deadline`: an absolute RFC 3339 UTC timestamp;
- `plenora.execution.idempotency_key`: an opaque bounded key.

Cancellation is propagated by the runtime invocation context.

**RT-006** — A control MUST NOT be accepted silently when the operation
descriptor declares it unsupported.

**RT-007** — Deadline, cancellation and idempotency behavior MUST preserve the
semantics of the same operation version on its other public surfaces.

## 5. Success result

A successful runtime invocation returns serialized output with:

- content type advertised by the operation;
- `plenora.operation.version`;
- `plenora.output.contract`;
- the originating correlation identity.

**RT-008** — A result-producing operation MUST return its public result. A
successful acknowledgement with no result is conforming only when the declared
output contract explicitly represents an empty acknowledgement.

**RT-009** — Streaming and artifact-reference outputs MAY use transport-specific
delivery, but every delivered result MUST preserve the advertised content type,
output contract and correlation identity.

## 6. Failure result

**RT-010** — A public runtime failure MUST preserve the common error axes from
`plenora-error-v1`. An adapter-specific retry class is not a substitute for
the public category, phase, remote effect and retry disposition.

A serialized error result uses content type
`application/vnd.plenora.error+json` and output contract
`plenora-error-v1`.

**RT-011** — Unknown operation, version, input contract or content type fails
before invocation with `remote_effect: none`.

## 7. Security

Runtime requests follow
[Public Security 1.0](../security/PUBLIC-SECURITY-1.0.md). Persistable messages carry
connection or secret references and MUST NOT contain raw credentials, tokens,
authorization headers or private key material.

## 8. Compatibility

Adding optional metadata is compatible when its absence preserves previous
behavior. Renaming reserved keys, changing their meaning, changing routing
identity or weakening result/error semantics requires a new runtime binding
version.

## 9. Canonical selectors and vectors

The exact operation selectors for the five component profiles are registered
in [`bindings/runtime-v1.json`](../../bindings/runtime-v1.json). Reusable
request, success and error fixtures are defined by
[Runtime Conformance Vectors 1.0](RUNTIME-VECTORS-1.0.md).
