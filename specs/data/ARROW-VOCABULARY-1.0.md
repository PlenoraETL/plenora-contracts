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

Each grammar matches the whole value: a decimal integer, an SRID or a
contract version followed by a line feed or any other character is not
well-formed. `plenora.geometry.crs_id` is `AUTHORITY:CODE`, an authority name
starting with a letter (letters, digits, `_`, `.`, `-`), a colon and a code
without spaces or colons. `plenora.geometry.types`, when present, is not
empty. The geometry keys are exactly those of the table above: any other key
beginning with `plenora.geometry.` is not well-formed, except those under
`plenora.geometry.native.` (section 5).

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

Section 7 decides what `axis_order` means. A vector of this directory states
only that its metadata is well-formed: `resolved-point.json` declares
`lat_lon` for `EPSG:4326`, which under VOC-001 says that its values store
latitude first, a valid but uncommon field.

## 7. Coordinate axis order

**VOC-001** — `plenora.geometry.axis_order` states the order of the first two
ordinates of every coordinate **as stored** in the WKB or EWKB values of the
field:

- `lon_lat`: longitude, then latitude;
- `lat_lon`: latitude, then longitude;
- `easting_northing`: easting, then northing;
- `northing_easting`: northing, then easting;
- `other`: a stored order that none of the four values describes;
- `unknown`: an order the producer could not establish.

It is not the axis order with which the CRS authority registers the CRS.
`EPSG:4326` registers latitude first; a field of `EPSG:4326` whose values store
longitude first declares `lon_lat`. Third and fourth ordinates (Z, M) are not
affected.

**VOC-002** — The producer of the field declares it: the component that puts
the values into the Arrow field, from the coordinate convention of the source
or of the computation that produced those values. It MUST NOT derive the value
from the axis order of the CRS registry alone. When the specification of a
source format fixes the stored order, that order is the declaration; for
example GeoPackage and GeoParquet store easting or longitude first whatever
the CRS, and GeoJSON (RFC 7946) stores longitude first. A producer that cannot
establish the stored order declares `unknown`. A pass-through keeps the value
(ARROW-008); an operation that exchanges ordinates declares the order it
produces.

**VOC-003** — WKB bytes do not show their axis order: both orders are
well-formed. A producer's declaration is verified through its public boundary,
by reading a source whose stored order and coordinate values are known and
checking both the declared order and the decoded ordinates. The data vectors
(section 12) use coordinates whose two ordinates cannot be exchanged without
leaving the domain of the declared axis, such as a longitude whose magnitude
exceeds 90 degrees, so that an exchanged declaration or exchanged ordinates
are detectable.

## 8. CRS identifier and definition

**VOC-004** — When `plenora.geometry.crs_id` is present it is normative: it
identifies the CRS. A `plenora.geometry.crs_definition` next to it describes
the same CRS; it never replaces the identifier, and a consumer never computes
with the definition in place of the CRS the identifier names. A consumer that
only carries the field, or records its CRS identity (writes the identifier or
the SRID to a target), MUST NOT reject the field because it cannot interpret
the definition; VOC-005 still applies to it. A consumer that computes with
the coordinates follows VOC-015. A pass-through preserves both values byte
for byte (ARROW-008).

**VOC-005** — A producer MUST NOT emit a definition that describes a CRS other
than the one `crs_id` names. A consumer MUST read the top-level authority
identifiers of the definition and reject the field with category `crs` when
the definition carries at least one identifier of the authority of `crs_id`
and none of them equals `crs_id`. The top-level identifiers are:

- WKT 2 (`wkt2`): the `ID[...]` elements that are direct children of the
  outermost keyword;
- WKT 1 (`wkt`): the `AUTHORITY[...]` element that is a direct child of the
  outermost keyword;
- PROJJSON (`projjson`): the `id` object or the `ids` array of the root
  object.

Authority names compare ASCII case-insensitively; codes compare as text, a
numeric code written as its decimal integer. Identifiers of another authority
are not compared. A definition that is not well-formed in its declared
`crs_definition_format` is rejected with `crs`: in WKT a bracket closes with
the kind that opened it, and the outermost keyword belongs to the declared
version (`GEOGCS`, `PROJCS`, ... for `wkt`; `GEOGCRS`, `PROJCRS`, `BOUNDCRS`,
... for `wkt2`); PROJJSON is a JSON object without repeated keys. A definition without an
identifier of that authority is not compared lexically; a consumer that
resolves both and establishes that they describe different CRSs rejects the
field with `crs`. In no case does a consumer choose one of the two.

Reading the top-level identifiers needs only the syntax of the three formats
(bracketed keywords with quoted strings and numbers, or JSON), not a CRS
library. Identifiers nested in the definition, such as the `AUTHORITY` of the
`GEOGCS` inside a `PROJCS`, are not top-level: they never satisfy, and never
contradict, this comparison; VOC-015 reads them.

**VOC-015** — A consumer that computes with the coordinates in their CRS
(measures, transforms, reprojects or builds geometry in CRS units) uses the
CRS that `crs_id` names only after verifying the definition next to it, when
there is one:

1. the definition carries a top-level identifier equal to `crs_id`
   (VOC-005);
2. the parts of the definition agree with the CRS that `crs_id` names. The
   consumer compares at least:
   - the CRS kind (geographic or projected) and the identifier of the base
     CRS when the definition names one;
   - the semi-major axis and inverse flattening of the ellipsoid, as exact
     decimal values;
   - the prime meridian;
   - every unit of the definition (of the ellipsoid, of the coordinate
     system, of the parameters), identified by name and conversion factor;
   - for a projected CRS, the conversion method and every parameter value,
     as exact decimal values;
   - the absence of a datum shift (`TOWGS84`, `BOUNDCRS`) that the CRS of
     `crs_id` does not have.

   A component documents any further part it compares.

