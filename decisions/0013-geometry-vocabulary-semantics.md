# 0013: Arrow Geometry Semantics 1.0, an opt-in contract next to the vocabulary

Status: accepted

Date: 2026-10-10

## Context

The interoperability suite (`plenora-interop`, report of 2026-10-10) ran the
same vectors through IO-tools, data-tools and database-tools. Arrow
Vocabulary 1.0 closes the values of the geometry keys but not what several
of them mean, and the libraries chose differently:

1. **`axis_order`.** IO-tools declares `lat_lon` for every `EPSG:4326` field,
   the axis order of the EPSG registry, including fields read from GeoPackage
   or CSV whose values store longitude first. data-tools reads the key as the
   order of the stored coordinates and rejects every geometry operation on
   them (DT-ARROW-004).
2. **`crs_definition`.** data-tools rejects every definition it cannot
   interpret without a CRS library, even next to an identifier it knows;
   IO-tools writes one for every GeoPackage it reads. Nothing says which of
   identifier and definition prevails, or what a contradiction is.
3. **Encodings and SRID.** database-tools refuses `wkb` when the field
   declares an SRID; IO-tools sinks refuse `ewkb`, the only encoding
   database-tools emits.
4. **Types, several geometry fields, identity and precision.** database-tools
   refuses `types=point,polygon`; IO-tools and data-tools refuse a second
   geometry field without a stated category; database-tools reads geometry
   fields without `field_id` and `precision`.

data-tools proposed to read only the identifier at the root of a definition
and to compare the decidable parts before computing.

## Why a new contract, not a clarification of 1.0

The first version of this change wrote the rules into Arrow Vocabulary 1.0
as clarifications. An independent reading (Codex) showed that some of them
restrict what v1.1.0 admitted: a definition without a top-level identifier,
interpretable before, is now refused for computation; the rejection
categories would override acceptances that a published profile states
(DT-ARROW-003). COMPATIBILITY.md asks for the same meaning and the same
accepted data; keeping the old files is not enough when the meaning of the
rules changes, and that those behaviors were already non-conforming cannot
be shown point by point.

A successor wire vocabulary (`plenora.contract.version=2`) would make every
consumer of version 1 reject every new schema (ARROW-002), for rules that add
no key. The rules are therefore an opt-in contract next to the vocabulary,
**Arrow Geometry Semantics 1.0** (`plenora-arrow-geometry-semantics-v1`):

- Arrow Vocabulary 1.0 returns to its published text, plus an informative
  section that points to the new contract;
- the wire is unchanged: same keys, same values, same contract version;
- a component claims the contract in its adoption manifest and then follows
  every rule; a pipeline relies on them only between components that claim
  them;
- the repository release that publishes it is MINOR (new contract and
  vectors next to the existing ones, no published meaning changes).

## Decision

Arrow Geometry Semantics 1.0, rules GEO-000 to GEO-018:

| gap | rules |
|---|---|
| three verdicts | GEO-000: input conformance, component support and operation applicability are distinct; profile acceptances such as DT-ARROW-003 are never revoked |
| 1 | GEO-001 (stored order, `other` for polar or south-oriented axes), GEO-002 (the producer declares it from the source, the request or the computation; `unknown` gives no guarantee), GEO-003 (verification with coordinates that cannot be exchanged unnoticed) |
| 2 | GEO-004 (the identifier is normative), GEO-005 (top-level identifiers only; contradiction and malformed definitions are `crs`), GEO-006 (definition without identifier), GEO-015 (verification before computing: identifier at the root, kind, base CRS, datum, ellipsoid, prime meridian, units by quantity, conversion, datum shift), GEO-017 (the conservative subset every component applies identically) |
| 3 | GEO-007 (both encodings accepted), GEO-008 (`wkb`), GEO-009 (`ewkb`, SRID only on the outermost geometry, ISO to EWKB conversion), GEO-018 (an effect is a publication or a commit) |
| 4 | GEO-010 (types as a closed set), GEO-011 (well-formed WKB), GEO-012 (several geometry fields), GEO-013 (identifiers), GEO-014 (precision), GEO-016 (whole-value grammars, closed geometry keys) |

