# Plenora Geometry Operations 1.0

Status: normative

Contract identifier: `plenora-geometry-operations-v1`

## 1. Scope and oracle notation

**GOP-001** — This opt-in contract governs newly exposed geometric behavior
shared between components. An adopter MUST name its supported families and
profiles at its public boundary. It MUST NOT reinterpret an existing operation
identity, Arrow field, plan budget or default through this contract. It defines
no new WKB encoding, Arrow key, plan format, runtime envelope or endpoint.
All rules labelled **Product** below are family product choices, not external
standard requirements. Oracle identifiers resolve to exact editions/sections
in the [oracle register and fixture plan](../../conformance/GEOMETRY-ORACLES-1.0.md).

**GOP-002** — All new profiles here accept finite XY coordinates, resolved
CRS/datum, stated stored axis order and explicit numerical precision. A pair
uses the same CRS unless an explicit transformation is part of the request.
Z, M and curves are `unsupported`, never discarded. Invalid geometry is
`data_mapping`; repair is an explicit separate policy with a declared method,
collapsed types and error bound. Empty and null are distinct: a null geometric
operand is `data_mapping` for these new calculations, without changing nullable
Arrow transport. New batched
calculations are atomic: failure returns no successful prefix. Existing
service per-element behavior is outside this new API contract. Product;
O1, E0; Arrow GEO-001–GEO-020 and REJ-001–REJ-004 still govern Arrow input.

## 2. Models, CRS and accuracy

**GOP-003** — The model MUST be explicit: `planar`, `shortest_geodesic`, or
`preserve_shape`. Planar segments are straight in stored SR coordinates;
length and area use coordinate units and their square. In a geographic SR
they are angular, never metres inferred from degrees. A segment from 179 to
-179 crosses the coordinate plane through 0; it does not wrap at 180. The
poles are coordinate locations in this model, not a topological seam.
No implicit reprojection or geometry-to-geography conversion is permitted.
Product, with O1 planar topology and E1 calculationType as distinct oracles.

**GOP-004** — Shortest-geodesic calculations use the ellipsoid of the resolved
datum, geodetic latitude in [-90,90] and longitude in [-180,180]. Both longitude
endpoints are accepted; generated longitude is in [-180,180), and a generated
pole uses longitude 0. Original vertices remain unchanged in densify.
Distances are metres and areas square metres unless a declared linear/area
unit conversion is requested (international foot = 0.3048 m exactly).
No sphere substitutes for an ellipsoid. Coincident points have distance zero.
Non-unique shortest paths, including the relevant antipodal cases, fail with
`unsupported` when a path is required; a unique near-antipodal path is valid.
Point-pair minimum distance remains defined even with multiple minimizers.
Pole crossings use continuous geodesic paths, never linear interpolation of
longitude. Product domain; G1 sections 2, 4–6 and G2 Multiple shortest geodesics.

**GOP-005** — The first surface domain consists of simple shells and holes
whose individual enclosed region is strictly less than half the ellipsoid.
Shell/hole roles are explicit; crossing/touching rings or an ambiguous
hemisphere/complement are `unsupported`. A pole inside a small cap is allowed.
Signed ring area is positive counter-clockwise as viewed from outside the
ellipsoid; reversing traversal negates it. Surface area is the positive shell
area less positive hole areas. Esri clockwise shell serialization MUST NOT
negate the reported surface area. Larger regions require a distinct explicit
complement policy, outside this first profile. Product; G1 section 6,
G2 Area of a polygon, E0 Polygon. Antimeridian crossings are continuous;
serialization that needs planar pieces splits at the seam with paired +180/-180
boundary coordinates and preserves topology. Cutting changes representation,
not the geodesic region. An uncertifiable seam reconstruction fails.

**GOP-006** — Each approximate result MUST carry or reference a public error
certificate: model, CRS/datum, units, absolute bound, relative bound, and
composition of transformation, discretization and numerical errors. For a
scalar result v and exact model value t, the guarantee is
`abs(v-t) <= absolute + relative*abs(t)`. Length and area bounds are separate.
Both bounds are finite and nonnegative, in the declared scalar units (relative
is dimensionless). The certificate concerns the exact selected mathematical
model, not the survey accuracy of a datum realization or a transformation.
Those source uncertainties are reported separately; extrapolation marked
unassured MUST NOT be presented as a certified real-world positional accuracy.
A geometry approximation uses a symmetric Hausdorff bound in the declared
model metric and must preserve the declared topology. Precision metadata
`float64` is coordinate representation, not an error certificate. Quantization
and requested repair/generalization are stated separately from numeric error.
Sampling convergence alone is not certification. Failure to prove the requested
bound is `execution` with bounded code `GEOMETRY_ACCURACY_UNPROVEN`, or
`resource_limit` when an actual budget was exhausted. Product; G1/G2 only
certify their primitive domain, not complete buffers or minimization.

