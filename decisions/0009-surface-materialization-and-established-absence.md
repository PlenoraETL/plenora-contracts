# 0009: The effect of a surface that materializes a result; an established absence of geometry

Status: accepted

Date: 2026-10-06

Two gaps IO-tools met while adopting the io-tools profile for `4.0.0`
(PR #6, HB3 and HB4). Neither can be closed inside a component.

## HB3: an operation whose output is a dataset could not be bound to a CLI

### Context

Surface Bindings 1.0 §1 requires a surface to preserve the catalog's side
effects. CLI 2.0 §4 reserves the machine stream for exactly one JSON document.
Together they leave no truthful declaration for `io.read`, whose catalog entry
has `side_effect: none` and an Arrow output: the CLI must put the bytes
somewhere, and writing a file is a local effect. IO-tools declares
`side_effect: local` for `io.read` in its capability document, against the
catalog, and records the difference as a deviation.

The first version of PR #6 stated that the binding "MUST declare the resulting
effect on its own surface", but Capability Discovery 2.0 has one `side_effect`
per operation and no member for a surface's effect: the rule had no machine
spelling.

### Decision

- The catalog and the capability `side_effect` describe the operation. A
  surface that cannot return a result in process writes it only to a
  destination the caller named as a declared input, and declares the effect it
  adds.
- The declaration is the shared capability attribute
  `plenora.surface_side_effects` (contract `plenora-surface-side-effects-v1`,
  SB-001): an object from the operation's surfaces to `local` or `remote`, each
  stricter than the operation's `side_effect`. A consumer calling through a
  surface reads the stricter of the two.
- Attribute keys beginning with `plenora.` are reserved for shared contracts
  (Capability Discovery 2.0 §7).
- The validator checks SB-001 on every capability example; a valid and an
  invalid example show the shape.

For IO-tools, `io.read` keeps `side_effect: none` and declares
`{"plenora.surface_side_effects": {"cli": "local"}}`, which closes its first
deviation.

### Compatibility

From the point of view of a conforming consumer (COMPATIBILITY.md):

- the attribute is optional; without it every surface has the operation's
  effect, as before, and a consumer that ignores it keeps reading
  `side_effect` as before;
- `attributes` was already an open object, and untyped attributes were opaque
  to consumers (CAP-013), so no consumer gave a `plenora.` key a meaning;
  reserving the prefix narrows only what a component may publish;
- no schema, catalog, binding or vector changes.

### Alternatives

- **A `side_effect` per surface in a capabilities v3 schema.** Exact, but a new
  capability document version for every component, for one operation of one
  component.
- **Declare `local` in the catalog.** It would describe the CLI, not the
  operation, and make the Rust and runtime surfaces, which return the dataset
  in process, look as if they wrote files.
- **Keep the deviation.** It records a difference the contract cannot express
  rather than a choice of the component.

## HB4: "scanned in full, no geometry" has no spelling, and needs a version

### Context

Arrow Vocabulary 1.0 §3 closes `plenora.geometry.types_declaration` on
`exact`, `mixed` and `unresolved`, and §4 requires `exact` to carry a non-empty
list. A source scanned entirely and carrying no geometry is therefore written
`unresolved`, indistinguishable from one whose types could not be determined.
The two carry different guarantees: a sink that accepts only a subset of the
canonical types can take the first and must refuse the second.

### Decision

The 1.0 vocabulary does not change. The obvious fix, an optional key such as
`plenora.geometry.types_scan`, was in the first version of PR #6 and was
withdrawn:

1. the vocabulary closes itself in its first sentence, so a consumer may
   validate that a geometry field carries these keys and no others; adding to
   a closed set is not adding an optional field to an open one;
2. `plenora.contract.version` already carries the fail-closed mechanism for
   introducing vocabulary, and leaving it at `1` would use none of it;
3. `arrow-metadata-vector-v1.schema.json` accepts any string-valued metadata
   key; that is a property of how the vectors are validated, not a statement
   about what a conforming consumer must accept, and reading compatibility off
   it would make every future key compatible by construction.

The shared distinction belongs to a successor vocabulary that raises
`plenora.contract.version`. Until then a component that needs it uses
`plenora.geometry.native.*`, which §5 reserves for that and ARROW-009 and
ARROW-010 govern, and a sink that restricts geometry types keeps refusing
sources whose types are undetermined, including those that are certainly
empty. The refusal is conservative and loses no data.

The other half of the IO-tools deviation, that the refusal cannot be
predicted from the `io.catalog` result, is a component-owned catalog field,
not a vocabulary change; it is handled by the IO-tools catalog contract, not
here.

## Change statement

- **Consumers affected:** consumers that select a surface by its effect, and
  IO-tools, which closes the `side_effect` deviation of `io.read`.
- **Before:** one `side_effect` per operation; a materializing surface had no
  truthful declaration.
- **After:** SB-001 and the reserved attribute prefix; Arrow Vocabulary 1.0
  unchanged, with the route to a successor recorded.
- **Compatible:** yes.
- **Schemas, examples and profiles:** two capability examples; no schema,
  catalog, binding, vector or profile changes.
- **Adoption impact:** IO-tools may declare the attribute after moving its pin
  and drop the deviation. A component that publishes a `plenora.`-prefixed
  attribute of its own renames it.