### The factor of the degree

GEO-017 admits two exact spellings of the degree, `0.0174532925199433` (the
fifteen digits that EPSG, GDAL and PROJ write in WKT) and
`0.017453292519943295` (the shortest decimal that round-trips the binary64
nearest to pi/180), compared as exact decimal values. A comparison with two
fixed decimals needs only a decimal normalization (sign, digits, exponent),
which Rust and Python implement identically; a tolerance would need a
floating-point comparison that two implementations can round differently,
and pi/180 itself has no finite decimal expansion.

### data-tools' proposal

Adopted: identifiers only at the root (GEO-005), nested ones read only by
GEO-015; the identifier alone is not enough to compute; the parts compared.
Different: a top-level identifier that contradicts `crs_id` fails at input
with `crs`, as Arrow Vocabulary 1.0 section 4 and ARROW-006 require, instead
of downgrading the field to declared-but-unresolved.

### Second readings

Two independent readings found, and this decision corrects: the first
minimum of the verification let modified definitions pass (another central
meridian, an ellipsoid in feet, the Paris meridian, a changed datum
identifier, coordinate-system units in PROJJSON, a unit of the wrong
quantity); "well-formed" was undefined for WKB and WKT; the grammars accepted
a final line feed, empty type lists, an authority-less `crs_id` and unknown
geometry keys; vectors combined two defects where one was meant (now a
vector with only the nested base identifier altered and one with only a
member SRID); `valid` meant two things (GEO-000).

A further reading found two more ways a modified definition passed: the
PROJJSON prime meridian was read on the CRS while the format places it in
the datum, and a datum without identifier was accepted when its ellipsoid
matched. The meridian is read wherever it is placed, and an identity the
definition does not state is undecidable, never inferred. The validator's
messages name fields by position, never by name, and the vector of a
definition without root identifier is now isolated (the same complete UTM
definition with the identifier is accepted). The vectors illustrate the
rules; their number does not attest full coverage.

### Not ratified

- **Rejecting `unknown` axis order for computation.** Options: (a) a rule in
  the next data-tools profile version; (b) database-tools declares the order
  it can establish (`lon_lat` for `geography`); (c) both. Recommended: (c).
- **A range check on geographic ordinates.** The bound depends on the angular
  unit of the CRS.
- **The CRS in `ARROW:extension:metadata`.** A successor vocabulary decides.

## Change statement

- **Consumers affected:** components that claim the new contract, and the
  interoperability suite.
- **Before:** closed values without stated meaning.
- **After:** Arrow Geometry Semantics 1.0, opt-in; Arrow Vocabulary 1.0
  unchanged except an informative pointer.
- **Compatible:** yes: a new contract next to the existing ones; nothing
  published changes meaning.
- **Schemas, examples and profiles:** new specification, new schema
  `arrow-data-vector-v1`, two invalid examples, 42 vectors in
  `vectors/arrow-data-v1`. No existing schema, catalog, binding, vector or
  profile changes.
- **Adoption impact**, for a component that claims the contract:
  - IO-tools: declare the stored order (`lon_lat` for GeoPackage,
    GeoParquet, GeoJSON and coordinate columns in `EPSG:4326`), never the
    registry order (`axis_order_for` in `plenora-io-model/src/crs.rs`); accept
    `ewkb` in every sink after the GEO-009 check; reject a contradictory
    definition (GEO-005); a second geometry field is `unsupported`.
  - data-tools: accept a definition next to an identifier it knows for
    pass-through and output, read top-level identifiers without a CRS
    library and verify with the subset of GEO-017 before computing; a second
    geometry field is `unsupported`; check EWKB SRIDs when decoding.
  - database-tools: accept `wkb` with a declared SRID; accept a list of
    several types or reject it with `unsupported`; emit `field_id` and
    `precision` on every geometry field it reads; an SRID mismatch is `crs`.