A definition without that identifier, one whose parts differ, and one whose
parts the consumer cannot decide are not verified: the operation fails with
`crs` before computing, whatever it would compute. An identifier equal to
`crs_id` is not enough by itself: a definition modified under the same
identifier would otherwise pass in silence. Without a definition, the
consumer computes with the CRS that `crs_id` names when it knows it, and
fails with `crs` otherwise.

**VOC-006** — Without `crs_id`, the definition is the identity of the CRS. A
consumer that computes with the coordinates and cannot interpret the
definition completely fails with `crs`; an operation that only passes the
field through carries it unchanged.

## 9. Encodings and SRID

**VOC-007** — Every consumer that declares this vocabulary accepts both
`plenora.geometry.encoding` values on every `geoarrow.wkb` input. An operation
MUST NOT reject a field, or a value, because of which of the two encodings it
uses; a consumer that needs the other encoding converts as VOC-008 and VOC-009
state, without loss.

**VOC-008** — Under `wkb`, values carry no SRID. Dimension flags may use the
ISO form (type code plus 1000, 2000 or 3000) or the extended form (high bits
`0x80000000` for Z and `0x40000000` for M); a value with the SRID flag
`0x20000000` is malformed and fails with `data_mapping`. Every value has the
CRS of the field. A consumer that needs a numeric SRID takes
`plenora.geometry.srid`; without that key it derives the SRID from the CRS
identity only under a mapping it documents, and otherwise fails with `crs`.

**VOC-009** — Under `ewkb`, a value MAY carry an SRID on its outermost
geometry; an SRID flag on a member of a multi-geometry or collection is
malformed and fails with `data_mapping`. A value that carries one
requires the field to declare `plenora.geometry.srid` with the same integer: a
value whose SRID differs from it, or that carries an SRID when the field
declares none, fails with `crs`. A value without SRID has the SRID of the
field. The check binds every consumer that decodes the value, converts it to
`wkb` or writes it to a target that interprets geometry, before any effect;
an operation that carries the bytes unchanged leaves it to the next consumer.
A producer that emits EWKB values with an SRID declares that SRID on the
field.

## 10. Geometry types and several geometry fields

**VOC-010** — With `types_declaration=exact`, `plenora.geometry.types` is the
closed set of the types of the non-null values; it does not assert that every
listed type occurs. With `mixed`, the field admits several types by
declaration, such as an unconstrained database column; a list, when present,
is the closed set, and without a list any type is admitted. `unknown` in a
list admits any type. `unresolved` states nothing. A list of several types, such as `point,polygon`, is valid
under `exact` and `mixed`. A consumer MUST NOT reject such a list as
malformed and MUST NOT select one of its types: a target that cannot store
the declared set rejects the field with `unsupported` before any effect.

**VOC-011** — A consumer that decodes a value rejects it with `data_mapping`
when the value is not well-formed WKB or EWKB, when its type is outside a
declared list (a `multipolygon` is outside `polygon`), or when its dimensions
differ from a declared `dimensions` other than `unknown`. A well-formed value
has a byte order of 0 or 1 in every header, a known type code in either the
ISO form or the extended form (never both, and the SRID flag only with the
extended form), members of the types and dimensions its container admits,
at most 32 levels of nesting and no byte after the geometry; a linestring
has zero or at least two points, a circular string zero or an odd number of
at least three, a linear ring of a polygon or triangle at least four points
with the last equal to the first, and a triangle at most one ring.

**VOC-012** — A schema MAY carry several `geoarrow.wkb` fields. Each declares
its own complete metadata; CRS, encoding and types of different fields are
independent. A consumer that accepts one geometry field per schema rejects a
schema with several with `unsupported` before any effect; it MUST NOT drop a
field, demote it to plain binary or choose one. A component with that limit
SHOULD make it predictable from its discovery results.

## 11. Identity and precision of produced geometry fields

**VOC-013** — A component that produces a geometry field from a source that
carries no field identity, such as a file or a database column, assigns
`plenora.field_id` (section 4): the smallest non-negative integer not already
used in the schema, taking the fields without identity in field order. The
same rule applies to every other field to which it assigns an identity. An
identity carried by the source is preserved (ARROW-004).

**VOC-014** — `plenora.geometry.precision` describes the coordinate values the
WKB carries:

- `float64`: they are the binary64 values in the bytes. This is true of every
  WKB value and is the declaration of a producer that knows nothing more;
- `float32`: every coordinate is exactly representable in binary32 because
  the source stored binary32;
- `native`: the source's own coordinate model, such as a fixed grid or
  decimal storage, produced them; `plenora.geometry.native.*` may describe
  it.

A producer that reads a source declares `float32` or `native` only when the
source establishes it, and `float64` otherwise. An operation that recomputes
coordinates declares `float64` and reports the normalization (ARROW-010).

## 12. Data vectors

The vectors in [`vectors/arrow-data-v1`](../../vectors/arrow-data-v1/) add row
values to the schema fixtures of section 6, in the shape of
[`arrow-data-vector-v1.schema.json`](../../schemas/arrow-data-vector-v1.schema.json).
A binary value, geometry included, is written as lowercase hexadecimal. A
`valid` vector is accepted by every consumer of this vocabulary; an `invalid`
vector names the category a consumer reports and the rules that decide it. A
valid vector whose geometry field carries a CRS definition also states the
verdict of a consumer that computes with the coordinates (VOC-015), derived
from the reference parts of the CRS identifiers the vectors use, which the
validator lists.
The validator decodes every geometry value and derives the verdict from the
rules of this document, so a vector cannot state a category the rules do not
give.
