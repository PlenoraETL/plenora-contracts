# Full interoperability matrix

Status: proposal, revision 2; a qualification roadmap for ratification, not an
adopted contract. Nothing in this document changes a published schema, catalog
or pin. Revision 2 incorporates the second reader's findings: corrected edge
counts, candidate edges that revision 1 wrongly declared non-edges, the
per-operation qualification, and the runtime prerequisite for the end-to-end
phase.

Every library must talk to every other library it can meaningfully exchange
data with, and the exchange must be proven, not assumed. This proposal lays
out the matrix of component pairs, states what is already declared and tested,
names the gaps, and proposes the order in which the gaps close.

## Where interop stands today

- `composition/pipelines-v1.json` declares **18 versioned edges: 16 Arrow
  edges (six directional pairs among io/data/database across operation
  versions) and 2 `rest.enrich -> data.run` edges** with
  `mode: adapter_required` over `plenora-rest-execution-result-v1`.
- `vectors/interop-v1` (40 vectors) exercises Arrow handoffs and rejections
  across io/data/database chains, including `io -> database -> io`
  (`handoff-io-database-io.json` and relatives).
- The `rest-arrow-adapter-v1` contract and vectors prove the REST -> data
  junction at the vector level; no end-to-end execution proves it through
  the runtime.
- `bindings/runtime-v1.json` binds all five components (36 operations).
  Note: not every cataloged operation version has a runtime binding —
  `data.run@2` has none, and `data.run@3` is intentionally a runtime-only
  representation absent from the CLI surface.
- `plenora-storage-tools` appears in **no** composition edge.
- No suite executes a declared edge end to end through the runtime control
  plane. Each library proves its own surface; the seams are proven only at
  the vector level, and only for the chains above.

## The matrix

Producer rows, consumer columns. Cell states: **declared+vectors**,
**declared** (edge in the composition document, no dedicated vectors),
**candidate** (meaningful exchange the contracts do not declare yet — to
ratify in phase 1), **adapter** (needs an explicit adapter contract),
**non-edge** (reasoned exclusion). A pair that moves tables uses Arrow
interchange; a pair that moves files uses the file interchange proposed
below. Arrow IPC is **also a file format**: `data.run@2` reads and writes
Arrow IPC files, `data.run@3` consumes runtime artifacts, and
`database.read`/`database.write` declare Arrow IPC file transport — so
storage is not "bytes versus Arrow": it can carry exactly the files those
operations consume and produce.

| from \ to | io | data | database | storage | rest |
| --- | --- | --- | --- | --- | --- |
| **io** | — | declared+vectors | declared+vectors | **candidate** (`io.write -> storage.put`, file) | **candidate** (`io.write -> rest.upload`, file); `io.read -> rest.enrich` is **adapter** (enrich takes JSON, not Arrow) |
| **data** | declared+vectors | — | declared+vectors | **candidate** (`data.run@2 -> storage.put`, Arrow IPC file) | **adapter** (`data.run -> rest.enrich` input leg: enrich accepts JSON; the published adapter covers the opposite direction only) |
| **database** | declared+vectors | declared+vectors | — | **candidate** (`database.read -> storage.put` via Arrow IPC file) | **adapter** (same JSON-input constraint as data -> rest) |
| **storage** | **candidate** (`storage.get -> io.read`, file) | **candidate** (`storage.get -> data.run@2`, Arrow IPC file) | **candidate** (`storage.get -> database.write` via Arrow IPC file) | — | **candidate** (`storage.get -> rest.upload`, file passthrough) |
| **rest** | **candidate** (`rest.download -> io.read`, file) | declared (adapter, `rest.enrich -> data.run`, vectors in `rest-arrow-adapter-v1`); `rest.download -> data.run@2` is **candidate** (Arrow IPC file) | **candidate** (`rest.download -> database.write` via Arrow IPC file) | **candidate** (`rest.download -> storage.put`, file passthrough) | — |

