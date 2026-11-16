# Geometry oracle register and fixture acquisition plan 1.0

Status: qualification plan; no ArcGIS server responses collected
Date: 2026-11-16

This plan supports [Geometry Operations 1.0](../specs/data/GEOMETRY-OPERATIONS-1.0.md)
and [decision 0024](../decisions/0024-geometric-operation-expectations.md).
An expected product outcome is not an observed Esri response. When they differ,
record both; never rewrite a product expectation to match an implementation.

## 1. Source record

All ten input documents were read from `C:/pg/inventario/geometria-motore`.
The family base is `38d68b402389855edbcecb7ce57c31e91282cb4e`.
The owner ratification on 2026-11-16 supersedes the plan's statement that its
recommendations are not yet approved; it does not make uncollected fixtures real.

| File | SHA-256 |
|---|---|
| PIANO.md | c4da081ef1312279e19fa7fab18716cae433edb98fae4b51cee770ec182eeada |
| GEO-booleane-estese.md | 64b72fb70a772b8d7354d48c801c5a43e89698bcf0d6802683bc34e25b46b167 |
| GEO-contratti-limiti.md | 24c7e084270e27d919bc1c6befafb2871f9fe412a556110d272c2f6dc718c702 |
| GEO-coordinate-testuali.md | c8bc8a822afdda87b217fb0ba0000b116dffba9dd4dcfb55ca23535c985a8bf7 |
| GEO-editing.md | 485067d7017a10904557cbcace0fcd1e7480bca5879f7f5056499e5aff8776f8 |
| GEO-geodetica.md | c5ceed8876df7b16a1fb355172c49974f83c2d79d091024d37db12025fabf7d1 |
| GEO-memoria.md | c358453cdd6a0a7444c9617ff51cfc89fc6af5053dc611d2b1774f90ecfe3dce |
| GEO-relazioni.md | 183be1c4f1aebb277ec9f80c76638681ffa310cdf50851be94971ab35b5b5f7b |
| PER_IL_MOTORE-cc7b6fc.md | 746adbb13b2e97c7a7370982e18817ecbac0f522d9dc750577cc90242190b6aa |
| OPERAZIONI-cc7b6fc.md | 2d55275d3fd7ba1a008c2401301e626bd6c38de8f99e350f7d6d08a862f1a2f2 |

The fixed documents are evidence of reported behavior, not independent
mathematical oracles. In particular preserveShape is not geodesic-only
densification, a line's OGC boundary is not its support, and estimated memory
ratios in those documents are not admission bounds.

## 2. Oracle register

ArcGIS entries below refer to **documentation consulted 2026-11-16**, sections
Description and Request parameters unless a narrower section is given. The
introduction version of a REST operation is not a server build. The local
dossiers preserve this consultation record. Relation, both text-conversion
pages and GeographicLib's Python documentation were also read during this step.
No sample-server example URL was followed and no GeometryServer was queried.

