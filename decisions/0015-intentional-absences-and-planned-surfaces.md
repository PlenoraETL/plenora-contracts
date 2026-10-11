# 0015: Intentional absences in the catalogs, and surfaces that are only planned

Status: accepted

Date: 2026-10-10; revised 2026-10-11 (versions 2.0 of the contracts)

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

- **Removal is forbidden.** COMPATIBILITY.md fixes every field of a published
  operation identity except the additions it lists, and surfaces may only
  grow; `repeated_identity_errors` and the immutability gate enforce it.
- **A "planned" marker has no place.** The catalog schema is closed and a
  marker would describe an artifact in a document that describes a target.
- **Capability discovery is authoritative.** Capability Discovery 2.0
  (CAP-004, CAP-008) and SURF-016 make the capability document the only
  statement of what an artifact exposes.

What was missing is a rule that says so to the consumer, a guard that keeps
the intentional absences, and the outcome of a result beyond a bound.

## Why versions 2.0, not an edit of 1.0

The first form of this decision wrote CAT-001 to CAT-003 into Public
Catalogs 1.0, RT-024 into Runtime Binding 1.0, the absences and the runtime
content types into the published profiles, and restricted
`database.query` version 1 to JSON on the runtime (DB-RT-001). Each changes
the obligations of a published text: a component pinned to 1.0 that
re-pinned a later revision would have found new rules under the same
identifier. COMPATIBILITY.md defines no minor version of a contract: an
identifier carries only its major version, is immutable and is never
reused with another meaning, and a change of observable meaning needs a new
contract version. The repository owner chose that route (2026-10-11):

- **Public Catalogs 2.0** (`plenora-public-catalog-v2`, schema
  `public-catalog-v2`, the same shape as version 1 but the `contract`
  value) carries CAT-001 to CAT-003 and the grammar of a stated reason;
- **Runtime Binding 2.0** (`plenora-runtime-binding-v2`) carries RT-024,
  with its illustrative vectors in `vectors/runtime-v2`, and RT-025, which
  replaces RT-002 so that a request of 2.0 is byte for byte one of 1.0;
- the 1.0 texts are unchanged except an informative pointer;
- COMPATIBILITY.md states the transition: what changes, who adopts, how the
  versions coexist and when 1.0 stops being a target;
- the published domain profiles are unchanged; the absences and the
  runtime rules belong to new catalog and profile versions of the
  components whose runtime the profiles stated as required, bound to the
  contracts 2.0 (stacked change: data-tools version 3, IO-tools version 3,
  database-tools version 2);
- two published profile documents do change, each by additions that apply
  only to the 2.0 contracts. The runtime-tools profile gains a section
  "Runtime Binding 2.0" with obligations that bind runtime-tools only when
  it claims that version (wire version, RT-026 on the destinations it
  selects, its transport bound in the manifest, the vectors of
  `vectors/runtime-v2` and `vectors/runtime-negotiation-v1`); a claim of 1.0
  keeps exactly the obligations it had. The profile index adds, for a
  catalog of Public Catalogs 2.0 only, that an omitted `conditional` surface
  needs no deviation (CAT-002), and that a profile may name Runtime Binding
  2.0;
- DB-RT-001 is withdrawn: `database.query` version 1 keeps on the runtime
  the content types its catalog declares, as Runtime Binding selects them.

## Decision

Public Catalogs 2.0, section 5:

- **CAT-001** — catalog surfaces are the target, never availability; a
  consumer selects surfaces only from the artifact's capability document; a
  cataloged surface that document does not list is *planned* for that
  artifact.
- **CAT-002** — no surface is removed and no marker is added; an artifact
  omits a surface it does not implement, with a deviation only when the
  target applicability is `required`.
- **CAT-003** — a surface the profile of a catalog of version 2 declares
  intentionally absent is never added to that operation identity; a binding
  needs a new operation version whose contract removes the reason. The
  validator checks every catalog of version 2 against the absences its
  profile declares, and that the profile states each rule with a reason of
  the exact grammar (`INTENTIONAL_ABSENCES`, `intentional_absence_errors`).
  Catalogs of version 1 are outside it.

Runtime Binding 2.0:

- **RT-024** — a result beyond a bound of the transport or of the component
  fails with `resource_limit`, never with a truncated success (SURF-014);
  the phase follows ERR-003 and the remote effect ERR-004. The component
  declares its limits where its profile says; the transport in its adoption
  manifest.
