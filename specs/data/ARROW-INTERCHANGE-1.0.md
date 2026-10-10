# Plenora Arrow Interchange Contract 1.0

Status: normative

Contract identifier: `plenora-arrow-interchange-v1`

## 1. Applicability

This contract applies when a public operation accepts or returns tabular data
as Arrow, Arrow IPC or PyArrow objects. It governs the exchanged artifact, not
the component's internal memory representation.

The registered content types are:

- `application/vnd.apache.arrow.stream`;
- `application/vnd.apache.arrow.file`.

An operation descriptor MUST declare the content types it accepts and produces.

## 2. Schema contract version

**ARROW-001** — A Plenora Arrow schema crossing a component boundary MUST carry
`plenora.contract.version` in schema metadata.

**ARROW-002** — A consumer MUST fail closed on a contract version newer than it
supports. It MUST NOT guess the meaning of versioned metadata.

## 3. Stable field identity

**ARROW-003** — A field whose identity must survive rename, projection or
round-trip MUST carry `plenora.field_id` as a non-negative decimal identifier.

**ARROW-004** — A component MUST preserve field identifiers for unchanged
logical fields. Newly derived fields receive new identifiers according to the
operation-specific output contract.

Field identifiers are public data identity. They do not reveal or constrain
internal struct fields.

## 4. Geometry identity

The shared geometry namespace includes:

- `ARROW:extension:name`;
- `plenora.geometry.encoding`;
- `plenora.geometry.dimensions`;
- `plenora.geometry.spatial_semantics`;
- `plenora.geometry.srid`;
- `plenora.geometry.precision`;
- `plenora.geometry.types`;
- `plenora.geometry.types_declaration`;
- `plenora.geometry.crs_resolution`;
- `plenora.geometry.crs_id`;
- `plenora.geometry.crs_definition`;
- `plenora.geometry.crs_definition_format`;
- `plenora.geometry.axis_order`.

The closed values, canonical ordering and dependent-field rules are normative
in [Arrow Metadata Vocabulary 1.0](ARROW-VOCABULARY-1.0.md).

**ARROW-005** — Canonical WKB geometry fields MUST use the GeoArrow extension
name `geoarrow.wkb` and a compatible Arrow binary storage type.

**ARROW-006** — Geometry metadata MUST be internally consistent. A component
MUST reject contradictory extension name, encoding, dimensions or CRS state
instead of selecting one interpretation silently.

**ARROW-007** — A component MUST distinguish resolved, declared-but-unresolved
and absent CRS information. It MUST NOT synthesize a resolved CRS from an
unverified numeric hint.

**ARROW-008** — Axis order and CRS definition format, when present, are part of
the public meaning and MUST survive a lossless pass-through.

## 5. Native metadata

Provider-specific public metadata MAY use a namespaced key such as
`plenora.postgres.*`, `plenora.sqlserver.*`, `plenora.mysql.*` or
`plenora.geometry.native.*`.

**ARROW-009** — A generic consumer MUST NOT require provider-specific metadata
to interpret the common Arrow and geometry contract.

**ARROW-010** — An operation that claims lossless pass-through MUST preserve
unknown metadata. An operation that intentionally normalizes or drops metadata
MUST report that behavior in its output contract or fidelity result.

## 6. Streaming

**ARROW-011** — An operation advertised with Arrow stream output MUST allow the
consumer to process batches without first materializing the complete result,
unless the operation descriptor explicitly declares bounded materialization.

**ARROW-012** — All batches in one stream MUST conform to the declared schema.
Schema change requires a new stream or an operation-specific versioned protocol.

This contract does not prescribe batch size, allocator, channel, iterator or
async runtime.

## 7. Surface equivalence

A Python SDK MAY expose a PyArrow object, a Rust API MAY expose Arrow-native
types and a runtime surface MAY transfer IPC bytes. They are equivalent only
when schema, field identity, metadata and row meaning are preserved.

## 8. Domain-owned schemas