**GOP-007** — Geodesic densify inserts uniform arc-length divisions on each
unique shortest edge: n = max(1,ceil(length/maxSegmentLength)), with positive
finite maxSegmentLength. Its domain is LineString/MultiLineString and
Polygon/MultiPolygon; other types are `unsupported`. Length measures accept
lines and polygon boundaries; area measures accept polygons. Empty measures
are zero, and multipart measures sum their parts. Each produced edge MUST satisfy that maximum after
numeric certification; increase n if needed. Preserve vertices, part order
and closure; an empty input remains empty. This maximum is not a shape-error
bound. PreserveShape instead measures the inverse-projected original straight
SR segment, or the original straight longitude/latitude segment in a geographic
SR. Its source coordinate path is never silently unwrapped; callers split a
short seam crossing explicitly. Unsupported inverse-projection domain fails
with `crs`. Product subdivision and seam policy; G1 direct/inverse, E1 Densify
and Areas and Lengths calculationType.

**GOP-008** — Geometric distance is the infimum over all points of both sets,
including filled polygon interiors; intersection or containment gives zero.
An empty operand is `data_mapping` in this new profile. Vertex-only distance
does not conform. Buffer of radius r is the closed metric neighborhood of the
whole set. Negative r is defined only for surfaces, as erosion; collapse is a
typed empty polygon, not null. Nonnegative line/point buffers and surface
buffers must meet GOP-005 and GOP-006; global/ambiguous complements fail with
`unsupported`. A zero-radius point/line buffer has empty polygonal output.
Output is Polygon/MultiPolygon, never an unannounced collection. An empty buffer
input produces a typed empty polygon result. Multiple
distances use distance-major, then input order; unionResults combines inputs
separately per distance. Product domain/order; E1 Buffer/Distance and analytic
set definitions; G1 is only a primitive oracle.

**GOP-009** — New projection policies retain rejection outside Web Mercator's
qualified domain; this contract introduces no clamp. Parametric extrapolation
requires explicit opt-in and returns accuracy as unassured outside the
transformation area. Grid extrapolation without covered samples is forbidden.
Esri WKT ingress MUST verify structure, parameters, datum and units against a
published closed alias subset; a matching name is insufficient. The new
`esri_wkt_ingress_v1` product subset uses the WKT1 structure and exact decimal
comparisons of GEO-017/GEO-019, adding only `D_WGS_1984` as an alias of datum
EPSG:6326. It accepts geographic WGS84 and WGS84 UTM zones 1..60, north/south,
with semi-major axis 6378137, inverse flattening 298.257223563, Greenwich 0,
degree factors from GEO-017 and projected metre factor 1. UTM requires
Transverse_Mercator, latitude_of_origin=0, central_meridian=6*zone-183,
scale_factor=0.9996, false_easting=500000 and false_northing=0 north or
10000000 south. No missing/duplicate parameter, datum shift, extension node
or unknown method is inferred from the outer name. Top-level authority, if
present, must agree with the structurally derived EPSG:4326 or 326xx/327xx;
without authority the complete structure must identify that same CRS uniquely.
Other definitions fail with `crs`. This adapter applies only to explicitly
selected raw ingress. It emits a canonical CRS identity/definition and records
normalization before constructing Arrow. An already received v1 Arrow field
still uses the unchanged GEO-017/GEO-019 subset: D_WGS_1984 without datum ID
there remains undecidable. This is a separate ingress interpretation, not an
extension of the old Arrow grammar. Product D2–D4; E2 Project and E0 Spatial
reference; alias compatibility needs paired S03 fixtures before release claim.

