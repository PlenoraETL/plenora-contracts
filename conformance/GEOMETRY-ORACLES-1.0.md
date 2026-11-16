# Geometry oracle register and fixture acquisition plan 1.0

Status: offline qualification plan; fixtures not yet acquired
Date: 2026-11-16

This plan supports [Geometry Operations 1.0](../specs/data/GEOMETRY-OPERATIONS-1.0.md)
and [decision 0024](../decisions/0024-geometric-operation-expectations.md).
All engine expectations derive offline from standards, independent reference
implementations, analytic constructions or declared product semantics. Never
rewrite an expectation to match the implementation under test. Service API
compatibility is outside this engine corpus.

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

References are fixed by edition/version below. Acquisition must archive the
source, tool and data digests before qualification. A documentation link is
not evidence that a fixture has already been generated or verified.

| ID | Fixed reference and sections | What it can establish |
|---|---|---|
| O1 | [OGC SFA 1.2.1, 06-103r4](https://docs.ogc.org/is/06-103r4/06-103r4.pdf), 6.1.2 Geometry operations, 6.1.7 Curve, 6.1.11 Polygon, 6.1.15.2 DE-9IM and 6.1.15.3 predicates | Planar topology, boundary and spatial operators; editing semantics are declared by this product. Archive official PDF and digest before release qualification. |
| G1 | Karney, [Algorithms for geodesics](https://doi.org/10.1007/s00190-012-0578-z), Journal of Geodesy 87 (2013), 43–55; [preprint v2, 2012-03-28](https://arxiv.org/html/1109.4448v2), sections 2, 4–7; [GeodTest 2010](https://geographiclib.sourceforge.io/geod.html), test data | Direct, inverse, area primitives; archive data checksum, not crate-generated expectations. |
| G2 | [GeographicLib Python 2.1](https://geographiclib.sourceforge.io/html/python/geodesics.html), Multiple shortest geodesics, Area of a polygon, Background | Independent fixture generator for geodesic primitives. Pin package digest and driver; not a buffer oracle. |
| T1 | NGA.STND.0037_2.0.0_GRIDS, 2014-02-28, Universal Grids and Grid Reference Systems; sections 2-4/2-5, 3-1–3-5, 4-2, 4-3, chapter 5, appendices A/B/C; [official NGA index](https://earth-info.nga.mil/?action=coordsys&dir=coordsys) | UTM/UPS, MGRS, GARS, GEOREF and angular conventions. Acquire official copy/digest; the dossier used an identified third-party copy. |
| T2 | [FGDC-STD-011-2001 USNG](https://www.fgdc.gov/standards/projects/FGDC-standards-projects/usng/fgdc_std_011_2001_usng.pdf), December 2001, sections 3.1–3.3, 4, 5 and annexes A/B/E | USNG datum, precision and relation to MGRS; USNG is not solely an NGA standard. |
| T3 | [NGA MSP GEOTRANS 3.10](https://earth-info.nga.mil/), release notes, User's and Programmer's Guides | Independent grid conversions, with pinned executable/data/license provenance. GeographicLib C++ UTMUPS/MGRS is an alternative only after an exact version and digest are selected. |
| L1 | [Arrow Geometry Semantics 1.0](../specs/data/ARROW-GEOMETRY-SEMANTICS-1.0.md), sections 2–10; [Plan Budget 1.0](../specs/data/PLAN-BUDGET-1.0.md), sections 4–5 | Existing metadata, CRS, precision and budget distinctions. Plan Budget applies only to its declared plan formats, not automatically data-tools profile v3. |
| L2 | [Runtime Binding 2.0](../specs/runtime/RUNTIME-BINDING-2.0.md), sections 4, 13–14; [Typed Errors 1.0](../specs/errors/ERRORS-1.0.md); [Public Catalogs 2.0](../specs/catalogs/PUBLIC-CATALOGS-2.0.md), sections 3–6; [Capability Discovery 2.0](../specs/capabilities/CAPABILITY-DISCOVERY-2.0.md) | Controls, complete results, typed failures and truthful discovery. |

## 3. Fixture record and comparison

Every acquired fixture MUST preserve these fields in a reviewable JSON record
plus raw attachments; this is an acquisition format, not a new runtime schema:

- stable case ID, GOP/D decision IDs, status `planned` or `captured`, origin
  (`analytic`, `reference`, `product-semantics`, or `compatibility-6.0.0`);
- exact request bytes and decoded input coordinates/geometries/text, ordered
  parameters including omitted/defaulted values, direction, profile and model;
- input/output SR identifiers **and definitions**, datum/ellipsoid, stored axis
  order, units, precision/repair/quantization and grid representative;
- raw response including error/status, independently derived expected outcome,
  comparison mode (exact bytes, exact indexes/types, topology, scalar interval,
  Hausdorff interval), absolute/relative tolerance with units and justification;
- source title/section/edition, consultation/acquisition UTC time, immutable
  reference tool version, build and SHA-256, driver hash, data-grid hashes;
- for analytic cases: rational construction or formula, arithmetic precision,
  proof/interval bound and independent review; for generated stress cases: seed,
  complete generator and input digest, not just a count or elapsed time.

Discrete types, masks, truth values, indexes, text and error categories compare
exactly. Numeric tolerances are fixed before observing the implementation under
test: analytic rational planar cases use zero where representable; otherwise
outward-rounded intervals. Geodesic fixtures use the G1 dataset's precision
and a separately stated conversion/roundoff allowance; no universal 1 cm² area
tolerance. Topology must match even when coordinate tolerance passes. A reference
result without provenance and justified tolerance is exploratory evidence only. Never
regenerate golden answers with the kernel under test. Performance records add
host/build/allocator and live-capacity evidence, not a universal time promise.

## 4. Offline reformulation of the twenty former capture groups

All groups remain **planned**, with no server acquisition dependency. IDs S01–S20
are retained solely for traceability to the original plan. The table records the
offline replacement and why service-only variants are removed; A cases below
supply reusable constructions. Full coordinates, parameters and derivations must
be saved before these groups count as captured evidence.

| ID / rules | Offline inputs | Independent expectation / disposition |
|---|---|---|
| S01 / 003,009 | Mercator at 0, 85.0511, 85.06, adjacent representable latitudes, poles and negative mirrors | A07 analytic formula and existing qualified rejection domain; no clamp inferred. |
| S02 / 009 | Parametric transformation inside/on/outside area, inverse and uncovered grid points | A07 explicit Helmert parameters, inverse composition and unassured extrapolation; missing grid samples fail. |
| S03 / 009 | Canonical/dialect WKT; changed units, parameters, ellipsoid, datum, missing/contradictory IDs | A08/L1 exact structural identity; names alone never establish equivalence. |
| S04 / 010 | Generalization crossing a hole/shell, collapse, zero/positive deviation | Declared repair method and certified displacement; rational validity checks. Existing fallback remains separate D5 decision. |
| S05 / 004–008 | Equator, poles, seam, near/exact antipodes, multipart/empty densify | A02–A04/G1/G2 independent arc-length divisions, closure, branch exclusions and error bounds. |
| S06 / 005–008 | Point/line/polygon buffers, zero/negative radii, collapse, multiple distances, polar cap | A06 analytic metric neighborhoods and G1 direct samples with certified Hausdorff bound; product order/domain. |
| S07 / 008 | Interior minima, crossing lines, containment, holes, seam and antipodal edges | A05 analytic minima or certified interval search; empty operand error. |
| S08 / 005–007 | Latitude 60 parallel, projected oblique segment, rectangle and reversed rings | A04 independent quadrature, unit conversion, signed area and explicit region exclusions. |
| S09 / 011–012 | Point inside/on/outside square, boundary/interior lines, identical polygons, reversal/empties | A10/O1 full matrices and standard predicates. Vendor named-relation truth tables removed: consumer responsibility. |
| S10 / 011–012 | Identical/overlapping lines, endpoints, closed lines, multipart parity, edge/vertex contacts | A10/O1 mod-2 boundary matrices in all dimensions. Service boundary conventions removed from engine qualification. |
| S11 / 013 | All six pattern symbols in all nine positions, reversal, malformed length/alphabet | A11 exact pattern matching. Quoted RELATE/SCL parsing removed: consumer language, not kernel input. |
| S12 / 014–015 | All nine dimension pairs, mixed union, empty inputs, crossing lines, polygon edge, residual intervals | A12/O1 exact sets, closure, general collections and explicit dimension filter; service restrictions/order removed. |
| S13 / 016–017 | Eastward/reversed offset, right angle, acute miter, zero, collapse and self-intersection | A13 parallels/arcs, miter length ratio below/equal/above explicit limit and bevel fallback. Service defaults removed. |
| S14 / 016,018 | Directed guide/reversal, cuts, start/end rays, no hit/two hits, parallel/collinear paths | A13 rational half-planes/intersections and explicit endpoint/move/add semantics. Service bit flags removed. |
| S15 / 019 | Two crossings, 0/1/3+ crossings, tangency/overlap, polygon/multipart/closed targets | A14 exact subpath replacement or documented unsupported errors; no external region-selection heuristic. |
| S16 / 020 | Adjacent square plus three sides, two faces, holes, overlap, line-only rings, open/duplicate edges | A14 rational face enumeration, edge provenance, ordering and explicit ambiguity errors. |
| S17 / 021–025 | Eight formats both directions, precision bounds, half ties, carry, inapplicable options | A15–A19/T1/T2/T3 canonical strings and product errors. Service defaults/ignored options removed. |
| S18 / 021–025 | Longitude endpoints, poles, UTM limits/zones, Norway/Svalbard, UPS, NAD83/NAD27 | A16–A17/T1/T2/T3 grid/datum choices; service-specific conversion modes removed. |
| S19 / 021–025 | Coarse cells, GARS 001AA/refinements, center/southwest, explicit transformation | A17–A18 rational cell extents, representative in source grid before transformation; no implicit default. |
| S20 / 022–025 | Valid-invalid-valid batch, odd digits, illegal letters, partial references, locale/Unicode/overflow | A19 exact lexical/domain errors, byte bounds and product atomicity; service per-item behavior removed. |

## 5. Offline specification and independent-reference cases

These cases do not need a server. The expected outcomes below are constructive
or product expectations, not observations invented for the engine under test. Reference tools
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
| A08 / 009 | Valid canonical WKT, same identifier with altered ellipsoid/unit/datum; WKT dialect D_WGS_1984 alias without datum ID; UTM zones 1/32/60 and south false northing, no-ID and contradictory-ID variants | L1 structural exact checks; preserve old Arrow v1 rejection while the explicitly selected new raw-ingress product adapter resolves only the complete matching structure, never the outer name |
| A09 / 010 | 0/1/2/collinear sites and width at threshold±delta; split length 100 at 20 and 60 with attachment 60 and merge 0 vs 60 | Rational hull/projection/intervals; with merge 0 retain both cuts, merge 60 retains 20 |
| A10 / 011–013 | Unit square vs point (1/2,1/2), (0,1/2), (2,2); open line endpoints; shared endpoint parity; X intersection | Hand-derived nine-cell matrices O1; exact truth/mask table independent of engine |
| A11 / 013 | All symbols at every matrix cell, transposition, length 8/10, bad alphabet, whitespace, quotes and wrappers rejected | Product grammar and O1, exact parse/error and mask outcomes |
| A12 / 014–015 | Sites {(0,0),(1,0)} union {(1,0)}; intervals [0,2] union [1,3]; [0,3] minus [1,2]; perpendicular lines intersect | Exact two sites, [0,3], two closed residuals, point intersection by default and empty dimension-1 intersection only with explicit filter; all nine dimension pairs, mixed collections and typed empties; O1 plus product closure/filter |
| A13 / 017–018 | Eastward line offset d has y=-d; right angle parallel intersection; vertical guide orientation reversal, unreachable parallel target | Rational parallels/intersections, exact side/type, circular arcs with stated Hausdorff tolerance |
| A14 / 019–020 | Two-crossing replacement with rational intersections; rectangle plus adjacent open three-sided boundary creates one new square | Enumerated paths/faces with exact area and provenance, product selection; excluded cases have exact error |
| A15 / 021–022 | DD/DDM/DMS 12.5 = 12 30 = 12 30 0; 59.999… carries, 60 input rejects, negative-zero canonicalization, half-even ties | Exact decimal fractions, zero text tolerance; quantify rounding unit |
| A16 / 023 | UTM central meridian easting 500000; southern false northing; zone boundaries and Norway/Svalbard; no UTM at poles | T1/T3 3.10, exact metadata and numeric interval; datum grids pinned |
| A17 / 021,023 | MGRS 100km square transitions, northing cycles, prohibited letters, UPS, 0..5 digits; full USNG examples NAD83/NAD27, required NAD27 suffix and datum conflicts, common square-letter scheme, product precision limit | T1/T2 official tables, T3 3.10; cell containment and center/SW independent of codec round trip |
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
matching datum identifier under a dialect name, changed ellipsoid, unsupported
datum alias without ID, and valid empty multiline/multipolygon transport.
They use the existing `arrow-data-vector-v1` schema and evaluator. These are
L1 obligations, not an implementation of the new codecs or geometry algorithms.
New `geometry-step1-*` error envelopes in `vectors/runtime-v2` use existing
data.run version 3 identity for pre-publication resource/cancel/timeout outcomes.
Their validator checks envelopes, not that a kernel really stops before a bound.

The three draft WKT vectors are renamed to `wkt-dialect-identified-datum`,
`wkt-dialect-wrong-ellipsoid` and `wkt-datum-alias-unverified` (with the
`geometry-step1-` prefix); their bytes and expectations are unchanged.
D_WGS_1984 is retained as real dialect data: the tests establish general
structural identity, rejection of a contradictory ellipsoid and rejection of
an unverified alias in the existing Arrow boundary. No baseline vector is edited. No new operation identity, shared attribute,
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
2. Future broader domains (polygon reshape, global geodesic regions or more
   WKT dialects) need explicit semantics and offline qualification before exposure.
   They do not block the declared domain or require reapproval of D1–D12.

Reference-tool package/data digests and official standard archives are acquisition
work, not unresolved policy decisions. Checkpoint intervals and numeric bounds
must be published and demonstrated by each adopting artifact; no host timing or
numeric promise has been invented for an absent engine.
