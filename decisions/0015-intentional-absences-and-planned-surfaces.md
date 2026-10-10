# 0015: Intentional absences in the catalogs, and surfaces that are only planned

Status: accepted

Date: 2026-10-10

## Context

The interoperability analysis of 2026-10-10 compared the catalogs with the
released artifacts and found two kinds of gap.

**Absences without a stated reason.** The catalogs leave out, on purpose:

- the CLI and the runtime for `database.transaction.*`;
- the runtime for `database.execute`;
- the CLI and the Python SDK for `data.run` version 3;
- the runtime for `data.run` version 2.

Only the last has its reason in a profile. The contracts
`plenora-database-transaction-handle-v1` and
`plenora-database-savepoint-input-v1` declare `application/json`, but no
surface serializes them: Rust and Python pass handle objects (SURF-009). A
reader cannot tell a decision from an omission, and a later change could
"complete" the catalog by adding a surface whose hazard nobody recorded.

**Surfaces listed but not implemented.** `io-tools-v2.json` lists `runtime`
for all six operations, and no released IO-tools artifact implements it
(plenora-IO-tools PR #27 is open); `data-tools-v2.json` lists it for
`data.catalog`, `data.describe`, `data.validate` and `data.run` version 3,
and data-tools has no runtime binding. A consumer reading the catalog can
take them for available.

## What the specifications already allow

Asked whether to remove those surfaces or mark them "planned", the rules
answer:

- **Removal is forbidden.** COMPATIBILITY.md fixes every field of a published
  operation identity except the additions it lists, and surfaces may only
  grow; `repeated_identity_errors` and the immutability gate enforce it.
  Public Catalogs 1.0 section 5 item 4 adds that a catalog is not edited to
  match an incomplete implementation.
- **A "planned" marker has no place.** The catalog schema is closed
  (`additionalProperties: false`) and an operation's `attributes` are fixed
  once published; a marker would need `public-catalog-v2` and would describe
  an artifact in a document that describes a target, against Public Catalogs
  1.0 section 1 and the profile index ("do not report current
  implementation status").
- **The prescribed mechanism exists.** Section 1 of Public Catalogs 1.0 says
  the catalog does not claim that an artifact conforms; Capability Discovery
  2.0 (CAP-004, CAP-008) and SURF-016 make the capability document the only
  statement of what an artifact exposes; `runtime` is `conditional` in both
  catalogs, so an artifact without it is conforming and needs no deviation.

What was missing is a rule that says so to the consumer, and a guard that
keeps the intentional absences.

## Decision

Public Catalogs 1.0, section 5:

- **CAT-001** — catalog surfaces are the target, never availability; a
  consumer selects surfaces only from the artifact's capability document; a
  cataloged surface that document does not list is *planned* for that
  artifact.
- **CAT-002** — no surface is removed and no marker is added; an artifact
  omits a surface it does not implement, with a deviation only when the
  target applicability is `required`.
- **CAT-003** — a surface a profile declares intentionally absent is never
  added to that operation identity; a binding needs a new operation version
  whose contract removes the reason. The validator checks every catalog
  version against the absences and that each profile states the rule
  (`INTENTIONAL_ABSENCES`, `intentional_absence_errors`).

Profiles:

- database-tools: **DB-ABS-001** (transactions: no CLI, because a handle does
  not survive the process and CLI 2.0 is one invocation, one envelope; no
  runtime, because messages are independent and a transaction across them
  needs affinity, lease and orphan recovery that no contract defines),
  **DB-ABS-002** (`database.execute`: no runtime, because Runtime Binding 1.0
  does not promise at-most-once delivery and the operation accepts no
  idempotency key, so a redelivered request could execute an arbitrary
  statement twice), **DB-ABS-003** (handle and savepoint contracts are
  logical shapes, never serialized; `application/json` names a
  representation no surface has).
- data-tools version 2: **DT-ABS-001** (`data.run` version 3: no CLI or
  Python SDK, because it needs the application's artifact resolver and
  version 2 already serves the local case with the same semantics),
  **DT-ABS-002** (`data.run` version 2: no runtime, one payload per
  response), and the runtime entries of the other operations are planned
  until an artifact advertises them.
- The profile index defines `conditional` with CAT-001; the profiles of
  IO-tools (versions 1 and 2), database-tools and data-tools version 1 say
  `conditional` for the runtime instead of "required for every operation
  selected for orchestration", which the catalogs never said.

### Content types on the runtime (database-tools)

database-tools asked how the runtime carries the content types its catalog
declares, which Runtime Binding 1.0 cannot select:

- **`database.query`**: the catalog declares `application/json` and the Arrow
  stream for the result, and the closed input contract cannot ask for one.
  Two options: (a) JSON only on the runtime for version 1; (b) a selection
  member in a new input contract, which is a new operation version, not a
  minor change, because `plenora-database-query-input-v1` is closed.
  Decided (a), as **DB-RT-001**, with the condition that the JSON is the
  complete result and not a summary (RT-008, Arrow Interchange 1.0 section
  7); (b) is the route when a pipeline needs Arrow from the runtime, with an
  artifact sink rather than inline bytes, as `data.run` version 3.
- **`database.write`**: the envelope is `application/json` and the Arrow
  rows arrive by artifact reference; **DB-RT-002** states it, without
  changing the catalog, whose content types describe the operation.
- **`database.query` in the Python SDK**: no binding returns Arrow. The
  result may be the structured JSON form, but Python SDK 1.0 section 3
  says a tabular SDK SHOULD use PyArrow or Arrow IPC at the boundary, and
  without it `database.query` enters no Python pipeline. This is a gap to
  close, not an intentional absence: a PyArrow (or `__arrow_c_stream__`)
  result for `Session.select`.

### Open point: mutating runtime operations without an idempotency key

DB-ABS-002 belongs to a class. On the runtime, with `side_effect: remote` and
no idempotency key, the catalogs also bind `database.write` (append mode
repeated adds rows), `data.run` version 3 (an `overwrite: true` sink is
replaced again; `false` fails with `conflict`) and `storage.put`,
`storage.copy`, `storage.delete`. Those surfaces are published and cannot be
removed (CAT-002). The safe rule is one the transport keeps: a request for
such an operation is delivered at most once, and an unproven outcome is
reported `remote_effect: unknown` (ERR-004, ERR-014), never retried
automatically. Options: (a) state it in the runtime-tools profile; (b) a new
version of each operation with the idempotency-key control; (c) both, (a)
first. Recommended: (c). Not ratified here: it changes the runtime-tools
profile, a separate adopter.

## Change statement

- **Consumers affected:** every consumer that reads a catalog to choose a
  surface; maintainers of the catalogs.
- **Before:** catalog surfaces could be read as availability; four absences
  had no stated reason; the handle contracts declared a JSON form that no
  surface has.
- **After:** CAT-001 to CAT-003, DB-ABS-001 to DB-ABS-003, DB-RT-001,
  DB-RT-002, DT-ABS-001, DT-ABS-002 and the validator guard.
- **Compatible:** yes: no catalog, binding, schema or vector changes; the
  rules restate what Capability Discovery 2.0 already makes authoritative and
  forbid only additions that no published document contains.
- **Schemas, examples and profiles:** profiles of database-tools, data-tools
  (versions 1 and 2), IO-tools (versions 1 and 2) and the profile index.
- **Adoption impact:**
  - IO-tools: no change while its capability document omits `runtime`
    (it does: `capability.rs` lists Rust and CLI); PR #27 adds it when it
    lands.
  - data-tools: no change while its capability document lists only the
    surface that answers (`crates/plenora-cli/src/capacita.rs`), as it does;
    no deviation is needed, the surface is conditional.
  - database-tools: write the reasons of DB-ABS-001 and DB-ABS-002 in its
    documentation and keep the handles out of every serialized surface;
    return the complete query result as JSON on the runtime (DB-RT-001) or
    record a deviation while the runtime returns a summary; accept the
    Arrow of `database.write` on the runtime only by artifact reference
    (DB-RT-002); give `Session.select` an Arrow result.
