# 0013: Meaning of the geometry keys: axis order, CRS definition, encodings, types

Status: accepted

Date: 2026-10-10

## Context

The interoperability suite (`plenora-interop`, report of 2026-10-10) ran the
same vectors through IO-tools, data-tools and database-tools. Arrow
Vocabulary 1.0 closes the values of the geometry keys but not what several
of them mean, and the three libraries chose differently:

1. **`axis_order`.** IO-tools declares `lat_lon` for every `EPSG:4326` field,
   the axis order of the EPSG registry, including fields read from GeoPackage
   or CSV whose values store longitude first. data-tools reads the key as the
   order of the stored coordinates and rejects every geometry operation on
   them (DT-ARROW-004). The published vector `resolved-point.json` declares
   `lat_lon` for `EPSG:4326`, which each library reads its own way.
2. **`crs_definition`.** data-tools rejects every definition it cannot
   interpret without a CRS library, even next to an identifier it knows;
   IO-tools writes one for every GeoPackage it reads. Nothing says which of
   identifier and definition prevails, or what a contradiction is.
3. **Encodings and SRID.** database-tools refuses `wkb` when the field
   declares an SRID and requires EWKB; IO-tools sinks refuse `ewkb`, the only
   encoding database-tools emits. Both encodings are in the closed set.
4. **Types, several geometry fields, identity and precision.**
   database-tools refuses `types=point,polygon` as an invalid type;
   IO-tools and data-tools refuse a second geometry field without a stated
   category; database-tools reads geometry fields without `field_id` and
   `precision`, which section 4 requires.

data-tools proposed (2026-10-10) to read only the identifier at the root of
a definition, never nested ones, and to compare the decidable parts of the
definition with the CRS the identifier names before computing, because the
identifier alone lets a definition modified under the same identifier pass in
silence.

## Compatibility test

As in [decision 0010](0010-runtime-rejection-and-identity.md): choosing one
meaning among those a conforming consumer can already hold is compatible, and
makes some producers non-conforming, which is an adoption impact recorded
below; rejecting input that 1.0 accepts from a conforming producer is
incompatible.

- `axis_order` had no stated meaning. Of the two readings in use, only the
  stored order says anything the identifier does not already say: the
  registry order follows from `crs_id`, and ARROW-008 makes the key "part of
  the public meaning". It is also the reading of GeoParquet 1.1, whose
  coordinates are always easting or longitude first. Fixing it is a
  clarification; IO-tools changes what it emits, and no metadata becomes
  invalid.
- VOC-005 rejects a definition whose top-level identifier contradicts
  `crs_id`. Section 4 already requires contradictory metadata to fail with
  `crs` and ARROW-006 forbids choosing one interpretation; a producer that
  emits such a field is not conforming today. A definition that is not
  well-formed in its declared format already violates the grammar of the
  key.
- VOC-015 binds only a consumer that computes with the coordinates: it may
  refuse a computation that 1.0 does not mention, but never input that a
  pass-through or a sink accepts. ARROW-007 already forbids treating an
  unverified CRS as resolved.
- VOC-007 makes consumers accept more (both encodings), never less.
- VOC-008 to VOC-011 state what a well-formed WKB or EWKB value is and that a
  value contradicting the declared types, dimensions or SRID is not accepted:
  such a value was never conforming input.
- VOC-012 and VOC-013 fix a category and an assignment rule where 1.0 had
  none; VOC-014 states the meaning of a closed value.

## Decision

Arrow Vocabulary 1.0 gains sections 7 to 12 (VOC-001 to VOC-015):

