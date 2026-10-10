# Plenora Composition Contract 1.0

Status: normative

Contract identifier: `plenora-composition-v1`

The reviewed matrix is
[`pipelines-v1.json`](../../composition/pipelines-v1.json) and validates against
[`composition-v1.schema.json`](../../schemas/composition-v1.schema.json).

## 1. Purpose

The matrix answers whether the output of one public operation can be supplied
to another without inventing an implicit conversion. It describes boundary
compatibility, not a pipeline engine or scheduler.

## 2. Modes

- `direct`: source and target share the declared interchange contract and
  content type;
- `adapter_required`: a named semantic conversion is required before the
  target can validate the payload;
- `provisional`: an edge is reserved for review but cannot be relied on.

Direct compatibility does not bypass operation-specific validation. Arrow
schema, field identity, nullability, geometry/CRS metadata, provider mapping and
format fidelity constraints still apply.

## 3. Arrow handoff

The stable direct handoffs are:

| Producer | Consumers |
|---|---|
| `io.read` | `data.run`, `database.write` |
| `database.read` | `data.run`, `io.write` |
| `data.run` | `io.write`, `database.write` |

These edges use `plenora-arrow-interchange-v1`. A runtime may move Arrow IPC
bytes, an SDK may use PyArrow and an in-process Rust caller may use Arrow-native
values; the representations are compatible only when the shared metadata and
row meaning survive.

ArcGIS composition is intentionally absent until its component ownership and
public operation contracts are ratified.

## 4. Explicit adapters

`rest.enrich` produces `plenora-rest-execution-result-v1` as JSON. It is not
directly composable with `data.run`, which consumes typed Arrow inputs. A
JSON-to-Arrow adapter consumes the complete REST result, including ordering and
partial errors, and must explicitly own field type inference or declaration,
nullability, ordering and per-record error policy. No component may silently
infer this edge from matching field names.

Storage operations now define opaque artifact source and sink references, but
those references and their bounded content type, size and optional SHA-256
metadata do not define the bytes' semantic content. No storage edge is
therefore added to the reviewed matrix until both endpoints share a reviewed
content and integrity contract.

## 5. Validation

For a `direct` edge, the semantic validator checks that:

1. both operations and versions exist in their target catalogs;
2. the source output and target input both declare the edge's interchange
   contract;
3. both sides declare the edge's content type.

This prevents documentation from claiming composition that the machine
catalogs do not support.

For an `adapter_required` edge, the named contract MUST be either the source
operation's output contract or an interchange contract declared by that
output. The adapter owns the conversion from that complete source result to a
contract accepted by the target.

## 6. Interoperability vectors

The vectors in [`vectors/interop-v1`](../../vectors/interop-v1/) fix what a
pipeline of public operations must deliver, so that a suite running the same
chain through every surface (Rust, Python, CLI, runtime) compares each
result with one expectation instead of with another implementation. Their
shape is
[`interop-vector-v1.schema.json`](../../schemas/interop-vector-v1.schema.json).

**COMP-001** — A vector is one of three kinds:

- `handoff`: an input table (an `expect: valid` vector of
  [`vectors/arrow-data-v1`](../../vectors/arrow-data-v1/)), a chain of steps
  and the exact table the chain delivers;
- `rejection`: an input table, one step and the error axes that step reports
  (Arrow Interchange 1.0, ARROW-013 to ARROW-015);
- `source`: a source document in a format whose specification fixes the
  coordinate order, the reading step and the coordinates and axis order it
  must declare (Arrow Vocabulary 1.0, VOC-002, VOC-003).

**COMP-002** — Consecutive steps of a chain are a `direct` edge of the
matrix, or a write followed by a read of the same component on the same
target (`via: target`). The first step reads the input table as Arrow IPC;
the output of a chain is the table its last step delivers or writes as Arrow
IPC. Step parameters such as a plan or a sink format are abstract: the
harness maps them to each surface's spelling.

**COMP-003** — A step changes the table only through the transformations it
declares, from this closed list, applied in the order of the table; only the
component and operation the basis names may declare one (`assign_field_ids`
any step, `large_to_standard` and `srid_from_epsg_identifier` `data.run`,
the four others `database.read`). Everything else, data and metadata, is
compared exactly and by type (`1`, `1.0` and `true` differ), byte for byte
for WKB:

| transformation | effect | basis |
|---|---|---|
| `assign_field_ids` | a field without `plenora.field_id` receives the smallest free identifier, in field order | VOC-013 |
| `large_to_standard` | `large_utf8` becomes `utf8` and `large_binary` becomes `binary` | the data-tools output contract (ARROW-010) |
| `srid_from_epsg_identifier` | a geometry field with a resolved `EPSG:<n>` and no `srid`, `n` within 32 bits, receives `srid=<n>` | the data-tools output contract (ARROW-010) |
| `ewkb_with_field_srid` | geometry values become EWKB carrying the field's `srid` on the outermost geometry, in the same byte order, and `encoding` becomes `ewkb` | VOC-009 |
| `axis_order_unknown` | `axis_order` becomes `unknown` on a geometry field with a declared CRS: the step cannot establish the stored order | VOC-002 |
| `several_types_to_mixed` | a geometry field declared `exact` with several types becomes `mixed` without a list: the target keeps them in an unconstrained column | VOC-010 |
| `provider_metadata` | keys under the step's reviewed provider prefix are added; they are verified by the provider's own vectors, not by this one | ARROW-009 |

A loss that is not in the list is a defect of the step, never an expected
difference.

**COMP-004** — A `rejection` vector whose input is an `invalid` data vector
expects that vector's category and the rule that decides it; when the rule is
a value class (VOC-008, VOC-009, VOC-011), the step decodes values: it
computes with coordinates or writes them to a target that interprets
geometry, never one that carries the bytes (VOC-009). A `rejection` of a
valid input names its class: `support` (`unsupported`, with VOC-012 or VOC-010
shown by the input) or `crs` for a step that computes, a `data.run` whose plan
is a registered `geo.` kernel, and cannot verify or use the CRS (VOC-015, or
DT-ARROW-004); a step that only carries or records the CRS is never expected
to refuse it (VOC-004). The schema classes expect phase `validate` and remote
effect `none`; a value class expects `read` for a reading step, or `write`
with remote effect `none` or `rolled_back` for a writing step. Every
rejection expects `retry.kind: never` and the CLI exit code 3. The
operation-schema class of ARROW-013 depends on a target or a plan that the
vectors of this version do not describe; the components' own vectors
exercise it.

**COMP-005** — The validator recomputes every expected table from the input
and the declared transformations, checks every chain against the matrix and
every rejection against the input vector and ARROW-013, and reads every
source document itself.
