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
O1; Arrow GEO-001–GEO-020 and REJ-001–REJ-004 still govern Arrow input.

## 2. Models, CRS and accuracy

**GOP-003** — The model MUST be explicit: `planar`, `shortest_geodesic`, or
`preserve_shape`. Planar segments are straight in stored SR coordinates;
length and area use coordinate units and their square. In a geographic SR
they are angular, never metres inferred from degrees. A segment from 179 to
-179 crosses the coordinate plane through 0; it does not wrap at 180. The
poles are coordinate locations in this model, not a topological seam.
No implicit reprojection or geometry-to-geography conversion is permitted.
Product model selection; O1 planar topology and G1/G2 geodesic primitives.

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
area less positive hole areas. Clockwise shell serialization MUST NOT
negate the reported surface area. Larger regions require a distinct explicit
complement policy, outside this first profile. Product; G1 section 6,
G2 Area of a polygon. Antimeridian crossings are continuous;
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
with `crs`. Product subdivision and seam policy; G1 direct/inverse and analytic
inverse-projection path integration.

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
separately per distance. Product domain/order; analytic set definitions; G1 is only a primitive oracle.

**GOP-009** — New projection policies retain rejection outside Web Mercator's
qualified domain; this contract introduces no clamp. Parametric extrapolation
requires explicit opt-in and returns accuracy as unassured outside the
transformation area. Grid extrapolation without covered samples is forbidden.
WKT dialect ingress MUST verify structure, parameters, datum and units against a
published closed alias subset; a matching name is insufficient. The new
`structural_wkt_ingress_v1` product subset uses the WKT1 structure and exact decimal
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
extension of the old Arrow grammar. Product D2–D4; L1 structural CRS rules and analytic projection formulas;
paired canonical/dialect fixtures S03 and A08 are required before release claim.

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
create zero-length pieces. Product D5/D7; O1 convexHull only for dimensional reasoning, analytic projections
and intervals for splitLine. No decision on the service fallback is implied.

## 3. General topology and arbitrary DE-9IM patterns

**GOP-011** — The topology model is planar OGC SFA 1.2.1 DE-9IM,
ordered `II IB IE / BI BB BE / EI EB EE`. Point boundary is empty; line
boundary uses mod 2 over all endpoints of all parts. A closed line has empty
boundary; a shared endpoint with even multiplicity is interior. Polygon
boundary is its rings. Precision is explicit and applied before topology;
no hidden epsilon expands a set. Oracle O1 sections 6.1.7, 6.1.11, 6.1.15.

**GOP-012** — The kernel MUST expose the complete ordered DE-9IM matrix
and evaluation of any valid nine-cell pattern for any pair of supported
Simple Features dimensions, including empty operands. It MUST NOT restrict
patterns to a vendor's named relations. Batched matching retains both input
indexes for each true pair, sorted lexicographically; duplicate input rows
retain their indexes. Standard named predicates, if exposed, use O1 definitions
and publish their dimension-dependent patterns. Empty predicates follow those
definitions; arbitrary patterns always evaluate the actual empty-set matrix.
Product boundary and cardinality; O1 supplies matrix and predicate semantics.

**GOP-013** — A pattern is exactly nine ASCII characters from `TF*012`,
without whitespace, quoting, wrappers or expressions. T matches any nonempty
cell, F an empty cell, a digit its exact dimension, and * any cell. Malformed
patterns are `invalid_configuration`. Every syntactically valid pattern is
accepted, even if no geometry pair can realize it. Multiple alternatives are
expressed by explicit caller composition of pattern results. Service query
languages and their parsing belong to consumers, not this kernel. Product
syntax; O1 matrix matching. See the non-normative
[consumer guide](../../guida/geometria-consumatori.md).

## 4. Boolean operations and dimensional selection

**GOP-014** — The general kernel computes union, intersection and difference
for all supported dimension pairs (0 point, 1 line, 2 surface), under O1 set
semantics. A mixed-dimensional result is explicit: GeometryCollection of
nonempty MultiPoint, MultiLineString and MultiPolygon components in ascending
dimension order; homogeneous results use the corresponding multi container.
Redundant lower-dimensional pieces covered by higher-dimensional components
are removed. Empty general results are empty GeometryCollection. Union is
many-to-one (including empty input); intersection/difference of array A against
B return one result per A, including empties. No dimension pair is rejected
merely to reproduce a service API restriction. Product containers; O1 sets.

