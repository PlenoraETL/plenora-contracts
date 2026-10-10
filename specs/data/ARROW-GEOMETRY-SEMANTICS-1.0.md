# Plenora Arrow Geometry Semantics 1.0

Status: normative

Contract identifier: `plenora-arrow-geometry-semantics-v1`

## 1. Scope

This contract fixes the meaning of the geometry keys of
[Arrow Vocabulary 1.0](ARROW-VOCABULARY-1.0.md) and what a component does
with them. It adds no key and no value, and does not change
`plenora.contract.version`: the bytes on the wire are those of Arrow
Interchange 1.0 and Arrow Vocabulary 1.0, which keep the meaning they were
published with.

It is opt-in. A component claims it in its adoption manifest, and from then
on follows every rule of this document on every surface that exchanges Arrow;
a component that does not claim it follows Arrow Vocabulary 1.0 only. A
pipeline relies on these rules only between components that claim them.

**GEO-000** — Three verdicts are distinct, and a vector or a component states
which one it gives:

1. **input conformance**: the input satisfies Arrow Vocabulary 1.0 and the
   grammar and consistency rules of this contract (GEO-004 to GEO-009,
   GEO-011, GEO-016). Every component that claims this contract accepts a
   conforming input and rejects a non-conforming one the same way;
2. **component support**: a component MAY refuse a conforming input that its
   targets cannot represent (GEO-010, GEO-012), with `unsupported`;
3. **operation applicability**: an operation that computes with the
   coordinates MAY refuse a conforming input whose CRS it cannot verify or
   use (GEO-006, GEO-015, or a profile rule), with `crs`.

A component profile MAY accept input that this contract rejects, such as the
missing keys that data-tools completes (DT-ARROW-003); this contract never
revokes an acceptance a profile states, and a profile never accepts less than
it requires.

## 2. Coordinate axis order

**GEO-001** — `plenora.geometry.axis_order` states the order of the first two
ordinates of every coordinate **as stored** in the WKB or EWKB values of the
field:

- `lon_lat`: longitude, then latitude;
- `lat_lon`: latitude, then longitude;
- `easting_northing`: easting, then northing;
- `northing_easting`: northing, then easting;
- `other`: a stored order whose axes are not one of these four pairs, such as
  westing and southing, or the axes of a polar projection that point along
  meridians rather than east and north (for example EPSG:3031);
- `unknown`: an order the producer could not establish.

It is not the axis order with which the CRS authority registers the CRS.
`EPSG:4326` registers latitude first; a field of `EPSG:4326` whose values store
longitude first declares `lon_lat`. Third and fourth ordinates (Z, M) are not
affected.

**GEO-002** — The producer of the field declares it: the component that puts
the values into the Arrow field, from the coordinate convention of the source,
of the request or of the computation that produced those values. It MUST NOT
derive the value from the axis order of the CRS registry alone. When the
specification of a source format fixes the stored order, that order is the
declaration; for example GeoPackage and GeoParquet store easting or longitude
first whatever the CRS, and GeoJSON (RFC 7946) stores longitude first. When
the format does not fix it, as for coordinates in a CSV file, the read
request states it. A producer that cannot establish the stored order declares
`unknown`. A pass-through keeps the value (Arrow Interchange 1.0, ARROW-008);
an operation that exchanges ordinates declares the order it produces.

`unknown` gives no guarantee about the order: a computation on a field with
`unknown` order is correct only if the stored order happens to be the one the
computation assumes. Rejecting such a computation is not required by this
version.

**GEO-003** — WKB bytes do not show their axis order: both orders are
well-formed. A producer's declaration is verified through its public boundary,
by reading a source whose stored order and coordinate values are known and
checking both the declared order and the decoded ordinates. The vectors use
coordinates whose two ordinates cannot be exchanged without leaving the
domain of the declared axis, such as a longitude beyond 90 degrees or a UTM
northing beyond the range of eastings.

## 3. CRS identifier and definition

**GEO-004** — When `plenora.geometry.crs_id` is present it is normative: it
identifies the CRS. A `plenora.geometry.crs_definition` next to it describes
the same CRS; it never replaces the identifier, and a component never
computes with the definition in place of the CRS the identifier names. A
component that only carries the field, or records its CRS identity (writes
the identifier or the SRID to a target), MUST NOT reject the field because it
cannot interpret the definition; GEO-005 still applies to it. A component
that computes with the coordinates follows GEO-015. A pass-through preserves
both values byte for byte (ARROW-008).

**GEO-005** — A producer MUST NOT emit a definition that describes a CRS other
than the one `crs_id` names. A component MUST read the top-level authority
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
the kind that opened it, every number is written with ASCII digits, and the
outermost keyword belongs to the declared version (`GEOGCS`, `PROJCS`, ... for
`wkt`; `GEOGCRS`, `PROJCRS`, `BOUNDCRS`, ... for `wkt2`); PROJJSON is a JSON
object without repeated keys. Identifiers nested in the definition, such as
the `AUTHORITY` of the `GEOGCS` inside a `PROJCS`, never satisfy and never
contradict this comparison; GEO-015 reads them.

