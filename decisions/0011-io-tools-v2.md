# 0011: IO-tools profile version 2: delivered serialization and sinks that require declared types

Status: accepted

Date: 2026-10-06

## Context

Two IO-tools deviations recorded against profile version 1 cannot be closed
inside the component:

1. `plenora-io-read-result-v1` fixes the delivered content type to the Arrow
   IPC file container, and `plenora-io-write-result-v1` admits only that
   container as received input. Since `4.0.0` IO-tools delivers and accepts
   the IPC stream too, as the catalog declares for both operations, so the
   results it emits for a stream do not validate against their own schema.
   The schemas were published with `4.0.0` and `4.1.0`; COMPATIBILITY.md
   forbids changing them in place, and the erratum exception applies only
   before adoption.
2. Every IO sink refuses a dataset whose geometry field carries
   `plenora.geometry.types_declaration: unresolved`, because each one accepts
   only a subset of the canonical geometry types. The refusal is typed but not
   predictable: `plenora-io-catalog-v1`, which the profile makes the sole
   normative source of publish guarantees, has no member for it.

Both need a new output contract, and an output contract is part of an
operation's identity in the catalog, so both need a new operation version.

## Decision

Publish IO-tools profile version 2, catalog `io-tools-v2.json`, next to
version 1:

- `io.read` version 2 with `plenora-io-read-result-v2` and `io.write` version 2
  with `plenora-io-write-result-v2`: the result names the serialization
  actually delivered or received, stream or file (IO-SER-001);
- `io.catalog` version 2 with `plenora-io-catalog-v2`: every writable format
  carries `requires_declared_geometry_types` (IO-CAT-001);
- `io.inspect`, `io.layers` and `io.convert` stay at version 1; the input
  contracts of the three new versions are those of version 1;
- null in IO success results means "not applicable" (IO-NULL-001), the same
  clarification made for profile version 1;
- the CLI binding map gives the three new versions the spellings of version 1,
  as Surface Bindings 1.0 §1 allows for versions no single catalog selects
  together; the runtime binding map adds `@2` selectors; the composition
  matrix repeats for version 2 the six edges of `io.read` and `io.write`.

The schemas stay owned by IO-tools; this repository fixes the identifiers and
the cross-component meaning of the two members.

## Alternatives

- **Add the three versions to `io-tools-v1.json`.** An artifact could then
  expose versions 1 and 2 together, but on the CLI it would need a second
  spelling for each (Surface Bindings 1.0 §1), and CLI 2.0 has no operation
  version selector: IO-tools would have to invent three command spellings to
  keep both. Rejected in favor of one catalog per artifact, as for
  data-tools.
- **Correct the emitter so that it produces valid version 1 results.** It
  withdraws a capability shipped in `4.0.0`, reopens the deviations it
  closed, and breaks the `direct` composition edges, which name the stream.
- **Keep the deviations.** They record a difference the contract cannot
  express, and the sink refusal stays unpredictable from the catalog.

## Change statement

- **Consumers affected:** consumers of `io.read` and `io.write` results, which
  learn the serialization from the result; orchestrators that choose a sink,
  which can predict the refusal of undeclared geometry types.
- **Before:** results that name only the file container; refusal visible only
  by invoking `io.write`.
- **After:** profile version 2 as the current target; version 1 unchanged and
  still available.
- **Compatible:** yes. New catalog, profile and operation versions next to the
  existing ones; no published document changes.
- **Schemas, examples and profiles:** new catalog and profile; CLI and runtime
  binding maps and the composition matrix add version 2 entries. The IO-owned
  schemas `plenora-io-read-result-v2`, `plenora-io-write-result-v2` and
  `plenora-io-catalog-v2` are published by IO-tools.
- **Adoption impact:** an artifact moves to version 2 by implementing the new
  catalog. For its consumers that is a breaking change of three operations,
  hence a major IO-tools release; an IO-tools release on profile version 1
  keeps the two deviations. The runtime transport learns the `@2` selectors.
