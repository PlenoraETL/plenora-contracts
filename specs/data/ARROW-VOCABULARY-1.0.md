# Plenora Arrow Metadata Vocabulary 1.0

Status: normative

Contract identifier: `plenora-arrow-metadata-v1`

This document closes the wire vocabulary used by Arrow Interchange 1.0. Values
are UTF-8 strings in Arrow schema or field metadata. Matching is case-sensitive.

## 1. Schema metadata

| Key | Required value | Rule |
|---|---|---|
| `plenora.contract.version` | `1` | Required on every cross-component schema. Unknown versions fail closed. |

## 2. Common field identity

| Key | Values | Rule |
|---|---|---|
| `plenora.field_id` | non-negative decimal integer | Unique within a schema and preserved for an unchanged logical field. |

Field identity is independent of field name and ordinal position.

## 3. Geometry field vocabulary

| Key | Closed values or grammar |
|---|---|
| `ARROW:extension:name` | `geoarrow.wkb` |
| `plenora.geometry.encoding` | `wkb`, `ewkb` |
| `plenora.geometry.dimensions` | `xy`, `xyz`, `xym`, `xyzm`, `unknown` |
| `plenora.geometry.spatial_semantics` | `geometry`, `geography` |
| `plenora.geometry.precision` | `float64`, `float32`, `native` |
| `plenora.geometry.srid` | signed 32-bit decimal integer |
| `plenora.geometry.types_declaration` | `exact`, `mixed`, `unresolved` |
| `plenora.geometry.types` | comma-separated canonical geometry types |
| `plenora.geometry.crs_resolution` | `resolved`, `declared_unresolved`, `missing` |
| `plenora.geometry.crs_id` | non-empty authority identifier such as `EPSG:4326` |
| `plenora.geometry.crs_definition` | non-empty WKT, WKT2 or PROJJSON text |
| `plenora.geometry.crs_definition_format` | `wkt`, `wkt2`, `projjson` |
| `plenora.geometry.axis_order` | `lon_lat`, `lat_lon`, `easting_northing`, `northing_easting`, `other`, `unknown` |

The canonical geometry type order is:

`point`, `linestring`, `polygon`, `multipoint`, `multilinestring`,
`multipolygon`, `geometrycollection`, `circularstring`, `compoundcurve`,
`curvepolygon`, `multicurve`, `multisurface`, `polyhedralsurface`, `tin`,
`triangle`, `unknown`.

When `plenora.geometry.types` contains multiple values they MUST be unique and
in canonical order.

## 4. Dependent-field rules

- A field with `ARROW:extension:name=geoarrow.wkb` uses Arrow `binary` or
  `large_binary` storage and declares field id, encoding, dimensions, spatial
  semantics, precision, type declaration and CRS resolution.
- `types_declaration=exact` requires a non-empty type list.
- `types_declaration=unresolved` forbids a type list.
- `crs_resolution=resolved` requires a CRS id or definition and requires axis
  order.
- `crs_resolution=declared_unresolved` requires a CRS id or definition and
  requires axis order.
- `crs_resolution=missing` forbids CRS id, definition, definition format and
  axis order.
- A CRS definition and its definition format are either both present or both
  absent.
- Geometry keys on a field without the `geoarrow.wkb` extension are invalid.

Contradictory metadata fails with category `schema` or `crs`; consumers MUST NOT
choose one of the conflicting values.

## 5. Native metadata

Public native geometry metadata uses the prefix
`plenora.geometry.native.`. Provider metadata may use a reviewed provider
prefix such as `plenora.postgres.` or `plenora.sqlserver.`.

Generic consumers do not need native keys to understand the common contract.
Lossless pass-through preserves unknown metadata byte-for-byte. A normalizing
operation reports any intentional loss through its public fidelity result.

## 6. Conformance vectors

The vectors in [`vectors/arrow-v1`](../../vectors/arrow-v1/) are abstract Arrow
schema fixtures. A component test constructs its native Arrow schema from the
fixture, serializes it through its public boundary and checks the expected
acceptance or rejection. The vector shape is defined by
[`arrow-metadata-vector-v1.schema.json`](../../schemas/arrow-metadata-vector-v1.schema.json).