**GEO-006** — Without `crs_id`, the definition is the identity of the CRS. A
component that computes with the coordinates and cannot interpret the
definition completely fails with `crs`; one that only passes the field
through carries it unchanged.

## 4. Encodings and SRID

**GEO-007** — Every component that claims this contract accepts both
`plenora.geometry.encoding` values on every `geoarrow.wkb` input. An operation
MUST NOT reject a field, or a value, because of which of the two encodings it
uses; a component that needs the other encoding converts as GEO-008 and
GEO-009 state, without loss.

**GEO-008** — Under `wkb`, values carry no SRID. Dimension flags may use the
ISO form (type code plus 1000, 2000 or 3000) or the extended form (high bits
`0x80000000` for Z and `0x40000000` for M); a value with the SRID flag
`0x20000000` is malformed and fails with `data_mapping`. Every value has the
CRS of the field. A component that needs a numeric SRID takes
`plenora.geometry.srid`; without that key it derives the SRID from the CRS
identity only under a mapping it documents, and otherwise fails with `crs`.

**GEO-009** — Under `ewkb`, a value MAY carry an SRID on its outermost
geometry, and only with the extended type code; an SRID flag on a member of a
multi-geometry or collection is malformed and fails with `data_mapping`, even
when it equals the outer SRID. A value that carries an SRID requires the field
to declare `plenora.geometry.srid` with the same integer: a value whose SRID
differs from it, or that carries an SRID when the field declares none, fails
with `crs`. A value without SRID has the SRID of the field. The check binds
every component that decodes the value, converts it to `wkb` or writes it to a
target that interprets geometry, before that value takes effect (GEO-018); a
component that carries the bytes unchanged leaves it to the next one. A
producer that emits EWKB values with an SRID declares that SRID on the field.
Converting ISO WKB to EWKB rewrites an ISO type code to the extended form
before setting the SRID flag.

## 5. Geometry types and several geometry fields

**GEO-010** — With `types_declaration=exact`, `plenora.geometry.types` is the
closed set of the types of the non-null values; it does not assert that every
listed type occurs. With `mixed`, the field admits several types by
declaration, such as an unconstrained database column; a list, when present,
is the closed set, and without a list any type is admitted. `unknown` in a
list admits any type. `unresolved` states nothing. A list of several types,
such as `point,polygon`, is valid under `exact` and `mixed`. A component MUST
NOT reject such a list as malformed and MUST NOT select one of its types: a
target that cannot store the declared set rejects the field with
`unsupported` before any effect.

**GEO-011** — A component that decodes a value rejects it with `data_mapping`
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

**GEO-012** — A schema MAY carry several `geoarrow.wkb` fields. Each declares
its own complete metadata; CRS, encoding and types of different fields are
independent. A component that accepts one geometry field per schema rejects a
schema with several with `unsupported` before any effect; it MUST NOT drop a
field, demote it to plain binary or choose one. A component with that limit
SHOULD make it predictable from its discovery results.

## 6. Identity and precision of produced geometry fields

**GEO-013** — A component that produces a geometry field from a source that
carries no field identity, such as a file or a database column, assigns
`plenora.field_id`: the smallest non-negative integer not already used in the
schema, taking the fields without identity in field order. The same rule
applies to every other field to which it assigns an identity. An identity
carried by the source is preserved (ARROW-004).

**GEO-014** — `plenora.geometry.precision` describes the coordinate values the
WKB carries: `float64` that they are the binary64 values in the bytes, which
is true of every WKB value and is the declaration of a producer that knows
nothing more; `float32` that every coordinate is exactly representable in
binary32 because the source stored binary32; `native` that the source's own
coordinate model, such as a fixed grid or decimal storage, produced them. A
producer that reads a source declares `float32` or `native` only when the
source establishes it, and `float64` otherwise. An operation that recomputes
coordinates declares `float64` and reports the normalization (ARROW-010).

## 7. Verification before computing

**GEO-015** — A component that computes with the coordinates in their CRS
(measures, transforms, reprojects or builds geometry in CRS units) uses the
CRS that `crs_id` names only after verifying the definition next to it, when
there is one:

1. the definition carries a top-level identifier equal to `crs_id` (GEO-005);
2. the parts of the definition agree with the CRS that `crs_id` names:
   - the CRS kind (geographic or projected) and the identifier of the base
     CRS when the definition names one;
   - the identifier of the datum or datum ensemble, which the definition
     must state: a datum without identifier is undecidable, never inferred
     from its ellipsoid or its name;
   - the semi-major axis and inverse flattening of the ellipsoid;
   - the prime meridian, wherever the format places it (in PROJJSON, in the
     datum or datum ensemble);
   - every unit, each for the quantity it measures (GEO-017);
   - for a projected CRS, the conversion method and every parameter value;
   - the absence of a datum shift (`TOWGS84`, `BOUNDCRS`) that the CRS of
     `crs_id` does not have.

