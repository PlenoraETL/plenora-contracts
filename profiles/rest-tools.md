# Public profile: rest-tools

Profile identifier: `plenora-rest-tools-profile-v1`

Normative target catalog: [`rest-tools-v1.json`](../catalogs/rest-tools-v1.json)

## Applicable contracts

- [Public Surfaces 1.0](../specs/surfaces/PUBLIC-SURFACES-1.0.md)
- [Capability Discovery 2.0](../specs/capabilities/CAPABILITY-DISCOVERY-2.0.md)
- [Typed Errors 1.0](../specs/errors/ERRORS-1.0.md)
- [Public Security 1.0](../specs/security/PUBLIC-SECURITY-1.0.md)
- [Python SDK 1.0](../specs/sdk/PYTHON-SDK-1.0.md)
- [Runtime Binding 1.0](../specs/runtime/RUNTIME-BINDING-1.0.md)
- [Arrow Interchange 1.0](../specs/data/ARROW-INTERCHANGE-1.0.md), when advertised
- [Surface Bindings 1.0](../specs/surfaces/SURFACE-BINDINGS-1.0.md)
- [Composition 1.0](../specs/composition/COMPOSITION-1.0.md)

## Public purpose

The component exposes a stable black-box HTTP execution surface. HTTP client,
pool, authentication flow and retry implementation remain private.

## Required operation families

The stable public catalog includes:

- `rest.test`;
- `rest.generate`;
- `rest.enrich`;
- `rest.download`;
- `rest.upload`.

Each operation descriptor declares input and output contracts, side effects,
execution controls and externally relevant limits. Supported HTTP methods,
authentication modes, response formats, pagination, polling and transfer
behavior are structured capability attributes rather than hidden inference.

## Component-owned contracts

The component owns and versions:

- `plenora-rest-execution-request-v1`;
- `plenora-rest-execution-result-v1`;
- `plenora-rest-file-transfer-input-v1`;
- `plenora-rest-file-transfer-result-v1`;
- `plenora-rest-capability-attributes-v1`.

Their normative schemas and operation specifications live in the adopting
`rest-tools` repository. The common catalog references their immutable
identifiers without centralizing provider or implementation details.

## Public surfaces

- Rust API: required.
- CLI: not required by this profile.
- Python SDK: required and governed by Python SDK 1.0.
- Runtime: required for every REST operation selected for orchestration.

The v1 catalog selects all five REST operations for the runtime surface; the
runtime target is therefore required, not conditional.

Equivalent Rust, Python and runtime operations preserve operation status,
output meaning and the common typed error axes.

## Artifact semantics

Rust and in-process Python callers may provide an explicitly authorized local
path as an input convenience. Serialized runtime requests use opaque artifact
references.

Public results identify an artifact through bounded metadata and an opaque
reference. They never echo private local paths.

The file-transfer input carries the REST connection configuration, artifact
source or sink, content type, size limits and optional integrity constraints.
Raw file bytes are not embedded in persistable JSON requests.

## Interchange

JSON is the default structured representation. Binary and file transfer
operations declare their content type and artifact contract explicitly.

Arrow is optional and applies only if an operation advertises Arrow input or
output. REST responses MUST NOT be represented as Arrow merely to satisfy this
profile.

## External security

TLS verification is secure by default. Insecure networking, private-network
access, redirects, custom methods and local file transfer are explicit,
discoverable opt-ins.

Credentials, tokens, PEM material, authorization headers, body previews and
local paths MUST NOT appear in capability documents, public errors or persisted
diagnostics.

## Not specified here

This profile does not prescribe the HTTP client, connection pool, DNS resolver,
retry loop, Python binding technology or internal JSON representation.