**GOP-010** — Generalize output repair requires explicit opt-in and separate
qualification of its displacement and collapsed types; it is not ordinary
Douglas–Peucker. A new dimensional hull returns empty Polygon for no sites,
Point for one distinct site, and LineString between lexicographic extreme
sites for exact collinearity; otherwise it retains the declared polygonal
hull policy. Exact degeneracy is the default. An explicit positive threshold
in SR units uses the minimum width of the convex hull; at or below that width
threshold it returns the farthest site pair as a LineString, endpoints in
lexicographic order and lexicographic pair order resolving distance ties.
This threshold is distinct from concavity. A new splitLine API has
separate nonnegative attachment-distance and cut-merge-distance parameters.
Attachment is inclusive; cut merging uses curvilinear distance, sorted cuts,
and retains the first cut of each group whose distance from that retained cut
is at most the merge tolerance (no transitive chaining), independently for
each input part. End cuts do not
create zero-length pieces. Product D5/D7; E2 Generalize only for the unrepaired
operation, O1 convexHull only for dimensional reasoning, analytic projections
and intervals for splitLine. No decision on the service fallback is implied.

## 3. Topology and the Esri relation subset

**GOP-011** — The reusable topology model is planar OGC SFA 1.2.1 DE-9IM,
ordered `II IB IE / BI BB BE / EI EB EE`. Point boundary is empty; line
boundary uses mod 2 over all endpoints of all parts. A closed line has empty
boundary; a shared endpoint with even multiplicity is interior. Polygon
boundary is its rings. Precision is explicit and applied before topology;
no hidden epsilon expands a set. Oracle O1 sections 6.1.7, 6.1.11, 6.1.15.

**GOP-012** — `esri_subset_v1` uses the following ordered A,B mapping.
This is a declared product subset pending E3 server qualification, not a
universal claim about ArcGIS line boundaries. Arrays are type-homogeneous;
each emitted true pair retains the two input indexes, sorted lexicographically.

| Name after esriGeometryRelation | Domain | DE-9IM condition |
|---|---|---|
| In | points, lines, surfaces | `T*F**F***` (OGC Within) |
| Within | nonempty points, lines, surfaces | covered-by: IE=F and BE=F |
| InteriorIntersection | points, lines, surfaces | `T********` |
| LineCoincidence | surface/surface only | `****1****` |
| LineTouch | surface/surface only | `F***1****` |
| PointTouch | points, lines, surfaces | II=F; maximum dimension of IB, BI, BB is 0 |
| Relation | points, lines, surfaces | pattern evaluation under GOP-013 |

For any empty operand the named predicates above are false; Relation evaluates
the actual empty-set matrix. Unsupported dimensional pairs for LineCoincidence
or LineTouch give `unsupported`, never false as a substitute. E3 SOAP definitions
motivate the mapping, O1 proves the matrices; the restriction is Product.
LineCoincidence on lines MUST NOT use BB=1 under OGC: it cannot be true there.
Line support as an Esri boundary awaits a separate qualified profile.

**GOP-013** — The complete accepted relationParam grammar for this subset is:

```text
parameter = ws ( mask | "RELATE" ws "(" ws "G1" ws "," ws "G2" ws "," ws quoted ws ")" ) ws
quoted = '"' mask '"' | "'" mask "'"
mask = nine characters, each one of T F * 0 1 2
ws = zero or more ASCII spaces or tabs
```

Match the entire input, case-sensitively; no escapes, comments, swapped names,
boolean operators, nesting, newline or trailing token. Maximum 256 UTF-8 bytes;
an over-limit input is `resource_limit`, malformed grammar is
`invalid_configuration`. T means nonempty, F empty, a digit exact dimension,
and * any cell. E3 REST documents SCL and RELATE; bare masks and this limited
grammar are Product. This MUST be advertised as a subset, never complete SCL.

## 4. Boolean dimensional profile

**GOP-014** — `esri_dimension_v1` computes set operations then keeps only the
declared output dimension. Union accepts the same Esri type in all inputs,
not merely equal dimension; it is many-to-one. Intersect and difference
are ordered array A against geometry B, with one result per A including empties.
The table is exhaustive (0 point/multipoint, 1 polyline, 2 polygon):

| A dimension | B dimension | intersect output | difference output |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
| 0 | 1 | 0 | 0 |
| 0 | 2 | 0 | 0 |
| 1 | 0 | error | error |
| 1 | 1 | 1 | 1 |
| 1 | 2 | 1 | 1 |
| 2 | 0 | error | error |
| 2 | 1 | error | error |
| 2 | 2 | 2 | 2 |

