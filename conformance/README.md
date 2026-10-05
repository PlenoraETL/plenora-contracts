# Black-box conformance

Conformance verifies public behavior without inspecting implementation details.
The executable harness lives in each component repository.

## Common checks

Every adopting component verifies that:

1. its capability document validates against the
   [capabilities v2 schema](../schemas/capabilities-v2.schema.json);
2. the document identifies the released artifact under test;
3. every advertised operation is reachable on every advertised surface;
4. unavailable operations fail closed before a side effect;
5. operation inputs and outputs use the advertised contract identifiers and
   content types;
6. public failures preserve all common error axes;
7. equivalent operations on multiple surfaces return equivalent observable
   results;
8. secret canaries never appear in discovery, results, errors or diagnostics.

For every operation advertising idempotency-key support, the component also
verifies stable delivery for repeated equivalent input and fail-closed reuse
with different input. Components advertising asynchronous HTTP recovery verify
submission, interrupted polling with a bounded recovery handle, resume without
resubmission and best-effort remote cancellation. Queue broker behavior is not
evidence for the HTTP component itself.

The repository validator additionally checks that target catalogs, surface
bindings and composition edges agree. Adopters consume those artifacts as test
inputs; they do not maintain independent copies of operation names.

Schema validation is necessary but does not establish cross-field conformance.
Capability documents also require unique `(id, version)` operation identities
(CAP-005) and operation surfaces present in `interfaces` (CAP-007).
Adoption manifests require unambiguous contract and artifact identities and
resolvable deviation references, as described in [ADOPTION.md](../ADOPTION.md).
The data-only checks in `tools/conformance_checks.py` run after structural
validation and are exercised by positive examples and semantic counterexamples.

The repository CI runs `tools/check_schema_immutability.py`, the regression
tests under `tools/test_*.py`, and `tools/validate_specs.py`. The example inventory
must include every JSON file under `examples/`; an unregistered example fails
the gate. The immutability guard compares published schema assertions,
catalogs, operation registries, binding maps and vectors with immutable Git
revisions ([COMPATIBILITY.md](../COMPATIBILITY.md#immutability-of-published-documents)).
It conservatively rejects assertion rewrites even if a reviewer believes them
equivalent; descriptive annotations can change without changing the contract
version.

## CLI checks

Invoke the installed or released binary as a subprocess. Verify help, version,
capabilities, one success, one validation failure, one unsupported operation
and one cancellation or timeout where applicable.

Validate stdout, stderr, exit code and the complete JSON document. Do not call
the CLI implementation as a library for this evidence.

## Python SDK checks

Install the built wheel in an environment that cannot import the source tree.
Verify package identity, `version()`, public exports, typing artifacts,
capability discovery, lifecycle, one success and typed failures.

Where sync and async forms exist, submit equivalent public inputs and compare
results and error axes.

## Rust checks

Publish the component-owned operation-to-public-export mapping, then compile a
consumer crate that depends only on those documented public exports. Verify
operation discovery, invocation and typed failures against the exact crate
version and digest recorded in manifest v4. Private modules, test-only features
and source-relative imports are not valid evidence.

## Runtime checks

Send the serialized input through the public runtime binding. Verify operation
and version selection, content type, correlation identity, result contract and
error mapping at the receiving boundary.

Run the fixtures in [`vectors/runtime-v1`](../vectors/runtime-v1/) for one
request, result and typed failure before claiming the runtime surface.

## Storage checks

The storage target includes all seven operations on Rust, CLI, Python SDK and
runtime. The common Python binding map names both `Engine` and `AsyncEngine`
entrypoints; the repository gate rejects a missing mode or discovery symbol.
An adopter still verifies the installed wheel and released artifacts itself.

The runtime fixtures include a request for every storage operation, success
results for list and both transfer directions, and partial/unknown error
outcomes. `tools/validate_specs.py` validates their metadata, catalog identity,
artifact roles, explicit policies, integrity and retry semantics. Missing
operation request coverage fails the gate.

`tools/test_storage_contracts.py`, run by the existing
[spec-validation workflow](../.github/workflows/spec-validation.yml), mutates
these fixtures to demonstrate rejection of missing policies, inline secrets,
local paths, invalid artifact references, inconsistent integrity/byte counts,
invalid cursors and unsafe retry. Positive boundary cases cover zero bytes,
maximum reference/metadata lengths and unknown optional source/sink metadata.
These checks do not replace validation against component-owned payload schemas.

Component evidence additionally exercises provider-specific create-if-absent
and atomic publication, pagination scope, cancellation and failures after a
possible write. Offline checks, local service fixtures and real-system
compatibility are separate claims. A missing real-account run is not a pass.

## Arrow checks

For every operation advertising Arrow:

- consume the emitted stream or file with an independent Arrow reader;
- compare schema metadata and stable field identifiers;
- verify geometry and CRS metadata consistency;
- round-trip representative null, decimal, temporal and geometry values when
  the operation claims lossless behavior;
- verify that an unsupported future contract version fails closed.

Run every fixture in [`vectors/arrow-v1`](../vectors/arrow-v1/), including the
semantic rejection cases from Arrow Metadata Vocabulary 1.0.

## Row diagnostics checks

Validate the complete diagnostics document against the
[row diagnostics schema](../schemas/row-diagnostics-v1.schema.json). Include cases for bounded examples,
redacted keys, partial knowledge and, for writes, an unknown remote outcome.

## Evidence recorded by the component

The adoption manifest records the exact contracts revision, public artifacts,
verification commands and deviations. Test output, provider fixtures and
release evidence remain in the component repository.