Every comparison follows the conservative subset of GEO-017, identically in
every component; a part outside that subset is undecidable. A definition
without that identifier, one whose parts differ, and one with an undecidable
part are not verified: the operation fails with `crs` before computing. An
identifier equal to `crs_id` is not enough by itself: a definition modified
under the same identifier would otherwise pass in silence. Without a
definition, the component computes with the CRS that `crs_id` names when it
knows it, and fails with `crs` otherwise.

**GEO-016** — The grammars of Arrow Vocabulary 1.0 section 3 match the whole
value: a decimal integer, an SRID or a contract version followed by a line
feed or any other character is not well-formed. `plenora.geometry.crs_id` is
`AUTHORITY:CODE`, an authority name starting with a letter (letters, digits,
`_`, `.`, `-`), a colon and a code without spaces or colons.
`plenora.geometry.types`, when present, is not empty. The geometry keys are
exactly those of the vocabulary's table: any other key beginning with
`plenora.geometry.` is not well-formed, except those under
`plenora.geometry.native.`.

**GEO-017** — The conservative subset. Every component compares definitions
with these rules and no others, so that two components never disagree on
whether a definition is verified:

- **numbers** compare as exact decimal values: the decimal text, with an
  optional sign, fraction and exponent, denotes a rational number, and two
  numbers are equal when they denote the same one (`6378137`, `6378137.0`
  and `6.378137E6` are equal). No number is rounded or converted to binary
  floating point;
- **units** are identified by their ASCII case-insensitive name and their
  factor, and must measure the quantity of the place where they occur
  (angle for a geographic coordinate system, a prime meridian and an angular
  parameter; length for a projected coordinate system, an ellipsoid axis and
  a linear parameter; scale for a scale factor). The decided units are:

  | quantity | names | factor |
  |---|---|---|
  | angle | `degree` | `0.0174532925199433` or `0.017453292519943295` |
  | length | `metre`, `meter` | `1` |
  | scale | `unity` | `1` |

  The two spellings of the degree are the fifteen-digit factor that EPSG,
  GDAL and PROJ write in WKT and the shortest decimal that round-trips the
  binary64 nearest to pi/180; comparing a factor with two fixed decimals is
  an exact text-level comparison that every language implements the same
  way, while an approximate comparison would need a tolerance that two
  implementations could round differently. Any other unit or factor is
  undecidable;