Errors are `invalid_configuration`. Union outputs dimension 0, 1, or 2 for
homogeneous dimension 0, 1, or 2 inputs respectively; mixed types fail.
Zero-dimensional set results use MultiPoint (even one site), line results
MultiLineString and surface results MultiPolygon at the new neutral boundary;
the adapter maps these to Esri multipoint/paths/rings. No GeometryCollection
is silently emitted. These container choices are Product; E4 defines the
REST dimension restrictions and O1 defines the underlying set operations.

**GOP-015** — Duplicates within a set are removed topologically, without
deduplicating input rows. Crossing lines with point-only intersection yield
an empty line result; edge-touching polygons an empty polygon result. Difference
returns the closure of residual pieces of the selected dimension: [0,3] minus
[1,2] is represented by [0,1] and [2,3], since Simple Features cannot encode
arbitrary open endpoints. Empty is the corresponding typed empty, not a missing
array entry. New neutral results compare topologically; coordinate/part ordering
is not a cross-implementation promise. Adapters claiming exact Esri ordering
need E4 fixture evidence. Product regularization and containers; O1/E4.

## 5. Editing subset

**GOP-016** — `editing_xy_v1` is planar, with explicit units and accuracy.
No repair is implicit. It rejects Z/M/curves and rejects trimExtend attribute
flags 2 or 4 as `unsupported` in XY; 2|4 is `invalid_configuration`.
Unknown flag bits are invalid. Simplify/repair outside this subset is a
separate qualified policy. E5 describes Esri's simplification and attributes;
this narrower product domain MUST be disclosed.

| Rule | Accepted domain and result | Explicit excluded/ambiguous cases | Oracle |
|---|---|---|---|
| GOP-017 offset | Directed single open simple polyline; positive distance right, negative left. rounded, bevelled and mitered joins; simplifyResult=false preserves non-simple linework when structurally valid. Zero distance preserves input. Rounded joins meet GOP-006. | Polygon offset, collapse, simplifyResult=true and join configurations without qualified bevelRatio semantics are unsupported. Default join is rounded; other joins require explicit ratio and qualified E5 fixture. Never repair to hide non-simplicity. | E5 Offset; analytic parallels/arcs; Product subset |
| GOP-018 trimExtend | Single open simple target and single straight directed guide. Unique transverse cut retains the left side; unique forward terminal extension reaches guide. Flags 0,1,8,16 and compatible combinations: 1 moves endpoint instead of adding; 8/16 suppress from/to extension. Unmodified target yields empty polyline in its original slot. | Collinear/tangent/overlapping guide, competing extensions, closed paths, multiple candidate intersections or multipart targets are unsupported. | E5 Trim/Extend; rational intersections; Product subset |
| GOP-019 reshape | Single open simple polyline target and single simple reshaper with exactly two distinct transverse intersections; replace target subpath between them with reshaper subpath, oriented to keep target direction. | Polygon region choice, zero/one/more than two intersections, overlaps, tangencies, closed or multipart target and invalid reconstructed line are unsupported. | E5 Reshape; Product subset; O1 validity |
| GOP-020 autoComplete | Valid disjoint polygons and simple linework; output every bounded unoccupied face having a positive-length edge from new linework and one from an existing polygon. Face interiors are disjoint from occupied area. | Overlapping polygon interiors, pre-existing holes not adjacent to new linework, and line-only faces are not emitted; ambiguous edge provenance is unsupported. Open residual edges produce no face. Output is a list of polygons; no qualifying faces means empty list. | E5 Auto Complete; rational planar face enumeration; Product selection |

No unsupported case is replaced with an area-maximizing or nearest-path
heuristic. AutoComplete output faces are ordered by lexicographic minimum XY
vertex, then area, then canonical counter-clockwise ring sequence to break
ties (holes sorted by the same rule). This is a Product order, not asserted
ArcGIS order. Additional Esri domains require fixtures before exposure.

## 6. Coordinate text profiles

**GOP-021** — Both directions require one of DD, DMS, DDM, UTM, MGRS, USNG,
GARS, GeoRef and a named profile (`standard_v1` or `esri_text_v1`). No format
guessing or abbreviated reference completion. Datum and coordinate order are
explicit: XY is longitude/easting first; canonical angular text is latitude
then longitude. Unknown datum or unavailable transformation is `crs`; no
implicit WGS84 shift. For standard_v1 USNG uses explicit NAD83 or NAD27 per T2;
all other first-profile formats use WGS84. Cell formats identify areas, not
exact points. The selected representative is `center` or `southwest` and is
mandatory in the standard profile. Product; T1–T3, E6.

