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
