# Plenora REST-to-Arrow Adapter Contract 1.0

Status: normative

Contract identifier: `plenora-rest-arrow-adapter-v1`

The declaration is defined by
[`rest-arrow-adapter-v1.schema.json`](../../schemas/rest-arrow-adapter-v1.schema.json)
and the conformance vectors by
[`rest-arrow-adapter-vector-v1.schema.json`](../../schemas/rest-arrow-adapter-vector-v1.schema.json).

## 1. Purpose and ownership

The composition edge from `rest.enrich` to `data.run` is `adapter_required`
([Composition 1.0](COMPOSITION-1.0.md) section 4): a REST result is JSON, and
`data.run` consumes typed Arrow. This contract fixes the minimum an adapter
declares and how it converts, so that two adapters given the same
declaration and the same REST result produce the same table or the same
error.

**RA-001** — The adapter belongs to the application that composes the two
operations. No component is required to implement it, and no component
infers it from matching field names. An adapter that claims this contract
converts exactly as this document states, from a declaration it receives
explicitly; it never infers a type, a nullability or an order.

## 2. Input

**RA-002** — The adapter consumes one complete
`plenora-rest-execution-result-v1` (owned by rest-tools) and reads only its
`status`, `output` and `errors`, in this order. A `status` the declaration
does not list in `accept_status` fails with `execution`: `failed` is never
accepted, even when a declaration lists it, and `partial` only when the
declaration lists it. Then the output must be of type `records`; any other
output type fails with `schema`. A partial result carries
the REST errors in its own `errors`; the adapter reports their number next
to its table, so the partial outcome is never read as complete (SURF-014).

## 3. Declaration

**RA-003** — The declaration lists the output fields, each with a unique
name, a unique `plenora.field_id`, an RFC 6901 JSON Pointer into a record,
an Arrow type among `bool`, `int64`, `float64` and `utf8`, and a
nullability. It also states `accept_status`, `on_record_error` (`fail` or
`exclude`) and `undeclared_members` (`ignore` or `reject`). A declaration
with a repeated name or identifier, a field named `@undeclared` (reserved
by RA-006), or a pointer that is not a non-empty
RFC 6901 pointer (it starts with `/`, and every `~` is followed by `0` or
`1`), fails with `invalid_configuration` before any record is read.

## 4. Order

**RA-004** — Row *i* of the table is the *i*-th record of `output.records`
that is not excluded. The adapter does not sort, deduplicate or reorder.

## 5. Conversion

**RA-005** — For each record and each declared field, in declaration order,
the pointer is evaluated on the record:

- a member absent from an object, or an array index beyond the array, gives
  a missing value; a missing value or JSON `null` is null, admitted only by a
  nullable field (otherwise cause `adapter.null_in_non_nullable`);
- traversing a string, number, boolean or null before the last token, or an
  array token that is not a decimal index without leading zeros, is a record
  error (`adapter.path_not_traversable`);
- `bool` accepts only `true` and `false`;
- `int64` accepts only a JSON number written as an integer, without fraction
  or exponent, within the signed 64-bit range (`adapter.not_representable`
  beyond it). The value is the exact integer of the literal: the adapter
  MUST NOT parse it through binary64, so `9007199254740993` stays
  `9007199254740993`. `1e3`, `1E3` and `9007199254740993e0` are written with
  an exponent and are `adapter.type_mismatch`, whatever their value;
- `float64` accepts any JSON number and takes the binary64 value nearest to
  its decimal text, ties to even (IEEE 754 round to nearest); a text whose
  rounding gives an infinity, a magnitude of at least 2^1024 - 2^970, is
  `adapter.not_representable`. A number written as an integer converts from
  its integer value, so `-0` gives `+0.0` and `-0.0` gives `-0.0`;
- `utf8` accepts only a JSON string, unchanged;
- any other JSON type, an object or an array included, is
  `adapter.type_mismatch`. No value is coerced between types: the string
  `"1"` is not an `int64`, the number `1` is not a `utf8`.

The conversion loses, by declaration and only there: for `float64`, the
decimal text beyond the nearest binary64 (`0.1`, an integer beyond 2^53, more
than 17 significant digits, the lexical form of the number, the sign of an
integer `-0`); for every type, the difference between an absent member and
JSON `null`, which are both null. A consumer that needs any of them declares
the field `utf8` and converts it with a versioned kernel.

**RA-006** — With `undeclared_members: reject`, a top-level member of a
record that is not the first token of any declared pointer is a record error
(`adapter.undeclared_member`), checked after the declared fields. The
member's key is source data: an error or a diagnostic never reports it, not
even in part, and names the fixed identifier `@undeclared` in its place
(ERR-010). With `ignore` it is not converted: a declared loss, never reported
as a failure.

## 6. Record errors

**RA-007** — The first record error of a record, in the order of RA-005 and
RA-006, is its cause. With `on_record_error: fail`, the first record with a
cause fails the whole adaptation with category `data_mapping`, naming the
record index, the declared field name (or `@undeclared`) and the cause,
never the value (ERR-010); no table is produced. With `exclude`, the record
is left out and the table carries one `plenora-row-diagnostics-v1` document
with scope `read`, `index_basis: source_row_zero_based`,
`completeness: complete`, `observed_total` the number of excluded records,
`input_total` the number of records, `counts` by cause, `examples_limit`
128, `examples_truncated` true only beyond 128, and one example per excluded
record in record order: `source_index` the record index, `cause`, and
`column` the declared field name, omitted when the cause is
`adapter.undeclared_member`, whatever the name. With
`fail` the table carries no diagnostics.

**RA-008** — Every error of the adapter has `remote_effect: none` and
`retry.kind: never`: the adapter has no remote effect, and the same input
fails again. Its phase is `validate` for `invalid_configuration`,
`execution` and `schema`, and `read` for `data_mapping`.

**RA-009** — Next to the table the adapter reports the REST `status`, the
number of REST errors and the row diagnostics of RA-007, so that a caller
distinguishes a complete conversion from one with excluded records or from a
partial REST result.

## 7. Output

**RA-010** — The table carries `plenora.contract.version=1` and each field's
declared `plenora.field_id` (Arrow Interchange 1.0, ARROW-001, ARROW-003);
it has no geometry field. Its schema is the declaration's even when no
record remains.

## 8. Conformance vectors

The vectors in
[`vectors/rest-arrow-adapter-v1`](../../vectors/rest-arrow-adapter-v1/) give
a declaration, the members of a REST result the adapter reads and the whole
expected outcome: the Arrow schema with types, nullability and identities,
the rows, the row diagnostics (validated against
`row-diagnostics-v1.schema.json`), the REST status, or every axis of the
error. The validator converts every vector with
a reference adapter that implements sections 2 to 7, so a vector cannot state
an outcome the rules do not give.
