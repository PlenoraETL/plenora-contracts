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
`interop-vector-v1` and 31 vectors in `vectors/interop-v1`:

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
  phase and remote effect of its class (ARROW-013 to ARROW-015); two
  geometry fields against `io.write` and `data.run` (`unsupported`,
  VOC-012); geometry operations on values stored latitude first
  (DT-ARROW-004), on an unknown CRS and on a definition modified under its
  identifier (VOC-015), all `crs`.
- **1 source vector**: a GeoJSON document read by `io.read`, which must
  declare `OGC:CRS84` and `lon_lat` and deliver the stored ordinates
  (VOC-002, VOC-003), with a longitude beyond 90 degrees.

The closed list of transformations (COMP-003) is what a step may change; each
has its basis in a rule: identifiers assigned (VOC-013), large types
narrowed and `srid` added from `EPSG:<n>` (the data-tools output contract,
ARROW-010), EWKB with the field's SRID (VOC-009), axis order `unknown` where
the step cannot establish it (VOC-002), several types widened to `mixed`
where the target keeps them in an unconstrained column (VOC-010), provider
metadata under a reviewed prefix (ARROW-009). Anything else that changes is
a defect of the step.

Chains are checked against the composition matrix (`direct` edges, or a write
then a read of one component on its target); rejections against their input
vector and ARROW-013; sources by reading the document.

### Second reading

An independent reading found, and this decision corrects: a `crs` rejection
did not check that the step computes, so a step that only carries the field
could be expected to refuse it against VOC-004 (now a `data.run` whose plan is
a registered `geo.` kernel); value-level rejections were expected from steps
that carry the bytes unchanged, which VOC-009 exempts (now only decoding
steps); the phases and remote effects of value classes follow the role of
the step; the order of transformations within a step changed the result (now
the order of the table); the comparison of expected tables did not tell `1`
from `1.0` or `true`; any step could declare any transformation (now each has
its owner); the operation-schema class had no check and is left to the
components' vectors; cited rules must exist.

### What the vectors fix that the suite observed differently

- database-tools reads geometry fields without `field_id` and `precision`:
  the vectors expect them (VOC-013, VOC-014), so the gap stays a defect, not
  a transformation.
- database-tools refuses `wkb` with a declared SRID; IO-tools sinks refuse
  `ewkb`: the handoff vectors expect both to pass (VOC-007, VOC-008).
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
- **After:** COMP-001 to COMP-005, schema `interop-vector-v1`, 31 vectors.
- **Compatible:** yes; nothing existing changes meaning.
- **Schemas, examples and profiles:** one schema, one invalid example, 31
  vectors; Composition 1.0 section 6. No catalog, binding or profile
  changes.
- **Adoption impact:** the suite loads `vectors/interop-v1` at a pinned
  revision instead of `suite/attese.py` for these chains and keeps its own
  expectations only for what the section "Left to the suite" lists. The
  libraries adopt the vectors with the changes of decisions 0013 and 0014.
