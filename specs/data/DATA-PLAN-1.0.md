# Plenora Data Plan Contract 1.0

Status: normative

Contract identifier: `plenora-data-plan-v1`

The machine shape is defined by
[`data-plan-v1.schema.json`](../../schemas/data-plan-v1.schema.json).

## 1. Applicability

This contract is the plan format accepted by `data.validate` version `2` and
`data.run` version `2` of the
[data-tools v2 catalog](../../catalogs/data-tools-v2.json). It replaces, for
those operation versions, the plan formats `4`, `5` and `6` governed by
[Plan Budget 1.0](PLAN-BUDGET-1.0.md), which keep governing `data.validate`
and `data.run` version `1` unchanged.

A plan is a closed JSON document: named Arrow tables in, a sequence of kernel
steps in single-assignment form, named Arrow tables out. The kernels and their
versions are those of
[`data-kernels-v2.json`](../../catalogs/data-kernels-v2.json).

## 2. Document

```json
{
  "version": 1,
  "inputs": ["orders", "customers"],
  "limits": {"max_governed_memory_bytes": 1073741824},
  "steps": [
    {"out": "valid", "op": "table.filter", "in": ["orders"],
     "config": {"column": "amount", "operator": ">", "value": 0}},
    {"out": "joined", "op": "table.join", "in": ["valid", "customers"],
     "config": {"left_keys": ["customer"], "right_keys": ["id"], "how": "inner"}}
  ],
  "outputs": ["joined"]
}
```

**DPLAN-001** — `version` is the integer `1`. A consumer MUST reject any other
value with category `invalid_plan`; it MUST NOT read a plan of a different
format as this one.

**DPLAN-002** — The document and the `limits` and step objects are closed:
unknown fields fail with `invalid_plan`. A key repeated at any depth,
`config` included, fails with `invalid_plan`; a consumer MUST NOT keep one of
the repeated values.

**DPLAN-003** — Every number is read at its exact written value. An integer
(no fraction, no exponent) is accepted from -2^63 to 2^64 - 1. Any other
number is read as the nearest IEEE 754 binary64 value and accepted only when
its exact decimal value equals that of the shortest decimal that reads back
as the same binary64: `0.1`, `1.5` and `1e3` are accepted,
`2.0000000000000000001` is not. A rejected number fails with `invalid_plan`;
a consumer MUST NOT round it.

## 3. Names and steps

**DPLAN-004** — `inputs` names the tables the caller provides (at least
one), `steps[].out` the table each step produces. Every name is defined once
across `inputs` and `steps[].out`. A plan without steps that names inputs as
outputs is valid: it returns them unchanged.

**DPLAN-005** — `steps[].in` lists, in the order the operation defines (left,
right), names defined by `inputs` or by an earlier step. `outputs` lists
defined names without repetition, in the order the result returns them.

**DPLAN-006** — `steps[].op` is the canonical identifier of a kernel in the
registry. An identifier outside the registry, legacy aliases included, and a
registered kernel that the answering artifact reports unavailable fail with
`unsupported`. A number of `in` names the kernel does not accept fails with
`invalid_plan`.

**DPLAN-007** — `steps[].config` is the kernel's configuration object; absent,
it is `{}`. Its fields are owned by the kernel descriptor that `data.catalog`
returns for the kernel's registry version.

**DPLAN-008** — `crs`, when present, is the plan CRS used by kernels that
produce geometries from non-geometric columns. It is resolved during
validation, fail-closed (`crs`), even when no step uses it.

## 4. Limits

**DPLAN-009** — `limits` replaces, one by one, the component defaults for the
keys it declares: `max_input_rows`, `max_output_rows`, `max_rows_per_edge`,
`max_governed_memory_bytes`, `max_string_bytes` and `max_regex_bytes`
(integers from 1 to 2^64 - 1) and `max_expansion_factor` (a number greater
than zero, under DPLAN-003). A value or combination the component cannot apply
fails with `invalid_plan`; the component publishes the defaults it applies.

**DPLAN-010** — `max_governed_memory_bytes` is the memory budget of the run.
Absent, the component applies its published default, which it MUST publish
(as in PLAN-013). The component checks each step against the budget before
running it, with a prediction it documents; a step that does not fit fails
with `resource_limit` before it runs, and a step that exceeds the budget while
running fails with `resource_limit` without returning outputs.

**DPLAN-011** — This format has no `max_domain_memory_bytes` and no isolated
execution profile. Plan Budget 1.0 rules PLAN-007 to PLAN-011 and PLAN-014 to
PLAN-016 do not apply to it.

## 5. Identity

**DPLAN-012** — This contract defines no plan hash and no canonical form. Two
plans are not asserted equal or different by any published identity; a
component MUST NOT present a value as the identity of a plan in this format.
Plan Budget 1.0 rules PLAN-017 to PLAN-021 do not apply.

**DPLAN-013** — No migration exists from plan formats `4`, `5` or `6` to this
format. A consumer of `data.validate` or `data.run` version `2` MUST reject a
document with `schema_version` instead of converting it.

## 6. Validation boundary

**DPLAN-014** — `data.validate` reads schemas, never rows, and rejects
before any execution: DPLAN-001 to DPLAN-009; the arity and configuration of
every step against its kernel descriptor; the output schema of every step,
derived from its input schemas; and the declared limits that schemas alone
can violate, such as a column count. `data.run` performs the same checks
first. Failures that depend on row values (row counts, data errors, memory
use) may occur only during `data.run`.

## 7. Machine-readable shape

[`data-plan-v1.schema.json`](../../schemas/data-plan-v1.schema.json) captures
the closed shape of section 2 and the types of section 4. It cannot express:

- **DPLAN-002** for repeated keys, which a JSON parser already merges;
- **DPLAN-003**, which concerns the written number before parsing (the
  validator checks it on the raw text of the examples);
- **DPLAN-004** and **DPLAN-005**, which relate names across the document;
- **DPLAN-006** and **DPLAN-007**, which depend on the registry and on the
  kernel descriptor.

`tools/validate_specs.py` checks DPLAN-003, DPLAN-004, DPLAN-005 and the
registry part of DPLAN-006 on the examples; components enforce all of them.