**GOP-015** — An explicit optional `output_dimension` (0, 1 or 2) retains
only components of that dimension from the general result; it does not extract
boundaries. Absence preserves all dimensions. A filtered empty is the matching
typed empty multi container. Thus crossing lines intersect at a point by default
and yield empty MultiLineString only when dimension 1 is requested; touching
polygons can intersect along an edge. Difference uses closure of residual
pieces because Simple Features cannot encode arbitrary open endpoints:
[0,3] minus [1,2] gives [0,1] and [2,3]; a line minus an isolated interior point
has the same represented point set after closure. Duplicates within a set
are removed topologically, without deduplicating input rows. Results compare
topologically; coordinate/part order beyond the component dimension order is
not promised. Invalid output dimensions are `invalid_configuration`.
Product regularization, containers and explicit filtering; O1.

## 5. Editing subset

**GOP-016** — `editing_xy_v1` is a product-defined planar domain, with
explicit units and GOP-006 accuracy. It rejects Z/M/curves as `unsupported`.
No repair is implicit. Unknown options and contradictory choices are
`invalid_configuration`; excluded or ambiguous geometric cases are
`unsupported`. Options are semantic values, not service bit flags.

| Rule | Accepted domain and result | Explicit excluded/ambiguous cases | Oracle |
|---|---|---|---|
| GOP-017 offset | Directed single open simple polyline; positive distance right, negative left; butt endpoints. Join is rounded (default), bevelled (straight segment between adjacent offset endpoints), or mitered (intersection of offset supporting lines). For mitered joins a mandatory finite miter limit >=1 bounds vertex-to-intersection distance divided by abs(offset); above it use bevel. Consecutive collinear edges in the same direction remain collinear after offset. Inner joins use supporting-line intersection; outer rounded joins use the circular arc centered at the original vertex. Zero distance preserves input. | Polygon offset, zero-length edges, exact reversal, collapsed/reversed offset segments and joins without a unique construction are unsupported. Non-simple output is preserved when structurally valid; simplification is a separate explicit policy. | Analytic parallels/intersections/arcs; Product |
| GOP-018 trimExtend | Single open simple target and single straight directed guide. Guide denotes its infinite supporting line. One transverse interior cut retains the target portion in the guide's left half-plane. With no cut, extend enabled terminal rays to the guide: start ray opposite first segment, end ray along last segment. Exactly one eligible positive-distance hit is required; zero hits leave target unchanged. Explicit endpoint selection is start, end, both or neither (default both); extension mode is add vertex (default) or move terminal vertex. | Collinearity, tangency, contact at an existing terminal endpoint, overlap, two eligible hits, closed/multipart target, multiple cuts, degenerate or non-simple reconstruction are unsupported. An unchanged target is returned unchanged in its original slot. | Rational intersections/half-planes; Product |
| GOP-019 reshape | Single open simple polyline target and single simple reshaper with exactly two distinct transverse intersections interior to both paths; replace target subpath between them with reshaper subpath, oriented to keep target direction. | Polygon region choice, zero/one/more than two intersections, overlaps, tangencies, closed or multipart target and invalid reconstructed line are unsupported. | Product construction; O1 validity |
| GOP-020 polygon completion | Valid polygons with disjoint interiors and simple linework; node all edges and output every bounded unoccupied face having a positive-length edge from new linework and one from an existing polygon. Face interiors are disjoint from occupied area. | Overlapping polygon interiors are unsupported. Pre-existing holes not adjacent to new linework and line-only faces are not emitted; ambiguous edge provenance (including coincident new/existing edges) is unsupported. Open residual edges produce no face. Output is a list of polygons; no qualifying faces means empty list. | Rational planar face enumeration; Product |

No unsupported case is replaced with an area-maximizing or nearest-path
heuristic. Completion faces are ordered by lexicographic minimum XY vertex,
then area, then canonical counter-clockwise shell sequence starting at its
minimum vertex; holes use clockwise sequences and are sorted by the same key.
These are product constructions, independently verifiable offline.

## 6. Coordinate text profiles

