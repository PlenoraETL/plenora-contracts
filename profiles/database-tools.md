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
- Runtime: conditional. An artifact that publishes the runtime surface
  follows Runtime Binding 1.0 for every operation it exposes there; an
  artifact without it omits `runtime` from its capability document, and the
  catalog's runtime entries are planned for it (CAT-001).

The same operation version exposed on multiple surfaces has equivalent input
validation, results, error axes and remote-effect semantics.

## Surfaces intentionally absent

These gaps in the catalog are decisions, not missing work. Public Catalogs
1.0 CAT-003 keeps them: none of these surfaces is ever added to these
operation identities.

**DB-ABS-001** — `database.transaction.begin`, `database.transaction.commit`,
`database.transaction.rollback` and `database.transaction.savepoint` are bound
to the Rust API and the Python SDK only.

- Not to the CLI: a transaction handle does not survive the process that
  opened it, and CLI 2.0 answers one invocation with one envelope. Spreading
  a transaction over several invocations needs a session process that holds
  the connection between them, which no shared contract defines.
- Not to the runtime: Runtime Binding 1.0 messages are independent requests
  that a transport may route to different workers. A transaction spread over
  several messages needs session affinity, a lease and the recovery of a
  transaction whose owner disappeared, which no shared contract defines.

A process-level caller that needs atomicity uses an operation whose single
invocation is the transaction, such as `database.write`.

**DB-ABS-002** — `database.execute` is not bound to the runtime. It runs a
statement the caller supplies, with remote effects the component cannot
characterize, and its controls accept no idempotency key. Runtime Binding 1.0
does not promise at-most-once delivery: a transport may deliver a request
again after a lost acknowledgement, and the shared defense against a second
execution is an idempotency key (SURF-012, RT-022), which this operation does
not accept. A runtime binding needs a new operation version that accepts the
key and states how a repeated key is recognized.

**DB-ABS-003** — `plenora-database-transaction-handle-v1` and
`plenora-database-savepoint-input-v1` are logical shapes. The Rust API and the
Python SDK realize them as native handle objects (SURF-009); no surface
serializes them, and the `application/json` content type the catalog declares
names the representation a serialized surface would use, not one that
exists. A consumer MUST NOT expect, persist or exchange them as JSON
documents; a handle is valid only in the process and session that created it.

## Content types on the runtime

Runtime Binding 1.0 carries one payload per request and per result, and lets
a caller choose neither among the content types an operation declares.

**DB-RT-001** — On the runtime, the result of `database.query` version 1 is
`application/json`, one of the two content types the catalog declares; its
input contract is closed and has no member to ask for Arrow. That JSON is the
complete `plenora-database-query-result-v1`, with the same meaning as the
Arrow form on the other surfaces (Arrow Interchange 1.0 section 7): a summary
without the rows is not the operation's result (RT-008). Arrow on the runtime
needs a new version of the operation whose input names an artifact sink, as
`data.run` version 3 does.

**DB-RT-003** — A query result larger than the bound of the runtime surface
fails with `resource_limit` under RT-024, before any row is returned; it is
never cut to the bound. `database.query` is read-only, so the remote effect
is `none`. database-tools declares its bound for the runtime surface in its
capability document, under its component-owned
`plenora-database-capability-attributes-v1`, and in its adoption manifest
while that contract has no member for it; the bound of the transport is the
transport's (RT-024). The vectors `database-query-result-limit-error.json`
and `database-query-transport-limit-error.json` show both.

**DB-RT-002** — On the runtime, the payload of `database.write` is
`application/json` (`plenora-database-write-input-v1`), and the rows travel
as an artifact reference that the application resolves (RT-013, RT-015); the
artifact's content type is one of the two Arrow content types the catalog
declares. The Arrow content types are artifact types on this surface, never
payload types.

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