- **RT-025** — capability version `1` names the wire format, which 2.0 keeps;
  the contract version is the `runtime` interface of the capability
  document (CAP-003). RT-018 compares the wire version with the wire
  version, never the contract version. Introducing a capability version `2`
  for an unchanged
  wire would have made every request of 2.0 unsupported by every 1.0
  artifact and duplicated every runtime vector, for no change of bytes.

- **RT-026** — the contract that governs an exchange is negotiated where
  the sender, or the transport that routes for it, selects the destination:
  a sender of 1.0 may use a destination of 2.0; a sender of 2.0 uses one of
  1.0 only after declaring that it accepts the downgrade, and otherwise
  refuses before sending; a request meant for 2.0 that reaches a destination
  of 1.0 is detectable only there, because the request is the same bytes.
  `vectors/runtime-negotiation-v1` states each case and the validator
  derives the decision.

The absences the profiles of version 2 declare: **DB-ABS-001**
(transactions: no CLI, because a handle does not survive the process and
CLI 2.0 is one invocation, one envelope; no runtime, because messages are
independent and a transaction across them needs affinity, lease and orphan
recovery that no contract defines), **DB-ABS-002** (`database.execute`: no
runtime, because Runtime Binding does not promise at-most-once delivery and
the operation accepts no idempotency key), **DB-ABS-003** (handle and
savepoint contracts are logical shapes, never serialized), **DT-ABS-001**
(`data.run` version 3: no CLI or Python SDK, because it needs the
application's artifact resolver and version 2 serves the local case),
**DT-ABS-002** (`data.run` version 2: no runtime, one payload per response).

### Catalogs and profiles of version 2 (stacked change)

database-tools, data-tools and IO-tools publish one new catalog version
each, bound to Public Catalogs 2.0: `database-tools-v2.json`,
`data-tools-v3.json` and `io-tools-v3.json`. Each lists the operation
identities of the previous current version unchanged; only `contract`,
`profile` and `$schema` differ. Their profiles (`database-tools-v2.md`,
`data-tools-v3.md`, `io-tools-v3.md`) are the previous ones with: Public
Catalogs 2.0 and Runtime Binding 2.0 among the applicable contracts; the
runtime `conditional` under CAT-001 and CAT-002 instead of "required for
every operation selected for orchestration"; DB-ABS-001 to DB-ABS-003,
DB-RT-002 and DB-RT-003 for database-tools; DT-ABS-001 and DT-ABS-002 for
data-tools. Only the latest version of each component gets a successor:
data-tools profile version 1 and IO-tools profile version 1 also stated the
runtime as required, and stay unchanged as available identities. The
previous catalogs and profiles are unchanged. The validator checks a
data-tools catalog against the operation versions it carries
(`DATA_CATALOG_GENERATION`: version 3 carries those of version 2), not
against its file version.

### Readings of the first form

Further readings of the first form fixed the axes of RT-024 (category,
remote effect and the ban on a truncated success; the phase left to
ERR-003) and the exact syntax of a reason: the profile is read as written,
LF and CR LF are the only terminators, and a lone CR, a byte order mark,
other line breaks and a line made only of non-ASCII white space are
explicit errors, each with its test. The fifth reading (Codex) found that
the first form changed published obligations in place, which this revision
corrects.

A sixth reading (Codex) of the versions 2.0 found that RT-025 was not
carried through: the metadata table still called the capability version the
"runtime binding version", RT-018 compared it with the advertised binding
version and called `"2"` unsupported, and COMPATIBILITY.md said that an
artifact of 2.0 satisfies every rule of 1.0, while 2.0 excludes RT-002. A
server advertising `plenora-runtime-binding-v2` and a request with `"1"`
were refused under the table and RT-018 and accepted under RT-025. The
table and RT-018 of 2.0 now compare the wire version with the wire version,
the contract is compared only with the capability document's interface
(RT-026), COMPATIBILITY.md states the exception of RT-002 and conditions
instead of an unconditional compatibility, and the negotiation cases have
vectors.

### Content types on the runtime (database-tools)

- **`database.query`**: the catalog declares `application/json` and the Arrow
  stream for the result, and the closed input contract cannot ask for one.
  The first form restricted version 1 to JSON on the runtime (DB-RT-001), a
  restriction added afterwards to a published operation: withdrawn. When a
  pipeline needs a chosen representation on the runtime, the route is a new
  operation version whose input names it, with an artifact sink rather than
  inline bytes, as `data.run` version 3.
- **`database.write`**: on the runtime the envelope is `application/json`
  and the Arrow rows arrive by artifact reference; the database-tools
  profile of version 2 states it (DB-RT-002) without changing the catalog,
  whose content types describe the operation.
- **A result beyond a bound**: the database-tools profile of version 2
  applies RT-024 to `database.query` and says where the bound is declared
  (DB-RT-003).
- **`database.query` in the Python SDK**: a gap to close, not an absence: a
  PyArrow (or `__arrow_c_stream__`) result for `Session.select`.

### Open point: mutating runtime operations without an idempotency key

DB-ABS-002 belongs to a class. On the runtime, with `side_effect: remote` and
no idempotency key, the catalogs also bind `database.write`, `data.run`
version 3 and `storage.put`, `storage.copy`, `storage.delete`. Those surfaces
are published and cannot be removed (CAT-002). The safe rule is one the
transport keeps, recorded as a requirement for the runtime-tools profile, to
be ratified there (issue
[plenora-contracts#35](https://github.com/PlenoraETL/plenora-contracts/issues/35)):

1. at most one start of the operation per request, across workers and after
   a crash: the request identity is recorded durably before the invocation;
2. a request already started whose outcome is unknown is never run again: it
   reports `remote_effect: unknown` and needs an explicit recovery (ERR-004,
   ERR-006, ERR-014);
3. a transport that cannot give this guarantee rejects such a request before
   any effect;
4. later, new versions of these operations with a mandatory idempotency key.

## Change statement

- **Consumers affected:** every consumer that reads a catalog of version 2
  to choose a surface; runtime consumers of artifacts that advertise
  Runtime Binding 2.0; runtime-tools for a claim of 2.0; maintainers of
  catalogs.
- **Before:** catalog surfaces could be read as availability; four absences
  had no stated reason; a result beyond a bound had no stated outcome.
- **After:** Public Catalogs 2.0 (CAT-001 to CAT-003) and Runtime Binding
  2.0 (RT-024, RT-025, RT-026), with the transition in COMPATIBILITY.md;
  1.0 unchanged.
- **Compatible:** yes for every existing document: two new contract
  versions, a new schema and two vectors next to the existing ones; no
  published text, schema, catalog, binding or vector changes meaning.
- **Schemas, examples and profiles:** new `public-catalog-v2.schema.json`
  and `runtime-negotiation-vector-v1.schema.json`; `vectors/runtime-v2`
  with two error vectors; `vectors/runtime-negotiation-v1` with the
  negotiation cases of RT-026; the profile index and the runtime-tools
  profile add obligations conditioned on the 2.0 versions, without changing
  a 1.0 claim; the validator checks catalogs against the schema of
  their contract, CAT-003 on catalogs of version 2, and `vectors/runtime-v2`
  like `vectors/runtime-v1`.
- **Adoption impact:** none until a component adopts its catalog of
  version 2 or an artifact claims Runtime Binding 2.0. With the stacked
  change:
  - database-tools: pin a revision with `database-tools-v2.json` and claim
    `plenora-public-catalog-v2`; write the reasons of DB-ABS-001 and
    DB-ABS-002 in its documentation and keep the handles out of every
    serialized surface (DB-ABS-003); on the runtime, accept the Arrow of
    `database.write` only by artifact reference (DB-RT-002) and fail a
    query result beyond its bound with `resource_limit`, declaring the
    bound in its capability attributes or adoption manifest (DB-RT-003,
    RT-024); give `Session.select` an Arrow result (gap, not absence).
  - data-tools: pin a revision with `data-tools-v3.json` and claim
    `plenora-public-catalog-v2`; no change while its capability document
    lists only the surfaces that answer; never bind `data.run` 3 on CLI or
    Python, nor `data.run` 2 on the runtime.
  - IO-tools: pin a revision with `io-tools-v3.json` and claim
    `plenora-public-catalog-v2`; no change while its capability document
    omits `runtime`; with the runtime (PR #27) it claims Runtime Binding 2.0
    or 1.0.
  - runtime-tools: optional claim of Runtime Binding 2.0 (transport bound
    in the manifest, `vectors/runtime-v2`).
