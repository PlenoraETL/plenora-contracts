# 0014: One category for each class of invalid Arrow input

Status: accepted

Date: 2026-10-10

## Context

The interoperability suite gave the same negative vectors to IO-tools,
data-tools and database-tools and compared the error axes:

| vector | data-tools | database-tools | IO-tools |
|---|---|---|---|
| `plenora.contract.version = 2` | `unsupported` | `unsupported` | `invalid_plan` |
| no `plenora.contract.version` | `schema` | `data_mapping` | `invalid_plan` |
| contradictory CRS | `crs` | `crs` | `invalid_plan` |

database-tools also reports every failure of its batch validation as
`resource_limit`. ERR-001 asks for "the most precise value", but nothing says
which class of defect each category covers, nor what a component reports
when an input has several defects.

## Where the rules live

The first version wrote them into Arrow Interchange 1.0 as clarifications.
An independent reading (Codex) showed two problems: applied to every
component, they would turn into rejections inputs that a published profile
accepts (DT-ARROW-003), and they depend on the geometry rules that
[decision 0013](0013-geometry-vocabulary-semantics.md) moved to an opt-in
contract. They are therefore section 10 of **Arrow Geometry Semantics 1.0**,
for the components that claim it; Arrow Interchange 1.0 and Typed Errors 1.0
keep their published meaning, with informative pointers.

## Decision

- **REJ-001**, one category per class, and the classes are disjoint:
  contract version absent or malformed `schema`, not supported
  `unsupported`; vocabulary `schema`; every dependency that involves the CRS
  keys, an absent CRS key included, `crs`; support `unsupported`; operation
  schema `schema`; invalid value `data_mapping`; value contradicting the CRS
  `crs`. Never `invalid_plan`, `invalid_configuration`, `resource_limit`,
  `io`, `execution` or `internal`.
- **REJ-002**, one order that includes the operation: version, vocabulary,
  CRS (a CRS the operation cannot use included), support, operation schema,
  values in row and field order.
- **REJ-003**, the other axes: schema-level classes before any effect,
  `none`, `never`, phase `validate` (or `connect`/`probe`); value classes in
  the phase where the value is met, `none` or `rolled_back` after a proven
  rollback of a provisional write (GEO-018).
- **REJ-004**, the vectors.
- The rules classify the rejections that are due; they never revoke an
  acceptance a profile states (GEO-000).

Nine vectors in `vectors/arrow-data-v1`: the three contract-version classes,
`geoarrow.wkb` on `utf8`, an unknown CRS identifier for a computing operation
and four precedence vectors with two defects each.

### Second readings

An EWKB SRID mismatch can only be found while reading values, possibly after
provisional writes: it is a value class with category `crs`. The vocabulary
and CRS classes overlapped on an absent CRS key (a resolved CRS without
`axis_order`): the CRS class now owns every CRS key. "Before any effect"
meant two things in two rules: it now means before a publication or a
commit (GEO-018).

### Why `schema` for an absent version and `unsupported` for version 2

An absent or malformed version is a defect of the schema's own metadata. A
well-formed version that the component does not support is the case ERR-002
names.

## Alternatives

- **Leave the category to each component.** The suite's divergence is the
  result.
- **One category for every Arrow defect.** It hides the distinction an
  orchestrator acts on.
- **The rules in Arrow Interchange 1.0.** They would restrict what v1.1.0
  admitted.

## Change statement

- **Consumers affected:** orchestrators and callers of components that claim
  the contract.
- **Before:** the category of each class left to the component.
- **After:** REJ-001 to REJ-004 in Arrow Geometry Semantics 1.0.
- **Compatible:** yes: part of a new opt-in contract.
- **Schemas, examples and profiles:** nine vectors; section 10 of the new
  specification; informative pointers in Arrow Interchange 1.0 and Typed
  Errors 1.0.
- **Adoption impact**, for a component that claims the contract:
  - IO-tools: the table's categories instead of `invalid_plan` (exit 3
    instead of 2).
  - database-tools: absent version `schema`; batch validation failures with
    their class, never `resource_limit` unless a resource bound was reached.
  - data-tools: already consistent with the three suite vectors; its order
    of checks against REJ-002, keeping DT-ARROW-003.
