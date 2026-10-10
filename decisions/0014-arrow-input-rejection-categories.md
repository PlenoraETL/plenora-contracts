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
`resource_limit` (exit code 4), an EWKB SRID mismatch included. ERR-001 asks
for "the most precise value", but nothing says which class of defect each
category covers, nor what a component reports when an input has several
defects; a pipeline whose orchestrator acts on the category (retry, quarantine,
fix the schema) behaves differently depending on which component met the
input first.

## Compatibility test

As in [decision 0010](0010-runtime-rejection-and-identity.md): every category
fixed here is admitted by `error-v1` for the rejection, so a conforming
consumer of errors already interprets it. The rules make the producers that
chose another value non-conforming, which is the adoption impact below. No
input that 1.0 accepts is rejected: the classes are defects that 1.0 already
requires to be rejected (ARROW-001, ARROW-002, ARROW-006, the vocabulary,
decision 0013).

## Decision

Arrow Interchange 1.0 gains section 9 (ARROW-013 to ARROW-016) and Typed
Errors 1.0 points to it:

- **ARROW-013**, one category per class: contract version absent or not a
  decimal, `schema`; version not supported, `unsupported`; vocabulary not
  well-formed, `schema`; CRS contradictory or unusable, `crs`; type or shape
  the component does not support, `unsupported`; schema incompatible with
  the operation, `schema`; invalid value, `data_mapping`. Never
  `invalid_plan`, `invalid_configuration`, `resource_limit`, `io`,
  `execution` or `internal`.
- **ARROW-014**, the order when several defects coexist: version,
  vocabulary, CRS, support, operation schema, values (row order, field
  order, then well-formedness, SRID, types and dimensions of one value).
- **ARROW-015**, the other axes: a schema-level class is reported before any
  effect, `remote_effect: none`, `retry.kind: never`, phase `validate` (or
  `connect`/`probe` when it needed the target); an invalid value with the
  phase where it was met and the remote effect of ERR-004.
- **ARROW-016**, the vectors.

The four classes the request names map as follows: invalid geometry,
`data_mapping` (VOC-011); unknown CRS, `crs` (VOC-015); unsupported type,
`unsupported`; incompatible schema, `schema`.

Nine vectors in `vectors/arrow-data-v1`: the three contract-version classes,
`geoarrow.wkb` on `utf8`, an unknown CRS identifier for a computing consumer
and four precedence vectors with two defects each. The validator derives each
category with the order of ARROW-014. The support and operation-schema
classes depend on the operation and the component; they are exercised by the
interoperability vectors, which name the operation.

### Why `schema` for an absent version and `unsupported` for version 2

An absent or malformed version is a defect of the schema's own metadata: the
producer omitted a required key. A well-formed version that the consumer
does not support is the case ERR-002 names. `data_mapping` describes values,
and `invalid_plan` the request.

## Alternatives

- **Leave the category to each component.** The suite's divergence is the
  result.
- **One category for every Arrow defect (`schema`).** Simpler, but it hides
  the distinction an orchestrator acts on: an unsupported version calls for
  another component version, a CRS defect for metadata repair, an invalid
  value for data repair.
- **A new error contract version with an Arrow-specific category.** The
  existing categories already separate the classes.

## Change statement

- **Consumers affected:** orchestrators and callers that act on the category
  of an Arrow rejection; the interoperability suite.
- **Before:** the category of each class left to the component.
- **After:** ARROW-013 to ARROW-016.
- **Compatible:** yes, by the test above.
- **Schemas, examples and profiles:** nine vectors; prose in Arrow
  Interchange 1.0 and Typed Errors 1.0. No schema, catalog, binding or
  published vector changes.
- **Adoption impact:**
  - IO-tools: report Arrow input defects with the table's category instead
    of `invalid_plan` (exit 3 instead of 2).
  - database-tools: absent version as `schema`, not `data_mapping`; batch
    validation failures with their class (`crs`, `data_mapping`,
    `schema`), never `resource_limit` unless a resource bound was reached.
  - data-tools: already reports the three suite vectors as the table says;
    checks its order of checks against ARROW-014.
