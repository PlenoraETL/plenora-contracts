# 0010: Rejection before invocation, result identity and controls on the runtime

Status: proposed

Date: 2026-10-06

## Context

Runtime Binding 1.0 and the typed error contract leave choices open where four
adopting libraries diverged once they exercised negative probes:

1. RT-004 admits `protocol` or `unsupported` for a routing mismatch, with no
   criterion;
2. the retry disposition of a rejection before invocation is not stated;
3. the result metadata of a rejection is not stated when the request carries
   no well-formed value to reflect, while the vector schema requires
   `plenora.capability.operation` and `plenora.operation.version` in every
   stored error vector and section 5 of the vectors contract keeps negative
   probes out of that schema;
4. the correlation identity is "required" in every result, but a request
   without a canonical correlation has none to preserve;
5. `plenora.message.causation_id` of a result is optional and has no rule;
6. the deadline is "an absolute RFC 3339 UTC timestamp", which leaves open
   `+00:00`, `-00:00`, lowercase `t`/`z`, a space for `T`, the number of
   fraction digits, a leap second, and the retry of an elapsed deadline;
7. a deadline in both the payload and the metadata has no rule;
8. a `plenora.*` metadata key the binding does not reserve, such as a
   misspelled control, has no rule;
9. a failed cleanup after a proven publication has no stated combination of
   axes.

## Compatibility test

COMPATIBILITY.md evaluates a change "from the point of view of a conforming
external consumer": it is compatible when such a consumer can continue to
invoke the same operation and interpret the result with the same meaning.
Two consumers matter here: the caller of the runtime surface, and the runtime
transport that carries component results.

- Choosing one value among those 1.0 already admits in a result is
  compatible: a conforming consumer already interprets every admitted value.
  It does make some producers non-conforming that were conforming, which is
  an adoption impact, recorded below, not a consumer incompatibility.
- Rejecting a request that 1.0 accepts from a conforming caller is
  incompatible: that caller can no longer invoke the operation.
- Changing the rule that consumers ignore unknown optional members
  (COMPATIBILITY.md, "Consumer behavior") is incompatible, and would also
  make every future optional metadata key a breaking change, against Runtime
  Binding 1.0 section 9.

## Decision

Ratified in Runtime Binding 1.0 and Typed Errors 1.0 as clarifications:

| gap | rule | compatibility |
|---|---|---|
| 1 | RT-017 (grammar, no normalization) and RT-018 (order: `protocol`, then `unsupported`, then `timeout`) | compatible: one of the two RT-004 values, which ERR-002 already prefers for a well-formed unsupported value |
| 2 | RT-016: `phase: validate`, `remote_effect: none`, `retry.kind: never` | compatible: `validate` and `none` follow from ERR-003 and ERR-004; `never` is the most conservative admitted value |
| 3 | RT-019: reflect only a well-formed value, byte for byte, otherwise omit | compatible: section 7 does not require these keys in an error; the vector schema's requirement applies to stored fixtures |
| 4 | RT-019: a rejection of a request without a canonical correlation carries none | compatible: only a non-conforming caller sends such a request, and the runtime-tools profile already makes the transport reject it before invocation |
| 5 | RT-020: a new message identity; causation SHOULD be present and, when present, MUST be the request's message identity | compatible; MUST-presence is not adopted, because the published success vectors omit it and stay immutable |
| 6, part | RT-021: a non-zero offset and `-00:00` are not UTC and fail with `protocol`; an elapsed deadline (`deadline <= now`) fails with `timeout` under RT-016; senders SHOULD use the `Z` spelling of the vectors | compatible: neither offset is UTC; `timeout` is SURF-010 |
| 7 | RT-023: both channels together fail with `invalid_configuration` | compatible: no shared input contract carries a deadline field today |
| 8, part | RT-022: a `null`, empty or over-bound idempotency key fails with `protocol`; a key on an operation without the control fails with `unsupported`; reuse with different input fails with `conflict` | compatible: metadata values are strings, and RT-006 and SURF-012 already require the rejections |
| 9 | ERR-014 (unknown after an unproven remote effect, even when the final failure is local; `requires_recovery` as a SHOULD) and ERR-015 (`cleanup` and `committed`; `never` for a local residue, `requires_recovery` for a remote one) | compatible: ERR-014 restates ERR-004 and keeps the retry a SHOULD because DT-RUN-006 admits `never`, `quarantine` or `requires_recovery`; ERR-015 picks values the schema admits |

The probes of `vectors/runtime-probes-v1` (new schema
`runtime-probe-v1.schema.json`) state the expected rejections as data, and the
validator derives each one from the rules above. Two storage error vectors
cover ERR-015.

Not ratified, because each one changes what a conforming caller may send:

- **Deadline spelling (rest of gap 6).** Rejecting `+00:00`, `z`, a space,
  more than nine fraction digits or `:60` rejects RFC 3339 UTC values a
  conforming caller may send today. Options: (a) accept every RFC 3339 UTC
  spelling in 1.0 and keep `Z` as the SHOULD for senders; (b) narrow the
  grammar in a new runtime binding version (capability version `2`); (c)
  narrow it in 1.0 by a governance decision that every adopter already
  rejects them, with the evidence of each adoption manifest. Recommended: (a)
  now, (b) with the next binding version.
- **Unknown `plenora.*` keys (rest of gap 8).** Rejecting them contradicts the
  consumer rule of COMPATIBILITY.md and would turn every optional metadata key
  added later into a breaking change. Options: (a) keep ignoring them, as 1.0
  requires today, and rely on RT-006 for controls the operation does not
  advertise; (b) reserve the `plenora.` prefix in a new binding version whose
  section 9 lists the keys a receiver must accept; (c) reject only the
  spellings a decision lists as known mistakes, a closed list kept here.
  Recommended: (a), with (b) if a future binding version is opened.
- **Rejecting a misspelled optional causation key** (gap 5, alternative): the
  same as the previous point.

## Alternatives

- **Leave the choices to each profile.** Every component would repeat the
  matrix, and the runtime transport would have to know each one.
- **A new runtime binding version for everything.** Correct for the two
  incompatible points, but it would move every adopter to capability version
  `2` for clarifications that 1.0 can carry.
- **MUST for the causation identity.** Contradicts the published success
  vectors, which omit it and cannot change.

## Change statement

- **Consumers affected:** callers of the runtime surface and the runtime
  transport, which can now rely on one category, one retry and one shape of
  result metadata for each rejection before invocation.
- **Before:** `protocol` or `unsupported` at the producer's choice; retry and
  result metadata unstated; the cleanup combination unstated.
- **After:** the rules RT-016 to RT-023, ERR-014 and ERR-015; the two points
  above stay as 1.0 states them.
- **Compatible:** yes, by the test above.
- **Schemas, examples and profiles:** new schema `runtime-probe-v1`, one
  invalid example, 21 probes, two storage error vectors. No existing schema,
  catalog, binding or vector changes. No profile changes.
- **Adoption impact:** a component pinned before this decision is unaffected
  until it moves its pin. After the move, every adopter exercises the probes
  whose base request it advertises: database-tools (`database.read`),
  data-tools (`data.run` 3), IO-tools (`io.read`), rest-tools (`rest.upload`),
  storage-tools (`storage.get`, and the two `storage.put` cleanup vectors);
  runtime-tools exercises all of them. A component that chose `unsupported`
  for a malformed value, `safe` for a rejection, or reflected a normalized
  value records a deviation until it changes.
