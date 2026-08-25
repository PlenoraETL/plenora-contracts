# Decision 0005: Introduce plan format v6 instead of extending v5

Status: accepted

## Context

An isolated execution profile needs the plan to declare the memory ceiling it
requests for its execution domain. The obvious move is to add an optional
member to the existing plan format: optional members whose absence preserves
previous behavior are normally compatible additions.

That reasoning does not hold here. The accepting components reject unknown plan
members rather than ignoring them. A version 5 reader confronted with a
document declaring the new member does not skip it — it refuses the document.

The addition is therefore backward compatible, since old plans stay valid, and
**not** forward compatible, since old readers reject new plans. Forward
incompatibility is the one that breaks deployments, because old readers already
exist there.

The same repository already has the precedent: the rename from
`max_memory_bytes` to `max_governed_memory_bytes` required an explicit
migration and a schema version increment, for exactly this reason.

## Decision

`max_domain_memory_bytes` is introduced in a **new plan format version 6**, not
added to version 5.

- versions 4 and 5 remain accepted under the rules that already governed them;
- the field exists only in version 6, inside `limits`;
- the field is optional; its absence means the isolated profile is not
  selectable for that plan, never an implied ceiling;
- each plan format version has its own hash domain;
- an existing version 5 plan keeps its canonical form and its plan hash;
- a version 6 plan belongs to the new domain, so a version 5 document and an
  otherwise identical version 6 document are different identities;
- when present, the field participates in the canonical form and the hash, so a
  version 6 plan with the field and one without are different plans.

The value is what the plan **requests**. The effective ceiling is
`min(requested, host policy)`. Host policy and enforcement mechanism stay
outside the plan format.

The normative text is [Plan Budget 1.0](../specs/data/PLAN-BUDGET-1.0.md).

## Alternatives considered

**Keep version 5 and declare forward incompatibility.** Cheaper: no migration,
no adoption cycle. Rejected because two mutually unreadable document shapes
would carry the same version number, which is precisely what a version number
exists to prevent. A reader's refusal would be indistinguishable from a
malformed document.

**Make the field mandatory in version 6.** Rejected: it would force every plan
to state a ceiling for a profile most plans never select, and would make the
migration from version 5 lossy for plans that have nothing to declare.

**Let the component substitute a default when the field is absent.** Rejected:
a default ceiling is a silent grant. A plan that never asked for isolation would
receive a domain sized by something it cannot see, and the caller could not
distinguish "I asked for this" from "someone chose for me".

## Change statement

Required by [governance](../GOVERNANCE.md).

- **Affected public consumer.** Any caller or orchestrator that submits plan
  documents to a component accepting them publicly, and anyone who stores or
  compares plan hashes.
- **Observable behavior before.** Plan format versions 4 and 5 are accepted. No
  plan can declare a domain memory ceiling. Every accepted plan hashes inside
  its own version's domain.
- **Observable behavior after.** Unchanged for versions 4 and 5, including
  their hashes. Version 6 is additionally accepted and may declare
  `max_domain_memory_bytes`. A version 6 document has an identity distinct from
  an otherwise identical version 5 document.
- **Compatible?** Yes as a contract change, because it is delivered as a new
  format version and no existing version changes meaning. It is **not** an
  additive field change: adding the member to version 5 would have been
  forward incompatible, which is why the version exists.
- **Schemas, examples and profiles affected.**
  [`plan-budget-v1.schema.json`](../schemas/plan-budget-v1.schema.json), six new
  examples, the semantic budget check in `tools/validate_specs.py`, and the
  [data-tools profile](../profiles/data-tools.md).
- **Adoption impact.** Only components whose profile lists Plan Budget 1.0.
  Today that is data-tools, which must add an explicit version 6 path, publish
  the default it applies to the governed budget, and register the identity
  boundary as an incompatibility for consumers migrating documents. Components
  that do not accept plans publicly are unaffected.

## Consequences

- Components accepting plans need an explicit version 6 path; they cannot treat
  it as version 5 with an extra member.
- Plan identities do not survive a version 5 to version 6 migration, and no
  migration may claim they do. Callers that cached identities must re-derive
  them for migrated documents.
- Callers cannot check the relation between the domain ceiling and the governed
  budget before submission unless the component publishes the default it
  applies when the governed budget is omitted. Publishing it becomes a
  requirement rather than a courtesy.
- The plan format as a whole is **not** promoted to this repository by this
  decision. Only the budget field, the version boundary and the identity
  consequences are ratified here.