- **implicit units**: in WKT 1 the units are fixed by the format (the
  `UNIT` of the `GEOGCS` for angles, of the `PROJCS` for lengths, metres for
  the `SPHEROID`); in WKT 2 and PROJJSON a coordinate system, a prime
  meridian and every parameter carry their unit (in WKT 2, the coordinate
  system's unit as a child of the CRS or of every axis), and an ellipsoid
  without unit is in metres. A unit that is missing where these rules
  require one is undecidable;
- **ellipsoid**: the semi-major axis and the inverse flattening. A
  definition that gives the semi-minor axis instead of the inverse
  flattening is undecidable;
- **methods and parameters** are identified by name, from this closed list
  of aliases, ASCII case-insensitively:

  | name in the reference | aliases |
  |---|---|
  | transverse mercator | `Transverse Mercator`, `Transverse_Mercator` |
  | latitude of origin | `latitude_of_origin`, `Latitude of natural origin` |
  | central meridian | `central_meridian`, `Longitude of natural origin` |
  | scale factor | `scale_factor`, `Scale factor at natural origin` |
  | false easting | `false_easting`, `False easting` |
  | false northing | `false_northing`, `False northing` |

  A method or parameter outside the list, or a parameter repeated, is
  undecidable. Parameters compare as a set, whatever their order;
- **reference values** are those of the EPSG registry for the identifier.

**GEO-019** — The closed grammar. A definition is verifiable only when it is
made entirely of the nodes and members below; any other node, member, object
type or attribute, whatever it says, makes it undecidable, so the operation
that computes fails with `crs` and a pass-through carries the field
unchanged. A dynamic frame (`DYNAMIC`, `FRAMEEPOCH`,
`DynamicGeodeticReferenceFrame`, `frame_reference_epoch`), a datum ensemble,
`USAGE`, `SCOPE`, `AREA`, `BBOX`, `REMARK`, a datum shift, a unit on an axis
and any member a later version of a format adds are therefore undecidable: a
format's extension never turns into a verified definition.

WKT 1, outermost `GEOGCS` or `PROJCS`; each node admits at most the number
of values shown and the children listed, each once unless marked `*`:

| node | values | children |
|---|---|---|
| `GEOGCS` | 1 | `DATUM`, `PRIMEM`, `UNIT`, `AXIS`*, `AUTHORITY` |
| `PROJCS` | 1 | `GEOGCS`, `PROJECTION`, `PARAMETER`*, `UNIT`, `AXIS`*, `AUTHORITY` |
| `DATUM` | 1 | `SPHEROID`, `AUTHORITY` |
| `SPHEROID` | 3 | `AUTHORITY` |
| `PRIMEM`, `UNIT` | 2 | `AUTHORITY` |
| `PROJECTION` | 1 | `AUTHORITY` |
| `AXIS`, `PARAMETER`, `AUTHORITY` | 2 | none |

WKT 2, outermost `GEOGCRS` or `PROJCRS`:

| node | values | children |
|---|---|---|
| `GEOGCRS` | 1 | `DATUM`, `PRIMEM`, `CS`, `AXIS`*, `ANGLEUNIT`, `ID`* |
| `PROJCRS` | 1 | `BASEGEOGCRS`, `CONVERSION`, `CS`, `AXIS`*, `LENGTHUNIT`, `ID`* |
| `BASEGEOGCRS` | 1 | `DATUM`, `PRIMEM`, `ANGLEUNIT`, `ID`* |
| `DATUM` | 1 | `ELLIPSOID`, `ID`* |
| `ELLIPSOID` | 3 | `LENGTHUNIT`, `ID`* |
| `PRIMEM` | 2 | `ANGLEUNIT`, `ID`* |
| `CONVERSION` | 1 | `METHOD`, `PARAMETER`*, `ID`* |
| `METHOD` | 1 | `ID`* |
| `PARAMETER` | 2 | `ANGLEUNIT`, `LENGTHUNIT`, `SCALEUNIT`, `ID`* |
| `ANGLEUNIT`, `LENGTHUNIT`, `SCALEUNIT` | 2 | `ID`* |
| `CS`, `AXIS`, `ID` | 2 | none |

PROJJSON, root of type `GeographicCRS` or `ProjectedCRS`; each object admits
only the members listed (an `id` or `ids` holds objects with `authority` and
`code` only; a unit object holds `type`, `name` and `conversion_factor`; a
number may be an object with `value` and `unit`):

| object | members |
|---|---|
| `GeographicCRS` | `$schema`, `type`, `name`, `datum`, `coordinate_system`, `id`, `ids` |
| `ProjectedCRS` | `$schema`, `type`, `name`, `base_crs`, `conversion`, `coordinate_system`, `id`, `ids` |
| base CRS (type `GeographicCRS` when stated) | `type`, `name`, `datum`, `coordinate_system`, `id`, `ids` |
| datum (type `GeodeticReferenceFrame` when stated) | `type`, `name`, `ellipsoid`, `prime_meridian`, `id`, `ids` |
| ellipsoid | `name`, `semi_major_axis`, `inverse_flattening`, `id`, `ids` |
| prime meridian | `name`, `longitude`, `id`, `ids` |
| coordinate system | `subtype`, `axis` |
| axis | `name`, `abbreviation`, `direction`, `unit` |
| conversion | `name`, `method`, `parameters`, `id`, `ids` |
| method | `name`, `id`, `ids` |
| parameter | `name`, `value`, `unit`, `id`, `ids` |

A definition admitted by the grammar is then verified by GEO-015 and GEO-017.

## 8. Effects

**GEO-018** — "Before any effect" means before anything is published or
committed. A component that writes inside a transaction it can roll back may
have written provisionally when it meets a value that GEO-009 or GEO-011
rejects; it rolls back and reports `remote_effect: rolled_back` when the
rollback is proven, and `unknown` otherwise (Typed Errors 1.0, ERR-004).

## 9. Data vectors

The vectors in [`vectors/arrow-data-v1`](../../vectors/arrow-data-v1/) are
schema fixtures of Arrow Vocabulary 1.0 with row values, in the shape of
[`arrow-data-vector-v1.schema.json`](../../schemas/arrow-data-vector-v1.schema.json).
A binary value, geometry included, is written as lowercase hexadecimal.
`expect` is the input-conformance verdict of GEO-000: a `valid` vector is
accepted by every component that claims this contract, unless its support
(GEO-010, GEO-012) or the applicability of an operation refuses it; an
`invalid` vector names the category and the rules. A valid vector whose
geometry field declares a CRS may state, in `computation`, the applicability
verdict for an operation that computes (GEO-015), derived from the reference
parts of the identifiers the vectors use, which the validator lists. The
validator decodes every geometry value and derives every verdict from the
rules, so a vector cannot state one the rules do not give. The vectors
illustrate the rules; their number does not attest that every rule, phase or
remote effect is covered.