**GOP-021** — Both directions require one of DD, DMS, DDM, UTM, MGRS, USNG,
GARS, GeoRef and the `standard_v1` profile. No format
guessing or abbreviated reference completion. Datum and coordinate order are
explicit: XY is longitude/easting first; canonical angular text is latitude
then longitude. Unknown datum or unavailable transformation is `crs`; no
implicit WGS84 shift. For standard_v1 USNG uses explicit NAD83 or NAD27 per T2;
all other first-profile formats use WGS84. Cell formats identify areas, not
exact points. The selected representative is `center` or `southwest` and is
mandatory when decoding a cell; it is inapplicable to point notations and
to encoding a point into its containing cell. Product; T1–T3.

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

| Format | Standard-derived definition and product syntax |
|---|---|
| UTM | T1 sections 2-4/2-5 and appendix A, zone 1..60, domain 80S..84N, Norway/Svalbard exceptions; canonical `zone hemisphere easting northing`, hemisphere N/S, metres, integer components rounded half-even; explicit resolution must be 1 metre in this first profile. No polar UTM. |
| MGRS | T1 chapter 3, appendices A/B/C; UTM/UPS full grid reference, 0..5 digits per coordinate, equal lengths; truncate to containing cell. Canonical uppercase without spaces. |
| USNG | T2 sections 3–5 and annexes A/B/E; full zone/band/square, equal 0..5 digits per coordinate (product subset; T2 also permits finer precision), truncate to containing cell; no abbreviated references. Canonical uppercase, single spaces between grid-zone designation, square and each coordinate field; omit empty digit fields. NAD27 text ends with ` (NAD 27)`; NAD83 has no suffix. A suffix conflicting with the explicit datum, or a missing NAD27 suffix, is `data_mapping`. Use the same square-letter scheme for both datums as T2 annex E requires. |
| GARS | T1 section 4-2; 30/15/5 minute cells, legal letters and quadrant/keypad ordering. Canonical uppercase 5/6/7 characters for the requested resolution. |
| GeoRef | T1 section 4-3, legal 15-degree/1-degree letters and equal minute digit fields; precision 2..5 digits per coordinate, truncation to cell. Canonical uppercase without spaces. |

For standard grids, +180 selects the last longitude cell/zone 60, -180 the
first/zone 1; +90 selects the last latitude cell where the grid is defined.
Elsewhere cell ownership is west/south inclusive and east/north exclusive.
UPS handles polar MGRS; USNG outside T2's domain is unsupported. Cell center
means midpoint in grid coordinates before inverse transformation, not midpoint
of a geographic bounding box. Product edge/representative conventions;
T1/T2 provide the grid systems.

**GOP-024** — Precision/resolution is explicit for every encoding; there
are no service-derived defaults. Cell formats use containing-cell truncation,
not rounding to a neighboring cell. Angular and UTM output use the rounding
specified above. Decoding a cell requires explicit `center` or `southwest`;
southwest is the minimum easting/northing (or longitude/latitude) corner in
the source grid. Select the representative before any explicit datum
transformation and return the source cell extent as well. Parsing accepts
only the stated canonical syntax (plus angular leading zeros under GOP-022);
no locale, alternate spacing or dialect is inferred. Options inapplicable to
a format are `invalid_configuration`, never silently ignored. Product choices;
T1/T2 and independent rational rounding/cell constructions.

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
Product; T1/T2 and analytic quantization oracle.

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
Product D6/D8; local oracle PLAN-011–PLAN-016.

**GOP-027** — Live-byte accounting includes decoded input owned by the call,
indexes, allocated capacity, noding graphs, repair/overlay intermediates,
shared backing storage once, output and serialization while live. Reserve
before growth; release only when storage is no longer live. Borrowed input
and host/allocator overhead are separately declared exclusions, not hidden
inside a claimed RSS ceiling. Isolation remains a separate host protection.
Exact arbitrary-precision arithmetic whose allocation the implementation does
not control MAY be charged with the actual size of each value immediately
after it is created, instead of before, and released when the value is
dropped, provided that the implementation declares and proves a maximum size
per value that does not depend on the number of input elements. The budget can
then be exceeded by at most that per-value maximum before the call fails with
the typed resource error; the maximum and its derivation are part of the
documented limit. Charging an upper bound of the whole operation (a product of
input sizes or an estimate per vertex) remains forbidden.
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
already checked here. Numeric geometry and resource metering
require adopter black-box harnesses and the independent corpus; passing the
repository validator alone MUST NOT be reported as such qualification.
Follow [decision 0024](../../decisions/0024-geometric-operation-expectations.md)
for release/version consequences. Product adoption rule; ADOPTION.md.
