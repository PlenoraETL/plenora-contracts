# Plenora Row Diagnostics Contract 1.0

Status: normative

Contract identifier: `plenora-row-diagnostics-v1`

The machine shape is defined by the
[row diagnostics schema](../../schemas/row-diagnostics-v1.schema.json).

## 1. Purpose

Row diagnostics let a caller identify bounded examples and trustworthy counts
for row-scoped read or write failures. They expose what is known; they do not
turn an ambiguous remote outcome into a precise one.

## 2. Identity and indexing

**DIAG-001** — `contract` MUST be `plenora-row-diagnostics-v1`.

**DIAG-002** — `index_basis` MUST be `source_row_zero_based`.
`source_index` always refers to the original input row across batch
boundaries.

**DIAG-003** — A component MUST NOT publish a guessed source index. When row
attribution is unavailable, it reports a knowledge limit instead.

## 3. Scope and completeness

`scope` is `read` or `write`. `completeness` is:

- `complete`: all rows in the declared population were classified;
- `partial`: only a known portion was observed;
- `unknown`: the component cannot bound the unobserved portion safely.

**DIAG-004** — `knowledge_limits` MUST identify why completeness is not
`complete`. Values are stable machine codes, not prose.

**DIAG-005** — `observed_total` is the number of row failures actually
observed. `total` or `input_total` MUST be omitted when not known.

## 4. Causes and examples

`counts` maps stable cause codes to counts. Each example contains
`source_index`, `cause` and optional `column`, `key` and `write_state`.

**DIAG-006** — Cause codes MUST be namespaced, stable and usable without parsing
messages, for example `database.constraint_violation` or
`conversion.value_not_representable`.

**DIAG-007** — `examples_limit` bounds the number of published examples.
`examples_truncated` MUST be true when additional observed examples were
omitted.

## 5. Keys and sensitive data

A row key has a field name, a state and an optional scalar value. States are
`value`, `redacted` and `unavailable`.

**DIAG-008** — Row values MUST NOT be included except for an explicitly selected
diagnostic key whose publication policy permits it.

**DIAG-009** — A key in `redacted` or `unavailable` state MUST NOT contain a
value. Error messages and cause codes MUST NOT contain source-row payloads.

## 6. Write outcomes

Write diagnostics may classify rows as:

- `certainly_rejected`;
- `certainly_not_attempted`;
- `certainly_rolled_back`;
- `effect_unknown`.

**DIAG-010** — These states express evidence, not intent. A row MUST be marked
`certainly_rolled_back` only when rollback is confirmed.

**DIAG-011** — Unknown quantities use an explicit `{state: unknown}`
partition count. Zero MUST NOT be used to represent unknown.

**DIAG-012** — Diagnostic partitions MUST be consistent with the enclosing
error's `remote_effect`. Row detail cannot strengthen an ambiguous global
outcome without evidence.

## 7. Attachment

Row diagnostics MAY be attached to a typed public error or returned in an
operation-specific result that explicitly allows partial success.

**DIAG-013** — The attachment point MUST preserve the complete diagnostics
document. A CLI, SDK, Rust or runtime binding MUST NOT replace it with a
human-readable summary.

When the enclosing serialized error uses `error-v1.schema.json`, the complete
document is placed at `details.row_diagnostics`. Native typed surfaces MAY
offer a direct `row_diagnostics` accessor to the same document.

## 8. Implementation freedom

This contract does not prescribe how components find invalid rows, how many
passes they perform, how transactions are implemented or how diagnostics are
stored internally.