**GOP-022** — Standard angular text is ASCII, decimal dot, one space between
components, no exponent/locale separators; output uses hemisphere suffixes
and unsigned magnitudes. DD is `d.ddN d.ddE`, DDM `d m.mmN d m.mmE`, DMS
`d m s.ssN d m s.ssE` (N/S and E/W as appropriate). Degrees are integers in
DDM/DMS; leading zeros are allowed on input; minus signs and hemisphere
contradictions are rejected. Minutes/seconds must be in [0,60); at latitude
90 or longitude 180 the lower components are zero. Requested decimal places
are integers 0..8, mandatory. Output rounds half to even with carry into the
next component; negative zero emits N/E zero. Output degrees have no leading
zeros except zero itself; minute and second integer parts have two digits.
The fractional part has exactly the requested number of digits; with zero
decimal places the decimal point is omitted. Parse does not normalize 60.
Product canonical syntax/rounding; T1 chapter 5 and rational sexagesimal arithmetic.

**GOP-023** — The grid requirements are:

| Format | Standard-derived profile | Esri distinction / fixture obligation |
|---|---|---|
| UTM | T1 sections 2-4/2-5 and appendix A, zone 1..60, domain 80S..84N, Norway/Svalbard exceptions; canonical `zone hemisphere easting northing`, metres, integer components rounded half-even. No polar UTM. | utmDefault and utmNorthSouth are distinct modes; exact notation requires E6 fixture. |
| MGRS | T1 chapter 3, appendices A/B/C; UTM/UPS full grid reference, 0..5 digits per coordinate, equal lengths; truncate to containing cell. | E6 old/new/default and zone-01-at-180 modes are explicit, not inferred from name; precision beyond 5 is not standard. |
| USNG | T2 sections 3–5; full zone/band/square, equal 0..5 digits per coordinate, truncate to containing cell; no abbreviated references without context. | Esri precision/defaults are a distinct profile, not the FGDC standard. |
| GARS | T1 section 4-2; 30/15/5 minute cells, legal letters and quadrant/keypad ordering. Standard representative is explicit. | garsDefault/garsLowerLeft select southwest; garsCenter selects center. |
| GeoRef | T1 section 4-3, legal 15-degree/1-degree letters and equal minute digit fields; precision 2..5 digits per coordinate, truncation to cell. | E6 rounding is independent of standard cell containment. |

For standard grids, +180 selects the last longitude cell/zone 60, -180 the
first/zone 1; +90 selects the last latitude cell where the grid is defined.
Elsewhere cell ownership is west/south inclusive and east/north exclusive.
UPS handles polar MGRS; USNG outside T2's domain is unsupported. Cell center
means midpoint in grid coordinates before inverse transformation, not midpoint
of a geographic bounding box. Product edge/representative conventions;
T1/T2 provide the grid systems.

**GOP-024** — esri_text_v1 preserves documented E6 defaults: numOfDigits
MGRS=5, USNG=8, GeoRef=5, DMS=2, DDM=4, DD=6; not applicable for UTM/GARS.
rounding=true for MGRS/USNG/GeoRef; addSpaces=false for MGRS and true for
USNG/UTM. Irrelevant options follow the documented ignore behavior only in
this profile. Exact tie rounding, MGRS/USNG/GeoRef cell representative, accepted
digit extremes and permissive parsing MUST be pinned by an E6 build fixture
before those modes are advertised. Until qualified they return `unsupported`,
not a guessed standard result. DD/DDM/DMS canonical product syntax is not
claimed to match Esri. Product qualification gate; E6 Request parameters.

**GOP-025** — Invalid characters, invalid band/zone/square combinations,
unequal grid digit counts, incomplete strings, contradictory signs, nonfinite
numbers and overflow are `data_mapping`; unknown profile/options are
`invalid_configuration`. Max input per string is 256 UTF-8 bytes; maximum
requested digit count is 8 (format-specific stricter limits still apply).
Exceeding the byte bound is `resource_limit`. Batches are atomic and retain
order/cardinality on success; no silent omission or null substitution.
Text quantization error is separately stated: half a unit of last place for
rounding, less than one for truncation; decoding a cell provides its extent
and representative policy, not centimetric accuracy of the source point.
Product; T1/T2 and analytic quantization oracle, E6 for compatibility fixtures.

