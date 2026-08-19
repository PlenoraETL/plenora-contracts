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
| `arcgis.read` | `data.run` |
| `data.run` | `io.write`, `database.write`, `arcgis.write` |

These edges use `plenora-arrow-interchange-v1`. A runtime may move Arrow IPC
bytes, an SDK may use PyArrow and an in-process Rust caller may use Arrow-native
values; the representations are compatible only when the shared metadata and
row meaning survive.

## 4. Explicit adapters

`rest.enrich` produces `plenora-rest-execution-result-v1` as JSON. It is not
directly composable with `data.run`, which consumes typed Arrow inputs. A
JSON-to-Arrow adapter consumes the complete REST result, including ordering and
partial errors, and must explicitly own field type inference or declaration,
nullability, ordering and per-record error policy. No component may silently
infer this edge from matching field names.

Storage composition remains undefined until the provisional storage catalog is
replaced by reviewed operations and artifact-reference contracts.

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