| gap | rules |
|---|---|
| 1 | VOC-001 (stored order, not registry order), VOC-002 (the producer declares it from the source convention, `unknown` when it cannot), VOC-003 (verification through the boundary, with coordinates that cannot be exchanged unnoticed) |
| 2 | VOC-004 (the identifier is normative; a consumer that only carries or records the CRS never needs to interpret the definition), VOC-005 (top-level identifiers only, contradiction is `crs`, malformed is `crs`), VOC-006 (definition without identifier), VOC-015 (verification before computing: identifier at the root and decidable parts, at least kind, base CRS identifier, ellipsoid, datum shift; otherwise `crs` before computing) |
| 3 | VOC-007 (both encodings accepted everywhere), VOC-008 (`wkb`: no SRID flag; SRID from the field), VOC-009 (`ewkb`: an SRID only on the outermost geometry, equal to the field's, otherwise `crs`) |
| 4 | VOC-010 (types as a closed set; several types are valid; `unsupported` for a target that cannot store them), VOC-011 (`data_mapping` for malformed values and values outside the declaration), VOC-012 (several geometry fields; `unsupported` for a consumer limited to one), VOC-013 (smallest free identifier in field order), VOC-014 (meaning of `precision`) |

New schema `arrow-data-vector-v1.schema.json` and 29 vectors in
`vectors/arrow-data-v1`: schema fixtures with row values, geometry as
hexadecimal WKB. The validator decodes every value and derives each verdict
from the rules (`tools/arrow_data.py`): input verdict, category and rule, and
for a field with a definition the verdict of a computing consumer, from a
reference table of the five EPSG identifiers the vectors use.

### data-tools' proposal

Adopted: identifiers only at the root (VOC-005), nested ones read only by
VOC-015; the identifier alone is not enough to compute (VOC-015); the parts
compared, which data-tools may extend and documents.

Different: a top-level identifier that contradicts `crs_id` fails at input
with `crs` for every consumer, as section 4 and ARROW-006 require, instead of
downgrading the field to declared-but-unresolved. For an unverified but not
contradictory definition the outcome is the one data-tools proposed: the
field passes through unchanged and an operation that computes fails with
`crs`.

### Second reading

An independent reading of the rules and of the validator found, and this
decision corrects:

- the minimum of VOC-015 let the most common modifications under the same
  identifier pass (another central meridian, an ellipsoid in feet, the Paris
  meridian): it now includes the prime meridian, every unit by name and
  factor, and the conversion method and parameters of a projected CRS;
- "well-formed" was undefined for WKB (cardinalities, closed rings, the SRID
  flag with an ISO type code, nesting) and for WKT (brackets of different
  kinds, a WKT 1 root declared `wkt2`): VOC-011 and VOC-005 define it;
- the grammars accepted a final line feed (`1
` as contract version, field
  identifier or SRID), an empty type list, a `crs_id` without authority and
  unknown `plenora.geometry.*` keys in a closed vocabulary: section 3 states
  the whole-value grammars and the closed key set;
- an SRID flag on a member is cited as VOC-008 or VOC-009 by encoding;
- the validator no longer states a computation verdict for a definition
  without identifier, which depends on the consumer's CRS knowledge, and
  checks that every rule a vector cites is defined.

### Not ratified

- **Rejecting `unknown` axis order for computation.** A consumer that
  computes with an `unknown` order assumes one. DT-ARROW-004 rejects only
  north-first orders. Rejecting `unknown` would refuse plans that 1.0 accepts
  (database-tools declares `unknown` for PostGIS fields). Options: (a) a rule
  in the next data-tools profile version; (b) database-tools declares the
  order it can establish (`lon_lat` for `geography`); (c) both. Recommended:
  (c).
- **A range check on geographic ordinates.** A latitude beyond 90 degrees
  shows exchanged ordinates, but the bound depends on the angular unit of the
  CRS (grads in some CRSs), so it is left to the consumer's CRS knowledge.
- **The CRS in `ARROW:extension:metadata`.** No library emits it; a successor
  vocabulary decides whether it becomes the shared representation.

## Alternatives

- **A successor vocabulary (`plenora.contract.version=2`).** Exact, but it
  would version every producer and consumer for clarifications that 1.0 can
  carry; decision 0009 keeps the successor for additions to the closed key
  set.
- **The registry order for `axis_order`.** Redundant with `crs_id`, and it
  leaves no key that says how to read the bytes.
- **The definition prevails over the identifier.** Every consumer would need
  a CRS library to read any field with a definition.

## Change statement

- **Consumers affected:** every producer and consumer of `geoarrow.wkb`
  fields.
- **Before:** closed values without stated meaning for axis order, CRS
  definition, encodings, types and precision.
- **After:** VOC-001 to VOC-015 and the data vectors.
- **Compatible:** yes, by the test above.
- **Schemas, examples and profiles:** new schema `arrow-data-vector-v1`,
  two invalid examples, 29 vectors. No existing schema, catalog, binding,
  vector or profile changes.
- **Adoption impact:**
  - IO-tools: declare the stored order (`lon_lat` for GeoPackage,
    GeoParquet, GeoJSON and coordinate columns in `EPSG:4326`), never the
    registry order (`axis_order_for` in `plenora-io-model/src/crs.rs`); accept
    `ewkb` in every sink after the VOC-009 check; reject a contradictory
    definition (VOC-005); report a second geometry field with `unsupported`.
  - data-tools: accept a definition next to an identifier it knows for
    pass-through and output, read top-level identifiers without a CRS
    library (VOC-005) and verify before computing (VOC-015); report a second
    geometry field with `unsupported`; check EWKB SRIDs when decoding.
  - database-tools: accept `wkb` with a declared SRID (VOC-008); accept a
    list of several types or reject it with `unsupported` (VOC-010); emit
    `field_id` and `precision` on every geometry field it reads (VOC-013,
    VOC-014); report an SRID mismatch with `crs` (VOC-009), never
    `resource_limit`.