Each **candidate** cell is ratified or rejected explicitly in phase 1: a
candidate that is rejected becomes a documented non-edge with its reason.

**Per-operation completeness.** The matrix is qualified per operation and
version, not per component. Phase 1 must include or exclude, with a reason,
at least: `database.query` as an Arrow producer, `data.describe` as a
consumer, `io.convert` in the file passages, `rest.generate` as a producer
of structured results, and the version split of `data.run` (@1/@2 CLI, @3
runtime-only). An operation left out of the matrix is left out in writing.

The **runtime** is not a row: it is the control plane that must execute the
declared edges through `bindings/runtime-v1.json` — discovery, negotiation,
execution, error propagation. Where an edge names an operation version with
no runtime binding (today `data.run@2`) or a runtime-only version
(`data.run@3`), phase 1 defines the per-surface mapping before phase 3 can
promise anything about it.

## The missing interchange: files

`plenora-arrow-interchange-v1` covers tables in flight. The candidate edges
above move **files**: storage fetches and publishes them, rest downloads and
uploads them, io reads and writes them, and data/database consume and
produce Arrow IPC files. Closing the matrix needs one new contract:

- `plenora-file-interchange-v1`: content type, size, SHA-256 digest,
  producing operation and declared format family; hand-off is by reference,
  never by re-encoding. The reference form distinguishes the two surfaces:
  a **local path** on the CLI surface, an **opaque authorized reference**
  on the runtime surface, which forbids private local paths. The published
  catalogs distinguish JSON envelopes from artifacts, so adding content
  types alone does not satisfy the direct-edge validator: the edge
  declaration itself must say which artifact form each side exchanges.
- Vectors: the published `interop-vector-v1` schema assumes Arrow inputs and
  tabular results, and schema immutability forbids widening it. File-edge
  vectors get **their own schema and contract identifier**
  (`file-interop-vector-v1` or a versioned successor), with positive
  hand-offs per edge and rejections — digest mismatch, content-type
  mismatch, truncated payload, format family the consumer does not
  advertise. Rejection vectors carry no payload data in the expected error,
  and the validator's own messages stay free of document data, per
  decision 0021.

## Phases

0. **Ratify this matrix** — every cell either an edge, a candidate with its
   decision pending in phase 1, or a reasoned non-edge. This PR.
1. **Contracts**: decide every candidate cell; add the file-interchange
   schema and the file-interop vector schema (new identifiers, no mutation
   of published shapes); extend the composition document with the ratified
   edges, each declaring its artifact form per side; record the
   per-operation inclusions and exclusions; define the per-surface mapping
   for operation versions without a runtime binding.
2. **Per-library conformance**: each library proves its side of each of its
   edges against the new vectors, behind its existing contract gates. Same
   bar as everything else: exact-by-construction, explicit refusals, no
   silent fallback.
3. **Runtime end to end**: `plenora-runtime-tools` executes the ratified
   edges that have a runtime binding — discovery, negotiation, probes,
   execution, error propagation — as one suite. Linux and Windows for the
   file edges; the dedicated VM for live legs (database containers, storage
   backends, a fixture REST server). Full chains after single edges:
   `storage -> io -> data -> database` and `rest -> data -> io -> storage`.
4. **Qualification**: the end-to-end suite becomes a release gate for
   runtime-tools and a scheduled compatibility run across the released
   versions of all six components; adoption manifests pin what was proven.

## Non-goals

- No new operations in any library: the matrix is proven over operations the
  public catalogs already declare.
- No orchestration changes in the runtime: execution stays sequential; this
  proposal adds proof, not scheduling.
- No re-encoding adapters for the FILE edges: a file hand-off that would
  require transcoding is a non-edge until a contract says otherwise. The
  JSON-input adapters for `rest.enrich` are a declared exception, with their
  own contract and vectors, like the published `rest-arrow-adapter-v1`.
