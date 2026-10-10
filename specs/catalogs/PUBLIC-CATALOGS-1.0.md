# Plenora Public Catalogs Contract 1.0

Status: normative

Contract identifier: `plenora-public-catalog-v1`

The machine shape is defined by
[`public-catalog-v1.schema.json`](../../schemas/public-catalog-v1.schema.json).
The target catalogs are in [`catalogs`](../../catalogs/), named
`<component>-v<N>.json`. The highest version of a component is its current
target; an earlier version stays as an available identity when a later one
changes operations incompatibly.

## 1. Purpose

A public catalog is the reviewed target boundary of one component. It states
which functions the Plenora ecosystem may depend on and how they are named,
versioned and represented. It does not claim that a particular released
artifact already conforms.

An artifact reports its actual surface through Capability Discovery 2.0. Its
capability document MUST be a truthful implementation of the applicable target
catalog: it may narrow conditional or extension entries, but it may not silently
rename a required operation or change its contracts.

## 2. Requirement levels

- `required`: every conforming artifact containing the applicable surface
  exposes the operation;
- `conditional`: the operation is required when the component publishes that
  function or surface;
- `extension`: the namespace and semantics are standardized, but an artifact
  may omit the extension entirely.

`storage-tools-v1.json` is normative after ratification of its atomicity,
publication, pagination, integrity and artifact-reference semantics. Normative
catalog status fixes identities and testable boundaries; it is not a release
or artifact conformance claim. Storage artifact capabilities may remain
`experimental` until a qualified release exists.

## 3. Operation identity

The pair `(id, version)` is the semantic operation identity. The component
release version, CLI protocol version, runtime binding version and operation
version are independent.

Changing accepted input, output meaning, side-effect classification or control
semantics incompatibly requires a new operation version and new immutable
contract identifiers. Surface-specific convenience spelling does not create a
new operation.

## 4. Payload descriptors

Every input and output declares:

- an operation-specific contract identifier;
- all accepted or produced content types;
- zero or more shared interchange contracts.

The operation-specific identifier owns the domain meaning. For example,
`plenora-database-read-result-v1` identifies the result of `database.read`,
while `plenora-arrow-interchange-v1` states that the tabular payload can cross a
component boundary without translation.

A component-owned schema remains component-owned when no other component needs
its fields. The stable identifier still appears here so callers can reject the
wrong payload before execution. This repository owns a schema when two or more
components must interpret the same fields.

## 5. Surfaces and released capabilities

An operation's `surfaces` array is the target binding set. An adopter MUST:

1. expose the same operation identity on every target surface it implements;
2. publish only the surfaces actually present in its capability document;
3. preserve validation, defaults, output meaning and error axes across those
   surfaces;
4. record temporary deviations in its adoption manifest rather than editing
   the common catalog to match an incomplete implementation.

**CAT-001** — An operation's `surfaces` and a catalog's `target_surfaces`
state the target, never availability. A consumer selects an operation and a
surface only from the capability document of the artifact it calls (CAP-004,
CAP-007, CAP-008, SURF-016) and MUST NOT invoke an operation on a surface that
this document does not list, whatever the catalog lists. A surface that the
catalog lists and an artifact's capability document does not is **planned**
for that artifact: the catalog and the binding maps name the spelling it will
have, not a surface that exists.

**CAT-002** — A published surface is never removed from a catalog or a
binding map (COMPATIBILITY.md), and neither carries a "planned" marker:
availability belongs to an artifact, and only capability discovery reports
it. An artifact that does not implement a target surface omits it from its
capability document. When that surface's target applicability is `required`,
the artifact also records a deviation in its adoption manifest; a
`conditional` surface that an artifact does not implement needs none.

**CAT-003** — A surface that a profile declares intentionally absent for an
operation, with its reason, is never added to that operation identity: a
binding on it needs a new operation version whose contract removes the
reason. The validator checks every catalog version and binding map against
the absences the profiles declare (DB-ABS-001, DB-ABS-002, DT-ABS-001,
DT-ABS-002), and that each profile states the rule with its reason: the
bold rule identifier followed, in the same paragraph, by a non-empty
sentence that ends with a period. It
checks the coherence of the documents, not what any artifact exposes:
availability is reported only by capability discovery (CAP-004, CAP-008).

The exact CLI, Python and runtime spellings are defined by
[Surface Bindings 1.0](../surfaces/SURFACE-BINDINGS-1.0.md).

## 6. Data kernel registry

`data.run` is the externally invocable plan operation. The table and geo
kernels selected inside a plan are not 146 artificial CLI commands. Their
stable identifiers and versions live in the registry the catalog's
`data.catalog` operation names: [`data-kernels-v2.json`](../../catalogs/data-kernels-v2.json)
for the current data-tools catalog, where a kernel's `version` is the version
of its observable semantics, and
[`data-kernels-v1.json`](../../catalogs/data-kernels-v1.json) for version 1.
Their machine shape is
[`operation-registry-v1.schema.json`](../../schemas/operation-registry-v1.schema.json).

Capability discovery for `data.catalog` MUST report only kernels present in the
answering artifact. Kernel parameters and logical result shape are described by
the component-owned kernel descriptor returned by `data.catalog`; the stable
kernel identity and version MUST agree with the common registry. How the
version 2 result reports a registered kernel the artifact cannot execute is
defined by the data-tools profile version 2 (DT-001).

## 7. External verification

Conformance tests treat the catalogs as black-box expectations. They verify
discovery, successful invocation, rejection of wrong versions and contracts,
typed failures and side-effect reporting. They MUST NOT inspect crate modules,
private classes, driver registries or executor topology.
