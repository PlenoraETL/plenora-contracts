# Public profile: database-tools

Profile identifier: `plenora-database-tools-profile-v1`

Normative target catalog:
[`database-tools-v1.json`](../catalogs/database-tools-v1.json)

## Applicable contracts

- [Public Surfaces 1.0](../specs/surfaces/PUBLIC-SURFACES-1.0.md)
- [Capability Discovery 2.0](../specs/capabilities/CAPABILITY-DISCOVERY-2.0.md)
- [Typed Errors 1.0](../specs/errors/ERRORS-1.0.md)
- [Public Security 1.0](../specs/security/PUBLIC-SECURITY-1.0.md)
- [Arrow Interchange 1.0](../specs/data/ARROW-INTERCHANGE-1.0.md)
- [Row Diagnostics 1.0](../specs/diagnostics/ROW-DIAGNOSTICS-1.0.md)
- [CLI 2.0](../specs/cli/CLI-2.0.md)
- [Python SDK 1.0](../specs/sdk/PYTHON-SDK-1.0.md)
- [Runtime Binding 1.0](../specs/runtime/RUNTIME-BINDING-1.0.md), when exposed
- [Surface Bindings 1.0](../specs/surfaces/SURFACE-BINDINGS-1.0.md)
- [Composition 1.0](../specs/composition/COMPOSITION-1.0.md)

## Public purpose

The component exposes discovery, reading, writing and query-oriented database
functionality without requiring a consumer to understand provider internals.

This profile and its operation catalog are normative targets. That status fixes
the expected public boundary; it does not claim that any component release
conforms. An artifact claims conformance only through immutable component-owned
operation and capability-attribute schemas plus the adoption manifest described
in [`ADOPTION.md`](../ADOPTION.md).

## Required operation families

The stable public catalog includes these baseline identifiers:

- `database.test_connection`;
- `database.list_catalogs`;
- `database.list_schemas`;
- `database.list_objects`;
- `database.describe_object`;
- `database.read`;
- `database.write`.

Public query and transaction entry points MUST also be discoverable under the
`database.query` and `database.transaction.*` families when the released
artifact exposes them.

`database.query` is read-only and has no remote mutation effect. Insert,
update, delete and upsert entry points bind to `database.execute` or
`database.write` and conservatively declare remote side effects.

Session constructors such as `connect` and `aconnect` establish persistent
sessions. They do not implement `database.test_connection`, which has dedicated
sync and async entry points and returns a bounded redacted verification result.

No `arcgis.*` operation is selected by this profile. ArcGIS operations,
bindings and composition edges remain absent until ownership is ratified as
REST operations, a dedicated component or another explicit public extension.

## Component-owned contracts

`database-tools` owns and immutably versions every
`plenora-database-*-v1` input or output contract referenced by the catalog,
including `plenora-database-capability-attributes-v1`. Their normative schemas
and operation specifications live in the component repository; this repository
owns their stable identities and cross-surface semantics.

The capability-attributes contract describes the selected provider and the
write modes actually available for that provider. Consumers MUST interpret
`write_modes` only under that contract. A mode unavailable for a provider is
omitted rather than accepted and failed later; the common catalog does not make
every mode universally available.

## Public surfaces

- Rust API: required.
- CLI: required and governed by CLI 2.0.
- Python SDK: required and governed by Python SDK 1.0.
- Runtime: required for every database operation selected for orchestration.

The same operation version exposed on multiple surfaces has equivalent input
validation, results, error axes and remote-effect semantics.

## Interchange

`database.read` returns tabular results through the Arrow Interchange 1.0
contract when a tabular surface is selected. `database.write` accepts Arrow
under that contract when its descriptor advertises Arrow input.

Read or write failures that expose row-level evidence use
`plenora-row-diagnostics-v1`.

## External safety

Connection selection is exposed as a reference or protected configuration
boundary. Capability documents, errors and ordinary results MUST NOT contain
credentials, DSNs, bound statements or source rows.

Writes and transaction operations declare remote side effects, supported
execution controls and possible ambiguous outcomes in their public
specification.

## Not specified here

This profile does not prescribe provider traits, drivers, pools, SQL rendering,
transaction implementation or Arrow conversion code.
