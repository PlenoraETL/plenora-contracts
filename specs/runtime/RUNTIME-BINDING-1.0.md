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
| `plenora.trace.correlation_id` | originating correlation identity |

**RT-004** — Routing and contract metadata MUST agree with one available
operation advertised by Capability Discovery 2.0. Mismatch fails before
invocation with `protocol` or `unsupported`.

**RT-005** — The serialized payload content type MUST be one of the input
content types advertised for that operation version.

The runtime message envelope carries these identity keys:

| Key | Requirement |
|---|---|
| `plenora.message.id` | required unique message identity |
| `plenora.trace.correlation_id` | required originating correlation identity |
| `plenora.message.causation_id` | optional direct-cause message identity |

**RT-012** — Envelope identities MUST use the canonical lowercase hyphenated
UUID representation. Alternate key spellings and non-canonical UUID text are
not compatible aliases. Message and optional causation identities remain
observable to the caller; results preserve the originating correlation UUID.

## 4. Execution controls

When advertised by the operation, the request MAY also carry:

- `plenora.execution.deadline`: an absolute RFC 3339 UTC timestamp;
- `plenora.execution.idempotency_key`: an opaque bounded key.

Cancellation is propagated by the runtime invocation context.

**RT-006** — A control MUST NOT be accepted silently when the operation
descriptor declares it unsupported.

**RT-007** — Deadline, cancellation and idempotency behavior MUST preserve the
semantics of the same operation version on its other public surfaces.

## 5. Artifact-bearing requests and results

**RT-013** — A persistable serialized input that identifies a file or other
artifact MUST carry an opaque artifact reference. Private local paths MUST NOT
cross the runtime boundary. The reference is resolved only through an
authorized runtime resource. When the component contract declares artifact
metadata, it is bounded and keeps content type, byte size and a genuinely
calculated SHA-256 separate from provider-specific identifiers.

**RT-014** — An artifact result MUST preserve its output contract, content
type, originating correlation identity, byte count and checksum algorithm and
value. The concrete transport or storage mechanism for the artifact is
implementation-specific.

**RT-015** — Artifact source and sink resolution belongs to the final
application boundary. A component may expose transport-neutral resolver traits
but MUST NOT require a core runtime-tools crate to depend on the component.

## 6. Success result

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

## 7. Failure result

**RT-010** — A public runtime failure MUST preserve the common error axes from
`plenora-error-v1`. An adapter-specific retry class is not a substitute for
the public category, phase, remote effect and retry disposition.

A serialized error result uses content type
`application/vnd.plenora.error+json` and output contract
`plenora-error-v1`.

**RT-011** — Unknown operation, version, input contract or content type fails
before invocation with `remote_effect: none`.

## 8. Security

Runtime requests follow
[Public Security 1.0](../security/PUBLIC-SECURITY-1.0.md). Persistable messages carry
connection or secret references and MUST NOT contain raw credentials, tokens,
authorization headers or private key material.

## 9. Compatibility

Adding optional metadata is compatible when its absence preserves previous
behavior. Renaming reserved keys, changing their meaning, changing routing
identity or weakening result/error semantics requires a new runtime binding
version.

## 10. Canonical selectors and vectors

The exact operation selectors for the five component profiles are registered
in [`bindings/runtime-v1.json`](../../bindings/runtime-v1.json). Reusable
request, success and error fixtures are defined by
[Runtime Conformance Vectors 1.0](RUNTIME-VECTORS-1.0.md).