## 7. Work, memory, cancellation and errors

**GOP-026** — Every new family API declares finite bounds for actual candidate
evaluations, temporary live bytes, output coordinates/items/bytes and, where
applicable, refinement steps. Zero permits zero work; no all-ones unlimited
sentinel. A candidate evaluation is one actual exact pair test after pruning;
repeat tests, validation passes and tie resolution each count again. A bounding
box visit alone is not an exact pair test; its memory and cancellation still
count. Refinement steps count each evaluated subdivision/iteration. Overflow
fails before the work or reservation. An exact limit is allowed; the next
charge fails. No n²/product/estimated bytes-per-vertex admission rejection is
permitted as a proxy for these new counters. Actual received bytes, counted
coordinates and demonstrably exact output counts may be checked at admission.
Product D6/D8; local oracle PLAN-011–PLAN-016, not an Esri requirement.

**GOP-027** — Live-byte accounting includes decoded input owned by the call,
indexes, allocated capacity, noding graphs, repair/overlay intermediates,
shared backing storage once, output and serialization while live. Reserve
before growth; release only when storage is no longer live. Borrowed input
and host/allocator overhead are separately declared exclusions, not hidden
inside a claimed RSS ceiling. Isolation remains a separate host protection.
Resource limits MUST NOT change geometry precision, remove nearest ties or
deduplicate output rows to obtain success. Product; PLAN sections 4–5 and
Runtime Binding 2.0 RT-024.

**GOP-028** — Every new family API claiming this contract MUST support
cooperative cancellation and deadlines. It checks cancellation and deadline at entry,
before publication, and during every phase: parsing/indexing, noding, refinement,
assembly and serialization. It declares a positive finite maximum work interval
between checks, with units and black-box interruption evidence; an unbounded
primitive cannot be labelled cooperative. This contract fixes no wall-clock
latency. Cancellation is `cancelled`, expired deadline `timeout`, exhausted
work/memory/output `resource_limit`. Runtime deadline stays metadata and
cancellation stays invocation context (RT-006/007/021/023); do not add a second
deadline inside a runtime payload. Product qualification obligation; RT sections
4, 13–14. On a checkpoint where both are observed, expired deadline takes
precedence over cancellation; previously observed validation failures retain
their category. The tie policy is Product.

**GOP-029** — Pure calculations have `remote_effect: none`; failure uses the
last meaningful phase and `retry.kind: never`. No partial success. When wrapped
in data.run publication, the enclosing operation's existing partial/unknown
effect rules prevail; cancellation is not proof of rollback. Domain exclusions
are `unsupported`, unresolved or out-of-domain CRS `crs`, malformed geometry/
text `data_mapping`, invalid parameters `invalid_configuration`. Errors are
bounded and contain no caller coordinates or text. No new error category is
introduced. Oracle ERR-001–ERR-016, RT-024; Product domain classifications.

## 8. Discovery, versions and verification

**GOP-030** — Detailed descriptors MUST distinguish model, supported types,
dimension table, profile/grammar version, datum/SR domain, error guarantee,
repair policy, text precision/representative and limits/cancellation support.
They belong in a versioned component-owned descriptor, following CAP-013;
data.catalog remains the sole detailed kernel source where DT-001 applies.
No untyped shared `plenora.*` attributes are introduced. Register exact new
kernel identities/versions when plan exposure is selected, adding entries as
COMPATIBILITY.md permits or using a successor registry/profile for incompatible
changes; direct kernel design alone is not a new CLI or
runtime operation. Unqualified domains are unavailable/omitted per CAP-009,
not advertised available. Oracle Public Catalogs 2.0 sections 3–6 and CAP-001–013.

**GOP-031** — Existing Arrow/runtime vectors continue to apply. Additional
vectors listed in the oracle plan exercise metadata, CRS and failure envelopes
already checked here. Numeric geometry, resource metering and Esri compatibility
require adopter black-box harnesses and the independent corpus; passing the
repository validator alone MUST NOT be reported as such qualification.
Follow [decision 0024](../../decisions/0024-geometric-operation-expectations.md)
for release/version consequences. Product adoption rule; ADOPTION.md.
