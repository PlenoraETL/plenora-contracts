# 0021: The gate's messages carry no data

Status: accepted

Date: 2026-10-10

## Context

Independent readings found document content in the gate's messages: field
names of Arrow vectors, keys of runtime probe metadata, the numeric token of
a plan, a credential key, the expected and computed probe results, and the
messages of jsonschema, which quote the rejected instance. A vector is a
fixture, but the same validators are the reference for components whose
errors must never carry data (ERR-010); a validator that prints what it
reads teaches the opposite, and a log of the gate could expose a value.
Fixing the messages one by one did not close the class.

## Decision

- A message of the gate holds only fixed text and structural identifiers:
  rule identifiers, paths of repository files, positions, and names that a
  schema or a contract defines (an error axis, a reserved metadata key, a
  missing member that a schema requires). `tools/messages.py` builds the
  parts that name members (`structural`, `differing_members`, `position`).
- Schema errors report the failing keyword, its place in the schema and an
  anonymous place in the instance (indices, `*` for members), never the
  message of jsonschema.
- `tools/test_message_sentinels.py` replaces, one at a time, every string
  value, number and object key of every vector and example with a sentinel,
  runs the complete gate and fails when a sentinel appears in its output. A
  future message that prints document content fails it, whatever validator
  builds it.

## Change statement

- **Consumers affected:** maintainers of the gate.
- **Compatible:** yes; no contract document changes.
- **Adoption impact:** none.
