# Plenora Surface Bindings Contract 1.0

Status: normative

Contract identifier: `plenora-surface-bindings-v1`

The exact bindings are machine-readable in [`bindings`](../../bindings/) and
validate against
[`surface-bindings-v1.schema.json`](../../schemas/surface-bindings-v1.schema.json).

## 1. One operation, multiple spellings

CLI commands, Python methods and runtime selectors are spellings of a catalog
operation, not independent semantics. Each binding identifies exactly one
`(operation, version)` pair from the component catalog.

A surface MAY wrap inputs and results in idiomatic types. It MUST preserve the
catalog contracts, defaults, error axes, side effects and execution controls.

## 2. CLI binding

[`cli-v1.json`](../../bindings/cli-v1.json) defines canonical commands. Tokens
written in uppercase denote caller-provided values; they are grammar
placeholders, not literal arguments.

Every listed CLI artifact also implements `--help`, `--version --format json`
and `capabilities --format json` according to CLI 2.0. Diagnostic, benchmark,
fuzz and self-test commands are not public domain bindings.

Deprecated aliases MAY remain callable only when listed under
`deprecated_aliases`. They MUST resolve to the canonical operation and emit the
same machine result. New integrations MUST use the canonical entrypoint.

## 3. Python binding

[`python-sdk-v1.json`](../../bindings/python-sdk-v1.json) defines distribution,
import and symbol spellings. The required target packages are:

| Component | Distribution | Import |
|---|---|---|
| database-tools | `plenora-database` | `plenora_database` |
| rest-tools | `plenora-rest` | `plenora_rest` |

Sync and async symbols listed for the same operation are semantically
equivalent. Lifecycle helpers and query builders may expose several idiomatic
methods that all bind to one operation identity.

## 4. Runtime binding

[`runtime-v1.json`](../../bindings/runtime-v1.json) uses the canonical selector
form `<capability>#<operation>@<operation-version>`. The capability name is
`plenora.<domain>-tools`; the runtime capability version remains `1` as defined
by Runtime Binding 1.0.

The selector is review notation. Serialized requests still carry the reserved
metadata keys from Runtime Binding 1.0 and MUST NOT derive routing by parsing a
CLI command or Python symbol.

## 5. Adoption rule

Target bindings describe what a conforming public artifact exposes. Existing
legacy spellings do not become normative merely because they are implemented.
During migration an adopter records the missing canonical binding and any
temporary alias in its adoption manifest.

This contract names public entrypoints only. It does not prescribe the internal
function, module, native binding technology or command dispatcher used to
implement them.