| ID | Fixed reference and sections | What it can establish |
|---|---|---|
| O1 | [OGC SFA 1.2.1, 06-103r4](https://docs.ogc.org/is/06-103r4/06-103r4.pdf), 6.1.2 Geometry operations, 6.1.7 Curve, 6.1.11 Polygon, 6.1.15.2 DE-9IM and 6.1.15.3 predicates | Planar topology, boundary and spatial operators; not Esri-specific editing. Archive official PDF and digest before release qualification. |
| G1 | Karney, [Algorithms for geodesics](https://doi.org/10.1007/s00190-012-0578-z), Journal of Geodesy 87 (2013), 43–55; [preprint v2, 2012-03-28](https://arxiv.org/html/1109.4448v2), sections 2, 4–7; [GeodTest 2010](https://geographiclib.sourceforge.io/geod.html), test data | Direct, inverse, area primitives; archive data checksum, not crate-generated expectations. |
| G2 | [GeographicLib Python 2.1](https://geographiclib.sourceforge.io/html/python/geodesics.html), Multiple shortest geodesics, Area of a polygon, Background | Independent fixture generator for geodesic primitives. Pin package digest and driver; not a buffer oracle. |
| T1 | NGA.STND.0037_2.0.0_GRIDS, 2014-02-28, Universal Grids and Grid Reference Systems; sections 2-4/2-5, 3-1–3-5, 4-2, 4-3, chapter 5, appendices A/B/C; [official NGA index](https://earth-info.nga.mil/?action=coordsys&dir=coordsys) | UTM/UPS, MGRS, GARS, GEOREF and angular conventions. Acquire official copy/digest; the dossier used an identified third-party copy. |
| T2 | [FGDC-STD-011-2001 USNG](https://www.fgdc.gov/standards/projects/FGDC-standards-projects/usng/fgdc_std_011_2001_usng.pdf), December 2001, sections 3.1–3.3, 4, 5 | USNG datum, precision and relation to MGRS; USNG is not solely an NGA standard. |
| T3 | [NGA MSP GEOTRANS 3.10](https://earth-info.nga.mil/), release notes, User's and Programmer's Guides | Independent grid conversions, with pinned executable/data/license provenance. GeographicLib C++ UTMUPS/MGRS is an alternative only after an exact version and digest are selected. |
| E0 | [ArcGIS JSON Geometry objects](https://developers.arcgis.com/rest/services-reference/enterprise/geometry-objects/), Spatial reference, Point, Multipoint, Polyline, Polygon | Serialization, rings, SR and empties; no new Z/M promise for an XY product. |
| E1 | [Buffer](https://developers.arcgis.com/rest/services-reference/enterprise/buffer/) (9.3), [Densify](https://developers.arcgis.com/rest/services-reference/enterprise/densify/) (10.0), [Distance](https://developers.arcgis.com/rest/services-reference/enterprise/distance/) (10.0), [Areas and Lengths](https://developers.arcgis.com/rest/services-reference/enterprise/areas-and-lengths/) and [Lengths](https://developers.arcgis.com/rest/services-reference/enterprise/lengths/) (9.3); geodesic, calculationType, units, unionResults | REST model/options; undocumented numerical tie/branch choices require server evidence. |
| E2 | [Project](https://developers.arcgis.com/rest/services-reference/enterprise/project/) (9.3), transformation/transformForward; [Generalize](https://developers.arcgis.com/rest/services-reference/enterprise/generalize/) (10.0), Description/maxDeviation | Projection options and ordinary generalization; not proof of a universal clamp or a particular repair. |
| E3 | [REST Relation](https://developers.arcgis.com/rest/services-reference/enterprise/relation/) (9.3 SP1), relation/relationParam; [SOAP 10.2 relation enum](https://resources.arcgis.com/en/help/soap/10.2/01vp/01vp000000z3000000.htm), members; ArcObjects Java 10.4 esriSpatialRelationEnum; Esri GeoServices REST Specification 1.0 (September 2010), Geometry Service/Relation and 4.2.4.2 | Names and historical SCL; SOAP/ArcObjects behavior is not automatically REST behavior on every build. |
| E4 | [Union](https://developers.arcgis.com/rest/services-reference/enterprise/union/), [Intersect](https://developers.arcgis.com/rest/services-reference/enterprise/intersect/), [Difference](https://developers.arcgis.com/rest/services-reference/enterprise/difference/) (10.0), geometries/geometry | Homogeneous types, dimension restrictions and cardinality; exact ordering/closure needs fixture. |
| E5 | [Offset](https://developers.arcgis.com/rest/services-reference/enterprise/offset/), [Trim/Extend](https://developers.arcgis.com/rest/services-reference/enterprise/trim-extend/), [Reshape](https://developers.arcgis.com/rest/services-reference/enterprise/reshape/), [Auto Complete](https://developers.arcgis.com/rest/services-reference/enterprise/auto-complete/) (10.0); offsetHow/bevelRatio/simplifyResult, extendHow, target/reshaper, polygons/polylines | Editing policy inputs; simplify since 10.1 for reshape is version-sensitive. |
| E6 | [To GeoCoordinateString](https://developers.arcgis.com/rest/services-reference/enterprise/to-geocoordinatestring/) and [From GeoCoordinateString](https://developers.arcgis.com/rest/services-reference/enterprise/from-geocoordinatestring/) (10.3), conversionType/conversionMode/numOfDigits/rounding/addSpaces and JSON response | Eight formats and REST defaults; not a complete permissive-parser grammar. |
| L1 | [Arrow Geometry Semantics 1.0](../specs/data/ARROW-GEOMETRY-SEMANTICS-1.0.md), sections 2–10; [Plan Budget 1.0](../specs/data/PLAN-BUDGET-1.0.md), sections 4–5 | Existing metadata, CRS, precision and budget distinctions. Plan Budget applies only to its declared plan formats, not automatically data-tools profile v3. |
| L2 | [Runtime Binding 2.0](../specs/runtime/RUNTIME-BINDING-2.0.md), sections 4, 13–14; [Typed Errors 1.0](../specs/errors/ERRORS-1.0.md); [Public Catalogs 2.0](../specs/catalogs/PUBLIC-CATALOGS-2.0.md), sections 3–6; [Capability Discovery 2.0](../specs/capabilities/CAPABILITY-DISCOVERY-2.0.md) | Controls, complete results, typed failures and truthful discovery. |

## 3. Fixture record and comparison

Every acquired fixture MUST preserve these fields in a reviewable JSON record
plus raw attachments; this is an acquisition format, not a new runtime schema:

- stable case ID, GOP/D decision IDs, status `planned` or `captured`, origin
  (`analytic`, `reference`, `arcgis`, or `compatibility-6.0.0`);
- exact request bytes and decoded input coordinates/geometries/text, ordered
  parameters including omitted/defaulted values, direction, profile and model;
- input/output SR identifiers **and definitions**, datum/ellipsoid, stored axis
  order, units, precision/repair/quantization and grid representative;
- raw response including error/status, independently derived expected outcome,
  comparison mode (exact bytes, exact indexes/types, topology, scalar interval,
  Hausdorff interval), absolute/relative tolerance with units and justification;
- source title/section/edition, consultation/acquisition UTC time, immutable
  reference tool version, build and SHA-256, driver hash, data-grid hashes;
- for ArcGIS: Enterprise release, full server build/patches, service version,
  service tolerance/resolution settings and transformations, raw response digest;
- for analytic cases: rational construction or formula, arithmetic precision,
  proof/interval bound and independent review; for generated stress cases: seed,
  complete generator and input digest, not just a count or elapsed time.

Discrete types, masks, truth values, indexes, text and error categories compare
exactly. Numeric tolerances are fixed before observing the implementation under
test: analytic rational planar cases use zero where representable; otherwise
outward-rounded intervals. Geodesic fixtures use the G1 dataset's precision
and a separately stated conversion/roundoff allowance; no universal 1 cm² area
tolerance. Topology must match even when coordinate tolerance passes. A server
response without known tolerance/build is exploratory evidence only. Never
regenerate golden answers with the kernel under test. Performance records add
host/build/allocator and live-capacity evidence, not a universal time promise.

## 4. Cases requiring a real ArcGIS server

All rows are **planned**. Choose one Enterprise release/build before capture;
additional builds are separate corpora. Use SR 4326 and a small-coordinate
projected test CRS where suitable; projected fixtures must record full SR and
unit definition, never assume a WKID alone proves datum equivalence.

| ID / rules | Input and parameter variants to capture | Expected comparison / ambiguity resolved | Source |
|---|---|---|---|
| S01 / 003,009 | project (12,41), (12,85.0511), (12,85.06), adjacent representable latitudes, (12,90), negative mirrors; 4326→3857 | Record value/empty/error per item and batch; never presume clamp threshold. Product retains rejection. | E2 Project, E0 |
| S02 / 009 | Explicit parametric transformation inside/on/outside area, inverse direction, crossing geometry; grid with uncovered point | Record selected transformation, accuracy and failure; distinguish extrapolation from missing samples. | E2 |
| S03 / 009 | Complete Esri WKT paired with canonical SR; altered unit, false easting, ellipsoid, datum, false authority, no authority, localized names | Equivalent structure vs false-name acceptance; obtain exact missing WKT examples. | E0/E2 |
| S04 / 010 | Shell/hole where Douglas–Peucker moves hole outside shell; zero/positive deviation and collapse | Raw unrepaired/repaired topology and new vertices; service fallback is separate owner issue. | E2 Generalize |
| S05 / 004–008 | densify equator, pole crossing, 179→-179, exact/near antipodes, multipart and empty; units and max length | Distribution, seam representation, closure, branch/simplify; compare primitive lengths separately to G1. | E1 Densify |
| S06 / 005–008 | buffer point, long line with interior minimum, polygon/hole; r=0, negative, collapse, multiple distances, unionResults; polar cap and large region; inSR/bufferSR/outSR | Dimension, complement, order, empty and error behavior; no vertex-circle substitution. | E1 Buffer |
| S07 / 008 | distance point/line, crossing lines, contained polygon, hole-separated sets, seam and nearly antipodal edges | Minimum over entire sets, not vertices or just boundaries; numeric intervals and empty errors. | E1 Distance |
| S08 / 005–007 | parallel at 60 degrees, projected oblique segment, longitude rectangle, reversed rings, >hemisphere region | planar/geodesic/preserveShape distinction, area sign, unit conversion and domain. | E1 measures |
| S09 / 011–012 | Point inside/on/outside square, line on square edge and through interior, identical polygons; reverse A/B; empty/multipart | In vs Within vs InteriorIntersection truth table and operand orientation. | E3 |
| S10 / 011–012 | Overlapping/identical lines, shared endpoint, closed line, mod-2 shared multipart endpoint; polygon edge/vertex contact; simultaneous overlap and touch | LineCoincidence/LineTouch/PointTouch per dimension; resolve SOAP boundary conflict. Unsupported pairs stay excluded until qualified. | E3 |
| S11 / 013 | Each nine-cell mask; quoted RELATE with single/double quotes; lowercase, spaces/tabs/newlines, G2/G1, boolean expression, escape, missing/extra token | Actual SCL subset vs product grammar; raw error for invalid strings; no full-language claim. | E3 REST/historical SCL |
| S12 / 014–015 | All nine dimension pairs; Point vs MultiPoint union; empty lists; crossing lines, shared polygon edge, collinear intervals, holes, duplicates | Dimension-filtered empties, Point/MultiPoint representation, residual closure, one-result-per-input and vertex/part order. | E4/E0 |
| S13 / 016–017 | Directed (0,0)→(10,0), reversed; right angle, acute miter, self-loop, polygon hole, collapse and zero; all offsetHow, omitted/explicit bevelRatio, simplifyResult both | Sign, defaults (mitered internal 10, bevelled 1.1 in dossier), ignored options, non-simple output. Nonrounded support remains gated by fixture. | E5 Offset |
| S14 / 016,018 | Horizontal target, vertical oriented guide/reverse; short/parallel/collinear targets; both endpoints and multiple guides; flags 0,1,8,16 and combinations, 2,4,2|4 | Retained side, endpoint move/add, unchanged→empty, competing extension tie, XY treatment of attributes. | E5 Trim/Extend |
| S15 / 019 | Two-crossing polyline; polygon with two possible retained regions; 0/1/3+ intersections, tangency, overlap, holes, multipart/closed target | First/last ordering and region choice; preserve excluded-domain errors until qualified. | E5 Reshape |
| S16 / 020 | Adjacent square and three new sides; two candidate faces; pre-existing hole, overlapping polygons, line-only ring, open line, no lines, duplicate edges, point-only contact | Face provenance/selection, exclusion of occupied areas, ordering/cardinality. | E5 Auto Complete |
| S17 / 021–025 | Both directions for all eight formats; defaults vs explicit values; digit counts 0..8 and beyond; rounding on/off, addSpaces on/off, half ties and carry | Exact strings, output XY, ignored parameters, bounds and rounding ties. | E6 |
| S18 / 021–025 | +180/-180, poles, UTM 80S/84N, zone edges, Norway/Svalbard, UPS; MGRS old/new/default and zone01 modes; NAD83/NAD27 USNG | Datum, zone/letter selection, standard vs Esri differences. | E6, T1/T2 for comparison |
| S19 / 021–025 | Coarse MGRS/USNG/GeoRef cell; GARS 001AA and refinements, lowerLeft/center/default | Determine representative point, transform before/after selecting it; capture cell extent. | E6 |
| S20 / 022–025 | Valid-invalid-valid batch, missing/odd digits, bad letters, abbreviated USNG, locale commas, signs/hemispheres, Unicode, NaN, overflow, overlong text | Raw atomic/per-element/null behavior and grammar. Product atomicity remains explicit even if server differs. | E6 |

## 5. Offline specification and independent-reference cases

These cases do not need a server. The expected outcomes below are constructive
or product expectations, not fabricated server observations. Reference tools
are outside the engine and do not become Rust runtime dependencies.

| ID / rules | Construction and expected outcome | Source / tolerance |
|---|---|---|
| A01 / 003 | Segment 179→-179 at y=0 has planar angular length 358, while a shortest equatorial arc spans 2 degrees; unit mismatch rejected | Rational arithmetic; G1 ellipsoid equator length a*pi/90 with interval bound |
| A02 / 004–005 | GeodTest direct/inverse cases, unique near-antipodes, multiple shortest paths, coincident poles, small polar cap, reversed ring, half/greater-than-half area | G1/G2 2.1, dataset digest and scalar intervals; product exclusions exact |
| A03 / 006–007 | Edge length L and maximum h: n=ceil(L/h); every new subedge at most h, same endpoints/closure; empty stays empty; tiny h exhausts actual output budget | G1/G2 independent direct samples, exact counts and bounded distances |
| A04 / 007 | At latitude phi, preserveShape parallel length is N(phi)*cos(phi)*delta-lambda; longitude rectangle area by independent ellipsoid quadrature | Analytic formula and high-precision interval quadrature, separately m and m²; shortest geodesic differs |
| A05 / 008 | Intersecting segments and contained surfaces distance 0; equatorial separated arcs have known gap; point perpendicular to meridian has interior minimum | Analytic cases plus G1; general minima require certified interval global search, never a vertex sample alone |
| A06 / 006,008 | Point geodesic buffer: every boundary point distance r; straight planar buffer parallels/caps; negative erosion of rectangle, collapse | Independent analytic/G1 direct construction and Hausdorff interval; topology checked independently |
| A07 / 009 | Mercator y=R*ln(tan(pi/4+phi/2)); phi=0 and near limits, divergence at poles; Helmert direct/inverse with explicit parameters | High precision formula, transformation uncertainty separate from numeric error |
| A08 / 009 | Valid canonical WKT, same identifier with altered ellipsoid/unit/datum; Esri D_WGS_1984 alias without datum ID; UTM zones 1/32/60 and south false northing, no-ID and contradictory-ID variants | L1 structural exact checks; preserve old Arrow v1 rejection while the explicitly selected new raw-ingress product adapter resolves only the complete matching structure, never the outer name |
| A09 / 010 | 0/1/2/collinear sites and width at threshold±delta; split length 100 at 20 and 60 with attachment 60 and merge 0 vs 60 | Rational hull/projection/intervals; with merge 0 retain both cuts, merge 60 retains 20 |
| A10 / 011–013 | Unit square vs point (1/2,1/2), (0,1/2), (2,2); open line endpoints; shared endpoint parity; X intersection | Hand-derived nine-cell matrices O1; exact truth/mask table independent of engine |
| A11 / 013 | All symbols at every matrix cell, transposition, valid quotes, length 8/10, bad alphabet, 256/257 bytes and compound SCL | Product grammar and O1, exact parse/error and mask outcomes |
| A12 / 014–015 | Sites {(0,0),(1,0)} union {(1,0)}; intervals [0,2] union [1,3]; [0,3] minus [1,2]; perpendicular lines intersect | Exact two sites, [0,3], two closed residuals, empty dimension-1 intersection; O1 plus product dimension filter |
| A13 / 017–018 | Eastward line offset d has y=-d; right angle parallel intersection; vertical guide orientation reversal, unreachable parallel target | Rational parallels/intersections, exact side/type, circular arcs with stated Hausdorff tolerance |
| A14 / 019–020 | Two-crossing replacement with rational intersections; rectangle plus adjacent open three-sided boundary creates one new square | Enumerated paths/faces with exact area and provenance, product selection; excluded cases have exact error |
| A15 / 021–022 | DD/DDM/DMS 12.5 = 12 30 = 12 30 0; 59.999… carries, 60 input rejects, negative-zero canonicalization, half-even ties | Exact decimal fractions, zero text tolerance; quantify rounding unit |
| A16 / 023 | UTM central meridian easting 500000; southern false northing; zone boundaries and Norway/Svalbard; no UTM at poles | T1/T3 3.10, exact metadata and numeric interval; datum grids pinned |
| A17 / 021,023 | MGRS 100km square transitions, northing cycles, prohibited letters, UPS, 0..5 digits; full USNG examples NAD83/NAD27 | T1/T2 official tables, T3 3.10; cell containment and center/SW independent of codec round trip |
| A18 / 023 | GARS 001AA southwest (-180,-90), center (-179.75,-89.75); all quadrants/keypads and final cell; GeoRef 15-degree/1-degree/minute boundaries | T1 sections 4-2/4-3 and rational grid arithmetic, exact cell indexes and angular intervals |
| A19 / 025 | Every codec invalid alphabet/range/count/partial form; valid-invalid-valid batch; byte and digit limits ±1 | Product error rules and T1/T2 lexical/domain checks; exact categories/cardinality |
| A20 / 026–029 | Actual charge count L-1/L/L+1, zero, overflow; repeated candidate/tie/validation visits; reservation release and resize; one pair with huge output | Product metering oracle, deterministic instrumented public-call harness; never derive expected work from n² |
| A21 / 028–029 | Cancellation and deadline during every phase, including index construction and serialization; simultaneous deadline/cancel, no cancel, failure after publication in data.run | L2, deterministic external control and published checkpoint bound; exact error/effect; no invented latency |

## 6. Coverage of inventory items 1–23

The following complements cases A/S above. Existing 6.0.0 artifacts provide
compatibility goldens only; mathematical answers come from the named source.
All stress inputs must be saved completely, not reconstructed from the reported
timing alone. Resource rows use GOP-026–029 and A20/A21 in every phase.

| Inventory | Cases and independent expected result |
|---|---|
| 1–5 CRS/generalize | S01–S04, A01/A07/A08; original default regressions plus explicit new modes. Same XY square in projected/geographic SR has same planar topology and distinct units. |
| 6 make_valid | 9999/10000/10001 segments and 50k with local crossing; rational bow-tie and explicitly different LINEWORK/STRUCTURE outcomes; no conservative-square rejection on new API. |
| 7 split/polygonize | Rational cut rectangle, empty/residual linework, zero/exact/over budget; finite limits and atomic stop. |
| 8 nearest | 5000 sparse sites, all coincident and equidistant; exhaustive small rational distance oracle; keep all ties, inclusive maxDistance, null/empty distinctions. |
| 9–10 hull/splitLine | A09, each cutter alone/together, attachment 0.6/30/60, cut distance 40, threshold equality, endpoints and translated origin. |
| 11 Voronoi | Rational semiplane intersections with declared clipping; duplicates have identical cells but preserved row cardinality; 3000/5000 duplicate stress with pinned full input. |
| 12 split scans | Enumerated zig-zag crossings, duplicate cuts, conserved line length and source indexes; 4000/10000 scale variants, actual temporary reservations. |
| 13 prepared snap | Exhaustive nearest-vertex oracle with equal-distance ties, exact tolerance, duplicates and invalid collapse; batch/prepared results equal generic path. |
| 14 normalized equals | Exhaust all rotations of small rings independently; periodic rings, long common prefixes, -0 and direction; positive tolerance is not assumed transitive. |
| 15 noding | n full horizontal and m vertical lines: n*m crossings, (n-1)*(m-1) bounded faces; repeated/collinear segments, exact capacity stop. |
| 16 pair distance/predicates | Rational pettini and multipoints, interior minima, containment zero, holes; O1 matrices and exhaustive small segment oracle; lower bounds must not prune a true minimum. |
| 17 subdivide | Blocks of lines/points and rational rectangles: per-part maximum, total area/union and provenance; quadrilateral maxVertices=4 nonconvergence explicit. |
| 18 coverage | k identical rectangles gives k*(k-1)/2 overlap issues with exact area; maxIssues ±1 errors without truncation, tolerance is area, no gap search. |
| 19 repair temporaries | Rational bow-tie, holes and crossed comb faces, explicit method/collapsed results; resource stop in both repair methods. |
| 20 fillGaps | Per-polygon morphological closing, slit widths below/equal/above 2t, two separated parcels stay separate; removeOverlaps retains first-input precedence. |
| 21 overlay | n disjoint horizontal strips against m vertical strips: n*m components with exact rational area; one pair alone can explode; source ordering and intermediate unions count. |
| 22 Delaunay | Rational orientation/incircle, t=2n-2-h in general position, duplicate/collinear/cocircular cases; compatibility oracle fixes old diagonal/order where math allows alternatives. |
| 23 interruption | A21 across every advertised cooperative phase; old BoundaryOnly/NonInterruptible labels are not retroactively rewritten. |

## 7. Repository vectors and release gates

New `geometry-step1-*` vectors in `vectors/arrow-data-v1` cover a structurally
matching datum identifier under an Esri name, changed ellipsoid, unsupported
datum alias without ID, and valid empty multiline/multipolygon transport.
They use the existing `arrow-data-vector-v1` schema and evaluator. These are
L1 obligations, not an implementation of the new codecs or geometry algorithms.
New `geometry-step1-*` error envelopes in `vectors/runtime-v2` use existing
data.run version 3 identity for pre-publication resource/cancel/timeout outcomes.
Their validator checks envelopes, not that a kernel really stops before a bound.

No existing vector is edited. No new operation identity, shared attribute,
encoding or wire shape is introduced, so no catalog/schema/binding rewrite is
required now. Registering executable kernels later requires additive registry
entries or a successor registry/profile if incompatible, under Public Catalogs
2.0 and COMPATIBILITY.md; a normative design alone is not availability.

Run the repository's hashed validation dependencies, schema immutability against
the family pin, all unittest gates, comment/documentation gates and validate_specs.
Run coverage as in CI where available. The requested offline/no-GitHub boundary
excludes CI's fetch and live-origin freshness check; report that distinction.
Record commands and actual exit codes in the task report, never substitute
numerical qualification claims for passing document checks.

## 8. Remaining owner actions

1. Decide the interim fate of the existing service generalize fallback (D5
   expressly withheld that choice). The new repair opt-in is already approved.
2. Select the ArcGIS Enterprise release/build and configured service for S01–S20.
   This is needed for a compatibility claim; no server has been queried here.
3. If full Esri compatibility beyond the declared subsets is required, review
   captured divergences: line-boundary mapping, polygon reshape/face selection,
   SCL beyond the small grammar, text parsing/cell representatives, and global
   geodesic regions. These are not a request to reapprove D1–D12. Until then
   the explicit product domains and errors apply.

Reference-tool package/data digests and official standard archives are acquisition
work, not unresolved policy decisions. Checkpoint intervals and numeric bounds
must be published and demonstrated by each adopting artifact; no host timing or
numeric promise has been invented for an absent engine.
