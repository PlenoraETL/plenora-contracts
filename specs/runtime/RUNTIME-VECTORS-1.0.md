# Plenora Runtime Conformance Vectors 1.0

Status: normative

Contract identifier: `plenora-runtime-vector-v1`

The fixtures in [`vectors/runtime-v1`](../../vectors/runtime-v1/) make the
Runtime Binding 1.0 metadata and result rules directly reusable by
`runtime-tools` and each domain component.

## 1. Request vector

A request vector contains the exact routing identity, operation version, input
contract and content type. A component test MUST reject any mutation that makes
these values disagree with its capability descriptor before invoking domain
functionality.

Every vector carries `plenora.trace.correlation_id` as a canonical lowercase
hyphenated UUID. Request metadata additionally carries the runtime capability
identity; success and error metadata carry the output contract.

The payload is illustrative operation data. It deliberately uses protected
references and MUST NOT be replaced with real credentials in committed test
evidence.

## 2. Success vector

A success vector preserves operation version, output contract and correlation
identity. Returning only an acknowledgement for a result-producing operation
does not satisfy the fixture.

## 3. Error vector

An error vector uses `application/vnd.plenora.error+json`, identifies
`plenora-error-v1` and carries all common error axes. Unknown remote effect is
paired with quarantine or recovery, never automatic retry.

## 4. Use by adopters

`runtime-tools` tests envelope transport and metadata preservation. A domain
component tests selector validation, invocation and semantic result/error
mapping through its public runtime adapter. Neither test needs access to the
other component's private types.

`runtime-tools` adopts these obligations through the separate
[runtime-tools transport profile](../../profiles/runtime-tools.md). That profile
does not make it a sixth domain library.

The structural shape is defined by
[`runtime-vector-v1.schema.json`](../../schemas/runtime-vector-v1.schema.json).
The repository semantic validator also checks the vectors against the public
catalogs and typed error schema.
