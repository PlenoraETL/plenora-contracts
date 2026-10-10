# 0017: A minimal contract for the REST-to-Arrow adapter

Status: accepted

Date: 2026-10-10

## Context

The edges from `rest.enrich` to `data.run` are `adapter_required`
(Composition 1.0 section 4): the adapter "must explicitly own field type
inference or declaration, nullability, ordering and per-record error
policy". No component implements it, and none says how. The interoperability
suite wrote its own to run the chain and marks the cell as a known gap,
because an adapter written by each application is a conversion nobody can
check: two applications can turn the same REST result into different tables
without either being wrong by any rule.

Two answers were possible: declare the adapter the application's business
and stop there, or fix a contract that an adapter can claim.

## Decision

Both, in one document: the adapter belongs to the application (RA-001), and
REST-to-Arrow Adapter 1.0 (`plenora-rest-arrow-adapter-v1`) fixes the minimum
an adapter declares and the conversion it performs, so that one claiming the
contract is verifiable.

- **Input** (RA-002): one complete `plenora-rest-execution-result-v1`, of
  output type `records` (`schema` otherwise); a status outside
  `accept_status` fails with `execution`; `failed` is never accepted.
- **Declaration** (RA-003): fields with name, `plenora.field_id`, RFC 6901
  pointer, Arrow type (`bool`, `int64`, `float64`, `utf8`) and nullability;
  `accept_status`, `on_record_error`, `undeclared_members`. A malformed
  declaration fails with `invalid_configuration` before any record.
- **Order** (RA-004): row *i* is the *i*-th record kept; no sorting.
- **Conversion** (RA-005, RA-006): no inference and no coercion; integers
  only from integer literals within int64; `float64` the nearest binary64 to
  the decimal text; missing and `null` are null only for a nullable field;
  undeclared members ignored or rejected as declared.
- **Record errors** (RA-007): five closed causes; `fail` stops with
  `data_mapping` naming record, field and cause, never the value; `exclude`
  leaves the record out and reports it in `plenora-row-diagnostics-v1`.
- **Report and output** (RA-008, RA-009): REST status and error count next to
  the table, so a partial result is never read as complete; the declared
  schema, with `plenora.contract.version=1` and the declared identities.

Two schemas (`rest-arrow-adapter-v1` for the declaration,
`rest-arrow-adapter-vector-v1` for the vectors), 22 vectors in
`vectors/rest-arrow-adapter-v1`, a reference adapter in the validator
(`tools/rest_adapter.py`) that derives every outcome. Composition 1.0
section 4 points to the contract; the edges stay `adapter_required`.

### Second reading

An independent reading found, and this decision corrects: a failed result
without records gave `schema`, because the output was checked before the
status (RA-002 now fixes the order); the overflow sentence contradicted
rounding to nearest at the boundary (RA-005 now states the IEEE threshold,
with a vector on each side); an integer literal `-0` and the sign of zero
were unstated (RA-005 states them, and the comparison of vectors tells
`0.0` from `-0.0`); an array index followed by a line feed was read as an
index; RA-006 did not say which undeclared member to name; a declaration
listing `failed` was accepted by the reference adapter.

### Scope left out of version 1

- Types beyond the four JSON scalars (decimals, dates, timestamps,
  geometry): an application converts them from `utf8` with a data kernel,
  whose semantics are already versioned.
- A link between a REST error and the record it concerns: the REST result
  reports `input_index` on errors, not on records.

## Alternatives

- **Application-owned only, without a contract.** Leaves the conversion
  uncheckable, which is the gap the suite found.
- **An operation of data-tools or rest-tools.** Moves application policy
  (which members, which types, which failures to drop) into a component, and
  creates an implementation to maintain for a conversion that differs per
  REST API.
- **Type inference from the records.** The same REST API would yield
  different schemas on different days; Composition 1.0 already forbids it.

## Change statement

- **Consumers affected:** applications composing `rest.enrich` with
  `data.run`; the interoperability suite.
- **Before:** an adapter with no stated behavior.
- **After:** REST-to-Arrow Adapter 1.0, optional to claim.
- **Compatible:** yes; nothing existing changes meaning.
- **Schemas, examples and profiles:** two schemas, two invalid examples, 22
  vectors, a new normative specification listed in the README; Composition
  1.0 section 4 gains a paragraph. No catalog, binding or profile changes.
- **Adoption impact:** none for the five libraries. The suite replaces its
  adapter with one that claims the contract and runs these vectors; the
  rest→data cell can then leave the known-gap list.
