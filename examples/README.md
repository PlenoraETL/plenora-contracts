# Examples

Files under `valid` must satisfy the indicated structural or semantic check.
Files under `invalid` are deliberate counterexamples and must fail that check.

| Example | Validation |
|---|---|
| `valid/cli-success.json` | `cli-envelope-v2.schema.json` |
| `valid/cli-error.json` | `cli-envelope-v2.schema.json` |
| `valid/capabilities.json` | `capabilities-v1.schema.json` |
| `valid/capabilities-v2.json` | `capabilities-v2.schema.json` |
| `valid/capabilities-rest-v2.json` | `capabilities-v2.schema.json` plus REST catalog semantics |
| `valid/row-diagnostics.json` | `row-diagnostics-v1.schema.json` |
| `valid/adoption-manifest.json` | `adoption-manifest-v1.schema.json` |
| `valid/adoption-manifest-v2.json` | `adoption-manifest-v2.schema.json` |
| `valid/adoption-manifest-v3.json` | `adoption-manifest-v3.schema.json` |
| `valid/rest-runtime-artifact-request.json` | REST runtime boundary invariants |
| `invalid/cli-missing-protocol.json` | `cli-envelope-v2.schema.json` |
| `invalid/error-after-missing-delay.json` | `error-v1.schema.json` |
| `invalid/capabilities-unavailable-without-reason.json` | `capabilities-v1.schema.json` |
| `invalid/capabilities-v2-unavailable-without-reason.json` | `capabilities-v2.schema.json` |
| `invalid/row-diagnostics-redacted-value.json` | `row-diagnostics-v1.schema.json` |
| `invalid/adoption-floating-revision.json` | `adoption-manifest-v1.schema.json` |
| `invalid/adoption-v2-floating-revision.json` | `adoption-manifest-v2.schema.json` |
| `invalid/adoption-v3-python-missing-api-modes.json` | `adoption-manifest-v3.schema.json` |
| `invalid/runtime-correlation-not-uuid.json` | `runtime-vector-v1.schema.json` |
| `invalid/runtime-message-id-missing.json` | `runtime-vector-v1.schema.json` |
| `invalid/runtime-message-id-not-uuid.json` | `runtime-vector-v1.schema.json` |
| `invalid/rest-capabilities-attributes-missing-contract.json` | REST capability semantics |
| `invalid/rest-runtime-artifact-local-path.json` | REST runtime boundary invariants |
| `invalid/rest-runtime-artifact-relative-path.json` | REST runtime boundary invariants |
| `invalid/rest-download-artifact-source-only.json` | REST artifact direction invariants |
| `invalid/rest-upload-artifact-sink-only.json` | REST artifact direction invariants |
| `invalid/rest-runtime-upload-inline-credentials.json` | REST runtime boundary invariants |
| `invalid/rest-download-local-mutating-method.json` | REST side-effect invariants |

Examples use fictional components and revisions. They are not component status
records. REST runtime boundary examples cover only shared security and
interoperability invariants; they do not define the component-owned REST input
schemas.