This contract does not define the columns of every operation. Each
operation-specific contract owns its logical input and output schema. This
document defines only the common interchange rules needed to move that schema
between Plenora components.

Reusable valid and invalid fixtures are defined by
[Arrow Metadata Vocabulary 1.0](ARROW-VOCABULARY-1.0.md).

## 9. Rejecting Arrow input

The same invalid input reaches every component of a pipeline. These rules fix
how each of them reports it, so that a consumer of the error can act on the
category without knowing which component found the defect.

**ARROW-013** — A component that rejects an Arrow input for one of these
classes reports the category the table gives, on every surface:

| class | examples | category |
|---|---|---|
| contract version absent or not a decimal integer | schema metadata without `plenora.contract.version`; the value `01` or `1.0` | `schema` |
| contract version not supported | `2` (ARROW-002, ERR-002) | `unsupported` |
| vocabulary not well-formed | a required key absent; a value outside its closed set or grammar; geometry keys on a field without `geoarrow.wkb`; `geoarrow.wkb` on a storage other than binary; types out of canonical order; a repeated field identifier | `schema` |
| CRS contradictory or unusable | the CRS rules of [Arrow Vocabulary 1.0](ARROW-VOCABULARY-1.0.md) section 4; a contradictory definition (VOC-005); a CRS the operation must compute with and cannot verify or does not know (VOC-006, VOC-015) | `crs` |
| type or shape the component does not support | an Arrow type it cannot represent; several geometry fields (VOC-012); a set of geometry types its target cannot store (VOC-010); `geography` semantics for a planar operation | `unsupported` |
| schema incompatible with the operation | a field the operation requires is absent; a field type differs from the target's and the operation's declared mapping does not convert it; a nullable field into a non-nullable target, when the schema decides it | `schema` |
| invalid value | malformed WKB or EWKB, a value outside the declared types or dimensions (VOC-011); the SRID flag under `wkb` (VOC-008); a value the target type cannot hold, such as an overflow or a null into a non-nullable target | `data_mapping` |
| value contradicting the CRS | an EWKB SRID different from the field's, or an SRID on a field that declares none (VOC-009) | `crs` |

These classes are never reported as `invalid_plan` or
`invalid_configuration`, which describe the request, nor as `resource_limit`,
`io`, `execution` or `internal`, whatever internal layer detected them. A
class not in the table keeps the most precise category of ERR-001.

**ARROW-014** — When an input shows defects of several classes, the component
reports the first in this order: contract version; vocabulary; CRS; support;
operation schema; values. Values are checked in row order, and fields in
field order within a row; for one geometry value, well-formedness, then the
SRID, then types and dimensions. The two value classes, invalid value and
value contradicting the CRS, are found only in this last step, whatever
their category: a defect of row 1 is reported before any defect of row 2. A component does not interpret any metadata
of a contract version it does not support.

**ARROW-015** — A rejection of every class except the two value classes is
decided from the schema alone and is reported before any effect, with
`remote_effect: none` and `retry.kind: never`. Its phase is `validate`, or
`connect` or `probe` when deciding it required reading the target, such as
the definition of an existing table (ERR-003). A value class is reported
with the phase in which the component met the value (ERR-003): `read` for a
component that reads it from its input, `write` for one that writes it to a
target; the remote effect is the one ERR-004 requires (`none` when nothing
was published or committed, `rolled_back` when a started write was proven
undone) and `retry.kind: never`, unless an unproven effect requires
`quarantine` or `requires_recovery` (ERR-006). The CLI projects every class
to exit code 3 (CLI 2.0 section 8); a Python SDK raises the exception of the
category (Python SDK 1.0 section 6).

**ARROW-016** — The invalid vectors of
[`vectors/arrow-data-v1`](../../vectors/arrow-data-v1/) state the category of
their class and cite the rules that decide it; the validator derives the
category with the order of ARROW-014. The classes that depend on the
operation or on the component's support (support, operation schema) are
exercised by the interoperability vectors of
[Composition 1.0](../composition/COMPOSITION-1.0.md), which name the
operation.
