# 0018: Interoperability vectors for the cross-library suite

Status: accepted

Date: 2026-10-10

## Context

The interoperability suite (`plenora-interop`) runs the same chains through
IO-tools, data-tools and database-tools on three roads (Rust, Python, CLI)
and compares each hop with an expectation. Today the expectations live in the
suite (`suite/attese.py`), written from the libraries' own documentation and
from observation: the suite decides what a correct chain delivers, and a
transformation observed in a library can become "expected" because it was
observed. The analysis of 2026-10-10 proposed to keep harness and CI in the
suite and to move the normative part, fixtures, expected tables and expected
errors, into this repository.

## Decision

Composition 1.0 gains section 6 (COMP-001 to COMP-005), schema
`interop-vector-v1` and 40 vectors in `vectors/interop-v1`:

- **7 handoff vectors**: io→data→io on points, on several geometry types, on a
  CRS with a definition and on EWKB; io→database→io; io→data→database→io;
  database→data→io. The input is a valid vector of `vectors/arrow-data-v1`;
  the expected table is recomputed by the validator from the input and the
  transformations each step declares.
- **23 rejection vectors**: three schema-level invalid inputs (contract
  version 2, version absent, contradictory definition) against `io.read`,
  `data.run` with the identity plan and `database.write`; three value-level
  ones (EWKB SRID mismatch, type outside the declaration, truncated WKB)
  against the steps that decode values, `data.run` with `geo.centroid`,
  `database.write` and `io.write` to GeoPackage; each with the category,
  phase and remote effect of its class (REJ-001 to REJ-003); two
  geometry fields against `io.write` and `data.run` (`unsupported`,
  GEO-012); geometry operations on values stored latitude first
  (DT-ARROW-004), on an unknown CRS and on a definition modified under its
  identifier (GEO-015), all `crs`.
- **1 source vector**: a GeoJSON document read by `io.read`, which must
  declare `OGC:CRS84` and `lon_lat` and deliver the stored ordinates
  (GEO-002, GEO-003), with a longitude beyond 90 degrees.

The closed list of transformations (COMP-003) is what a step may change; each
has its basis in a rule: identifiers assigned (GEO-013), large types
narrowed and `srid` added from `EPSG:<n>` (the data-tools output contract,
ARROW-010), EWKB with the field's SRID (GEO-009), axis order `unknown` where
the step cannot establish it (GEO-002), several types widened to `mixed`
where the target keeps them in an unconstrained column (GEO-010), provider
metadata under a reviewed prefix (ARROW-009). Anything else that changes is
a defect of the step.

Chains are checked against the composition matrix (`direct` edges, or a write
then a read of one component on its target); rejections against their input
vector and REJ-001; sources by reading the document.

### Second reading

An independent reading found, and this decision corrects: a `crs` rejection
did not check that the step computes, so a step that only carries the field
could be expected to refuse it against GEO-004 (now a `data.run` whose plan is
a registered `geo.` kernel); value-level rejections were expected from steps
that carry the bytes unchanged, which GEO-009 exempts (now only decoding
steps); the phases and remote effects of value classes follow the role of
the step; the order of transformations within a step changed the result (now
the order of the table); the comparison of expected tables did not tell `1`
from `1.0` or `true`; any step could declare any transformation (now each has
its owner); the operation-schema class had no check and is left to the
components' vectors; cited rules must exist.

### Arrow Geometry Semantics 1.0 and the third reading (Codex)

The vectors bind the components that claim Arrow Geometry Semantics 1.0
([decision 0013](0013-geometry-vocabulary-semantics.md)). A third reading
found, and this decision corrects:

- the rejection of an invalid input was taken from the input alone, before
  the operation: every step is now evaluated with the single order of
  REJ-002, the operation included (an unknown CRS and a truncated value give
  `crs` to a geometry operation; two geometry fields and a truncated value
  give `unsupported` to a sink limited to one), with vectors for both;
- the conversion of ISO WKB to EWKB set the SRID flag on an ISO dimension
  code, a combination GEO-011 forbids: the code becomes the extended Z and
  M flags first, with a POINT Z vector;
- `data.run` must keep the acceptance of DT-ARROW-003: the evaluation of a
  `data.run` step applies it, and a handoff starts from a field without
  `precision` that `data.run` completes (`complete_missing_geometry_keys`);
- provider keys were neither compared nor represented: `expected_output`
  lists them in `delegated_metadata`, which the harness removes before the
  exact comparison;
- a step names the limits its component declares (`one_geometry_field`,
  `one_geometry_type`), instead of the validator inferring them;
- a projected source with a known order: a CSV whose read request states
  UTM 32N easting first, with a northing beyond the range of eastings;
- the validator's messages name rules and paths, never values.

### Fourth reading (Codex)

Corrected: the contract version is judged before the profile's acceptance,
so nothing of an unsupported version is interpreted; a computing step
refuses `geography` semantics and non-planar edges as `unsupported` after the
CRS class and before the values (DT-ARROW-004), with vectors; the profile's
completion states `axis_order` `unknown` when a CRS is declared without it,
with a chain; delegated provider keys are recorded where the provider
delivers them and must survive every later step unchanged; the paths of the
validator's messages name data keys by position. The vectors illustrate the
rules and do not attest full coverage (COMP-005 lists what they leave out).

### What the vectors fix that the suite observed differently

- database-tools reads geometry fields without `field_id` and `precision`:
  the vectors expect them (GEO-013, GEO-014), so the gap stays a defect, not
  a transformation.
- database-tools refuses `wkb` with a declared SRID; IO-tools sinks refuse
  `ewkb`: the handoff vectors expect both to pass (GEO-007, GEO-008).
- IO-tools declares `lat_lon` for every `EPSG:4326`: the handoff and source
  vectors expect the stored order.
- The categories of the rejection vectors are those of decision 0014.

### Left to the suite

Provider metadata values, GeoPackage and other binary sources, database
types without a mapping, the uncertain outcome of a commit (a proxy that
drops the confirmation) and the sentinels that check that no value reaches a
message: they need a running service or a binary fixture, and the libraries'
own vectors own them.

## Alternatives

- **Everything in the suite.** The suite would remain the only judge of what
  a chain must deliver, and a library could not run the same expectations in
  its own tests.
- **Everything here, harness included.** This repository validates documents
  with JSON Schema and Python; building three Rust workspaces and starting
  databases does not belong to its gates.
- **Byte digests of the produced IPC as expectations.** Batch partitioning,
  padding and metadata order differ between implementations; the vectors fix
  the logical table, which the suite canonicalizes.

## Change statement

- **Consumers affected:** the interoperability suite; each library, which can
  run the vectors through its public boundary.
- **Before:** expectations owned by the suite.
- **After:** COMP-001 to COMP-005, schema `interop-vector-v1`, 40 vectors.
- **Compatible:** yes; nothing existing changes meaning.
- **Schemas, examples and profiles:** one schema, one invalid example, 40
  vectors; Composition 1.0 section 6. No catalog, binding or profile
  changes.
- **Adoption impact:** the suite loads `vectors/interop-v1` at a pinned
  revision instead of `suite/attese.py` for these chains and keeps its own
  expectations only for what the section "Left to the suite" lists. The
  libraries adopt the vectors with the changes of decisions 0013 and 0014.
