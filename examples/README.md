# Examples

Files under `valid` must validate. Files under `invalid` are deliberate
counterexamples and must fail against the indicated schema.

| Example | Schema |
|---|---|
| `valid/cli-success.json` | `cli-envelope-v2.schema.json` |
| `valid/cli-error.json` | `cli-envelope-v2.schema.json` |
| `valid/capabilities.json` | `capabilities-v1.schema.json` |
| `valid/capabilities-v2.json` | `capabilities-v2.schema.json` |
| `valid/row-diagnostics.json` | `row-diagnostics-v1.schema.json` |
| `valid/adoption-manifest.json` | `adoption-manifest-v1.schema.json` |
| `valid/adoption-manifest-v2.json` | `adoption-manifest-v2.schema.json` |
| `invalid/cli-missing-protocol.json` | `cli-envelope-v2.schema.json` |
| `invalid/error-after-missing-delay.json` | `error-v1.schema.json` |
| `invalid/capabilities-unavailable-without-reason.json` | `capabilities-v1.schema.json` |
| `invalid/capabilities-v2-unavailable-without-reason.json` | `capabilities-v2.schema.json` |
| `invalid/row-diagnostics-redacted-value.json` | `row-diagnostics-v1.schema.json` |
| `invalid/adoption-floating-revision.json` | `adoption-manifest-v1.schema.json` |
| `invalid/adoption-v2-floating-revision.json` | `adoption-manifest-v2.schema.json` |

Examples use fictional components and revisions. They are not component status
records.
