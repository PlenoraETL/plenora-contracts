# Full interoperability matrix

Status: proposal; a qualification roadmap for ratification, not an adopted
contract. Nothing in this document changes a published schema, catalog or pin.

Every library must talk to every other library it can meaningfully exchange
data with, and the exchange must be proven, not assumed. This proposal lays
out the complete matrix of component pairs, states what is already declared
and tested, names the gaps, and proposes the order in which the gaps close.

## Where interop stands today

- `composition/pipelines-v1.json` declares seven edges, all between
  `plenora-io-tools`, `plenora-data-tools` and `plenora-database-tools`
  over `plenora-arrow-interchange-v1`, plus `rest.enrich -> data.run`
  with `mode: adapter_required` over `plenora-rest-execution-result-v1`.
- `vectors/interop-v1` (40 vectors) exercises Arrow handoffs and their
  rejection cases across io/data/database chains only.
- `bindings/runtime-v1.json` binds all five components (36 operations) to
  the runtime surface; negotiation and probe vectors exist
  (`vectors/runtime-negotiation-v1`, `vectors/runtime-probes-v1`).
- `plenora-storage-tools` appears in **no** composition edge.
  `plenora-rest-tools` appears in exactly one.
- No suite executes a declared edge end to end through the runtime control
  plane with the released CLIs. Each library proves its own surface; the
  seam between two libraries is proven only for io/data/database, and only
  at the vector level.

## The matrix

Producer rows, consumer columns. Each meaningful pair is an **edge** with an
interchange contract; a pair that exchanges nothing directly is a declared
**non-edge** with its reason, so the absence is a decision rather than an
oversight.

| from \ to | io | data | database | storage | rest |
| --- | --- | --- | --- | --- | --- |
| **io** | — | declared+vectors | declared | **missing** (`io.write -> storage.put`, file) | **missing** (`io.write -> rest.upload`, file) |
| **data** | declared+vectors | — | declared+vectors | non-edge: data emits Arrow, storage moves bytes; mediated by `io.write` | **missing** (`data.run -> rest.enrich` input leg, Arrow) |
| **database** | declared | declared+vectors | — | non-edge: mediated by `io.write` | non-edge: mediated by `data.run` |
| **storage** | **missing** (`storage.get -> io.read`, file) | non-edge: bytes, not Arrow | non-edge: bytes, not Arrow | — | non-edge: no direct byte hand-off defined; revisit if a case appears |
| **rest** | **missing** (`rest.download -> io.read`, file) | declared, adapter (`rest.enrich -> data.run`) | non-edge: mediated by `data.run` | **missing** (`rest.download -> storage.put`, file passthrough) — ratify or reject explicitly | — |

The **runtime** is not a row: it is the control plane that must execute
*every* declared edge above through `bindings/runtime-v1.json` — discovery,
negotiation, execution, error propagation — with the real CLIs.

## The missing interchange: files

`plenora-arrow-interchange-v1` covers tables. Every missing edge above moves
a **file** (bytes with a format): storage fetches and publishes them, rest
downloads and uploads them, io reads and writes them. Closing the matrix
needs one new contract:

- `plenora-file-interchange-v1`: content type, size, SHA-256 digest,
  producing operation and declared format family; hand-off is by reference
  (path or stream), never by re-encoding.
- Vectors: positive hand-offs per edge, plus rejections — digest mismatch,
  content-type mismatch, truncated payload, format family the consumer does
  not advertise. Rejection vectors carry no payload data in the expected
  error, per the family error rule.

## Phases

0. **Ratify this matrix** — every cell either an edge or a reasoned
   non-edge. This PR.
1. **Contracts**: add the file-interchange schema, extend the composition
   document with the new edges (additive; new identifiers, no mutation of
   published shapes), add `vectors/interop-v1` cases per new edge, update
   catalogs only where an operation must advertise accepted/produced
   content types.
2. **Per-library conformance**: each library proves its side of each of its
   edges against the new vectors, behind its existing contract gates. Same
   bar as everything else: exact-by-construction, explicit refusals, no
   silent fallback.
3. **Runtime end to end**: `plenora-runtime-tools` executes every declared
   edge with the released CLIs — negotiation, probes, execution, error
   propagation — as one suite. Linux and Windows for the file edges; the
   dedicated VM for live legs (database containers, storage backends, a
   fixture REST server). Full chains after single edges:
   `storage -> io -> data -> database` and `rest -> data -> io -> storage`.
4. **Qualification**: the end-to-end suite becomes a release gate for
   runtime-tools and a scheduled compatibility run across the released
   versions of all six components; adoption manifests pin what was proven.

## Non-goals

- No new operations in any library: the matrix is proven over operations the
  public catalogs already declare.
- No orchestration changes in the runtime: execution stays sequential; this
  proposal adds proof, not scheduling.
- No re-encoding adapters for the file edges: a file hand-off that would
  require transcoding is a non-edge until a contract says otherwise.
