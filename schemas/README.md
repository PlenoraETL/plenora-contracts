# Schemas

These schemas are normative and use JSON Schema draft 2020-12.

| Schema | Purpose |
|---|---|
| `cli-envelope-v2.schema.json` | Common success and error envelope |
| `error-v1.schema.json` | Shared typed error axes |
| `capabilities-v1.schema.json` | Capability result carried by a success envelope |
| `adoption-manifest-v1.schema.json` | Component-owned declaration of adoption |

Schema identifiers are immutable. Modify a schema in place only for a change
that cannot alter whether an existing instance validates. Otherwise add a new
version.
