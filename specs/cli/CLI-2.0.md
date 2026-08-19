# Plenora CLI Contract 2.0

Status: normative

Contract identifier: `plenora-cli-v2`

This document is normative. The key words MUST, MUST NOT, SHOULD, SHOULD NOT and
MAY describe requirement strength.

## 1. Applicability

This contract applies to a component that exposes a public process-level CLI.
Internal benchmark, fuzzing and developer-only binaries are out of scope unless
the component explicitly declares them public.

## 2. Invocation modes

A conforming CLI MUST support an explicit JSON mode through `--format json`.
JSON mode is the only machine contract defined here.

A CLI MAY provide an explicit human format. Human output is not constrained by
the JSON stream rules and MUST NOT be selected implicitly by an orchestrator.

Unknown commands, unknown flags, missing values and extra positional arguments
MUST fail closed. They MUST NOT be ignored.

## 3. Required discovery surface

A conforming CLI MUST provide:

- `--help`;
- `--version --format json`;
- `capabilities --format json`.

The JSON version response MUST use the common success envelope. Its `result`
MUST include `component_version` and the adopted CLI protocol version.

Help MUST describe only commands compiled into that binary. Feature-disabled
commands MUST either be absent or produce a precise rebuild instruction; they
MUST NOT appear as available commands.

## 4. Machine output

In JSON mode, an invocation MUST:

- encode UTF-8 JSON;
- write exactly one JSON document followed by one newline to stdout;
- write nothing to stderr;
- use the envelope in `schemas/cli-envelope-v2.schema.json`;
- return exit code 0 only when `status` is `ok`;
- return a non-zero exit code only when `status` is `error`.

Progress, logging, warnings, panic hooks and dependency diagnostics MUST NOT
produce additional process output in JSON mode. A component MAY send protected
diagnostics to an external sink that is not stdout or stderr.

JSON object key order is not significant. Consumers MUST ignore unknown
optional fields unless the enclosing schema forbids them.

## 5. Success envelope

The required top-level fields are:

- `status`: `ok`;
- `protocol_version`: integer `2`;
- `component`: stable component identifier;
- `component_version`: released component version;
- `contract`: operation-specific, namespaced contract identifier;
- `command`: canonical command identifier;
- `result`: operation-specific JSON object.

Operation-specific data MUST be inside `result`; it MUST NOT create additional
top-level fields.

## 6. Error envelope

The required top-level fields are the same identity fields as a success
envelope, with `status: error` and an `error` object instead of `result`.

The `error` object MUST validate against `schemas/error-v1.schema.json`.
Machine behavior MUST be derived from typed fields, never by parsing `message`.

`message` MUST be redacted. It MUST NOT contain credentials, tokens, DSNs,
authorization headers, bound SQL, source rows or unbounded remote payloads.

Unhandled panics or exceptions MUST be converted to an `internal` error with a
redacted message. A stable non-reversible fingerprint MAY be included in
`details`.

## 7. Error axes

Every error carries four independent axes:

- `category`: what failed;
- `phase`: when it failed;
- `remote_effect`: what may have happened remotely;
- `retry`: what retry behavior is permitted.

`remote_effect: unknown` MUST NOT be paired with automatic retry. It normally
requires `quarantine` or `requires_recovery`.

`retry: after` MUST include a non-negative `delay_ms`. Other retry kinds MUST
NOT include `delay_ms`.

## 8. Exit codes

The JSON category is authoritative. The exit code is its stable coarse
projection:

| Code | Categories |
|---:|---|
| 0 | success |
| 2 | `invalid_plan`, `invalid_configuration` |
| 3 | `schema`, `data_mapping`, `crs`, `unsupported` |
| 4 | `resource_limit` |
| 5 | `io`, `not_found`, `conflict`, `concurrent_modification`, `protocol`, `authentication`, `authorization`, `timeout`, `transient` |
| 6 | `execution` |
| 70 | `internal` or an unmapped category |
| 130 | `cancelled` |

A new category MUST have an explicit mapping before release. Until then it MUST
project to 70, never to success.

## 9. Cancellation and deadlines

Cooperative cancellation MUST produce category `cancelled` and exit code 130.
The other error axes MUST still describe the phase, possible remote effect and
retry constraints.

A deadline or timeout MUST fail with a typed error. If completion is ambiguous,
the CLI MUST report `remote_effect: unknown` even when the local caller has
stopped waiting.

## 10. Capabilities

The capability response MUST validate against
`schemas/capabilities-v2.schema.json` and be carried inside the common success
envelope.

Capabilities MUST describe the binary that is running, including compile-time
feature selection. Unsupported behavior MUST remain unavailable or fail closed;
roadmap intent is not a capability.

Every public command that invokes domain functionality MUST map to an operation
identifier advertised by capability discovery. The CLI command name MAY be a
surface-specific spelling, but its operation version, input/output contract,
errors and side effects MUST remain equivalent to the other advertised surfaces.

## 11. Security

Production network connections MUST verify server identity by default.
Insecure modes MUST be explicit, clearly named and opt-in.

Secrets MUST NOT be accepted as ordinary command-line values because process
arguments are commonly observable. Components SHOULD use environment-variable
names, protected files, standard input or an external secret provider.

Machine output and error messages MUST be safe to persist in CI logs.

## 12. Compatibility

Within protocol version 2:

- adding an optional field is compatible;
- removing or renaming a required field is incompatible;
- changing a field type or meaning is incompatible;
- extending a closed enum requires an explicit compatibility review;
- changing stream selection or exit-code projection is incompatible.

An incompatible change requires a new protocol version and schema identifier.
