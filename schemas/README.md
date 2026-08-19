# Schemas

These schemas are normative and use JSON Schema draft 2020-12.

| Schema | Purpose |
|---|---|
| `cli-envelope-v2.schema.json` | Common success and error envelope |
| `error-v1.schema.json` | Shared typed error axes |
| `capabilities-v1.schema.json` | Capability result carried by a success envelope |
| `capabilities-v2.schema.json` | Public interfaces and operation-level discovery |
| `row-diagnostics-v1.schema.json` | Bounded row-level evidence shared by data, database and I/O boundaries |
| `adoption-manifest-v1.schema.json` | Component-owned declaration of adoption |
| `adoption-manifest-v2.schema.json` | Adoption across Rust, CLI, Python and runtime surfaces |

Schema identifiers are immutable. Modify a schema in place only for a change
that cannot alter whether an existing instance validates. Otherwise add a new
version.

Manifest v1 is retained for the historical CLI/SDK-only scope. New component
adoption uses manifest v2.
