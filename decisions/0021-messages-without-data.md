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
  rule identifiers, paths of repository files, positions, names the
  validator's code defines (an error axis, a reserved metadata key, a
  component), and names of a contract document (a schema, a catalog, a
  binding, a Markdown text), which it quotes only through
  `messages.contract_name`, between « and ». A value of a vector or an
  example never appears, not even quoted: members are named by position.
  `tools/messages.py` builds every such part.
- Schema errors report the failing keyword, its place in the schema (a
  contract name) and an anonymous place in the instance (indices, `*` for
  members), never the message of jsonschema; an invalid schema is reported
  by keyword and place, never by its text, and an unusable one (a reference
  that does not resolve, an unknown dialect) is an explicit failure. An
  exception that escapes is reported by its type only.
- `tools/test_message_sentinels.py` covers every input by construction. It
  intercepts every read of the unmutated gate (`open`, `Path.open`,
  `Path.read_text`, `Path.read_bytes`) to list the inputs: vectors,
  examples, schemas, catalogs, bindings, composition and every Markdown
  text. It then mutates one place at a time: every string value, object key,
  number and array element at any depth, with three string sentinels (upper
  case, lower case, and the original value with its last alphanumeric run
  replaced, so that one passes the pattern of its place and reaches the
  checks after the schema) and numbers that are an integer, a float and
  values beyond the 64-bit ranges; in Markdown every line and every link
  target. It runs the complete gate for each (schema checks and links
  included) and fails when a sentinel appears in the output, outside a
  contract name for a contract document, and anywhere for a vector or an
  example.
- `tools/gate_fuzz.py` makes the 34,000 runs affordable: a validator that
  `run_gate` calls is re-executed only when it read the mutated file or its
  arguments changed; listings and file existence are read once. An oracle
  re-runs every 97th mutation with every validator executed and requires the
  same output, and every input re-serialized unchanged must give the
  unmutated output. The null fuzz uses the same harness on every JSON input
  and every array element.

## Change statement

- **Consumers affected:** maintainers of the gate.
- **Compatible:** yes; no contract document changes.
- **Adoption impact:** none.
