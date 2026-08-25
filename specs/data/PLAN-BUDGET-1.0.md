# Plenora Plan Budget Contract 1.0

Status: normative

Contract identifier: `plenora-plan-budget-v1`

## 1. Applicability

This contract applies when a component accepts a declarative plan document at a
public boundary and publishes a plan identity derived from that document.

It governs three things only:

- the declared memory ceiling a plan may request for an isolated execution
  domain;
- the plan format version boundary that introduces that field;
- the identity consequences of the field for the canonical form and the plan
  hash.

Everything else in the plan document — operation nodes, edges, contracts,
options and every other limit — stays owned by the accepting component. This
contract does not promote the plan format as a whole.

**PLAN-001** — A component that does not accept plan documents at a public
boundary is unaffected by this contract.

## 2. Format versions

**PLAN-002** — Plan format version `6` is a distinct format. It is not
version `5` with an added field.

**PLAN-003** — Plan format versions `4` and `5` remain accepted under the rules
that already governed them. This contract does not deprecate them and does not
change what they accept.

**PLAN-004** — Earlier plan formats — the linear shapes a component may accept
below `schema_version` `4` — are **outside** this fragment entirely. This
contract does not describe them, does not require them, does not deprecate them
and does not change what they accept. A component that accepts them today keeps
accepting them.

**PLAN-005** — Those earlier formats cannot declare
`max_domain_memory_bytes`, and therefore cannot select the isolated execution
profile. That follows from PLAN-007 and PLAN-010 rather than being a new
restriction on them.

Rationale, informative. The version list in the machine-readable fragment stops
at `4` because that is where this contract starts governing, not because
anything below it is withdrawn. Reading a narrow fragment as a complete
enumeration of what a component may accept would turn a targeted ratification
into a silent revocation of existing compatibility.

**PLAN-006** — A component MUST reject a plan whose declared
`schema_version` it does not support. It MUST NOT interpret an unknown
version as the nearest known one.

Rationale, informative. The general consumer rule — ignore unknown optional
fields where the enclosing schema permits them — does not rescue this case,
because the plan document is a **closed** shape: the accepting components
reject unknown members rather than ignoring them.

A version 5 reader confronted with the new field therefore refuses the whole
document. Introducing the field inside version 5 would be backward compatible,
since old plans stay valid, and **not** forward compatible, since old readers
reject new plans — and forward incompatibility is the one that breaks
deployments, because that is where old readers already exist. Carrying two
mutually unreadable shapes under the same version number is precisely what a
version number exists to prevent.

## 3. The field

**PLAN-007** — `max_domain_memory_bytes` exists **only** in plan format
version `6`, inside the `limits` block. A version `4` or version `5` document
that declares it MUST be rejected.

**PLAN-008** — The value MUST be a positive integer representable in an
unsigned 64-bit integer. Zero, negative values, fractional values and values
outside that range MUST be rejected.

**PLAN-009** — The field is OPTIONAL. Its absence MUST NOT be treated as an
error, and MUST NOT be replaced by a default ceiling.

**PLAN-010** — When the field is absent, the isolated execution profile is not
selectable for that plan. A request to run that plan under the isolated profile
MUST be rejected rather than served with an implied ceiling.

## 4. Relation to the governed budget

**PLAN-011** — `max_domain_memory_bytes` MUST be greater than or equal to the
**effective** governed memory budget of the same plan.

**PLAN-012** — The effective governed budget is the value declared in the plan
when present, and the accepting component's documented default when the plan
omits it. The comparison is made against the effective value in both cases.

**PLAN-013** — A component MUST publish the default it applies. Without a
published default, PLAN-011 is not checkable by a caller before submission.

Rationale, informative. A domain ceiling below the budget the plan is allowed
to govern describes an execution that cannot succeed as declared. Rejecting it
at validation is cheaper and more legible than discovering it as an exhaustion
at run time.

## 5. What the value means

**PLAN-014** — The value is the ceiling the plan **requests**. It is not the
ceiling the host grants and it is not a guarantee that the plan will receive
it.

**PLAN-015** — The effective ceiling is `min(requested, host policy)`. The host
policy, how it is configured, how it is discovered and by what mechanism the
ceiling is enforced are **outside** this contract and outside the plan format.

**PLAN-016** — A component MUST NOT rewrite the declared value to the granted
one inside the plan document. The plan states the request; the granted ceiling
is reported through the component's own result surfaces.

Rationale, informative. Keeping the request in the artifact and the grant out of
it is what makes a plan portable: the same document submitted to two hosts with
different policies stays the same document, with the same identity, and the
difference shows up in the outcome instead of in the plan.

## 6. Identity

**PLAN-017** — A version `6` plan that declares `max_domain_memory_bytes` and
an otherwise identical version `6` plan that omits it are **different plans**.
When present, the field enters the canonical form and therefore the plan hash.

**PLAN-018** — Version `6` has a hash domain **distinct from version `5`**. A
version `5` document and a version `6` document that are otherwise identical
have **different** identities.

This states one relation, between two versions. It is **not** a general rule
that every plan format version has its own domain, and it must not be read as
one: some components migrate an older version into a newer canonical form and
publish the two as sharing an identity. That is exactly what happens today for
version `4`, which is migrated into the version `5` canonical form and
therefore shares its plan hash.

**PLAN-019** — This contract does **not** modify, generalize or withdraw any
identity relation among plan format versions below `6`. Migrations and
equivalences that already exist between earlier versions stay owned by the
accepting component, including the published equivalence between version `4`
and version `5`.

Rationale, informative. Introducing version `6` needs one new fact — that its
identities are separate from version `5`'s — and nothing else. Stating it as
«each version has its own domain» would have been shorter and would have
contradicted both PLAN-003 and a guarantee already published and regression
tested elsewhere. A contract that generalizes beyond what it needs revokes
things nobody asked it to touch.

**PLAN-020** — A version `5` plan MUST keep the canonical form, hash domain and
plan hash it already had. This contract changes nothing about already published
version `5` identities.

**PLAN-021** — A migration from version `5` to version `6` MUST NOT present the
two documents as having equivalent identity, and MUST NOT reuse the version `5`
hash for the migrated document.

Rationale, informative. The temptation is to say that a plan without the new
field keeps its hash, because nothing about it changed. That is true within
version `5` and false across **this** version boundary: version `6` canonicalizes
into its own domain, so the same nodes and edges expressed as version `6` are a
different plan.

Note the boundary is what does the work, not a general principle that a version
number always changes an identity — version `4` is evidence to the contrary,
since it canonicalizes into version `5` and keeps that hash. Stating the narrow
truth costs nothing. Stating the broad one would promise stability that the
format change does not deliver, and would revoke a guarantee that does hold.

## 7. Machine-readable fragment

The schema [`plan-budget-v1.schema.json`](../../schemas/plan-budget-v1.schema.json)
validates the **fragment** of a plan this contract governs:
`schema_version` and the two budget members of `limits`. It permits the
members it does not govern, because a real plan carries many more.

Its `schema_version` enumeration lists `4`, `5` and `6`: the versions this
contract governs. A document below `4` is **out of scope** (PLAN-004), not
invalid — this schema is simply not the one that describes it.

What the schema does **not** check:

- **PLAN-011**, because JSON Schema cannot compare two sibling values. It is
  enforced as a **semantic check** alongside the schema, and only for documents
  declaring both budgets: when the governed budget is omitted the comparison is
  against a component default this contract does not own (PLAN-012);
- PLAN-010, PLAN-014, PLAN-015 and PLAN-016, which are about behavior rather
  than document shape;
- PLAN-017 to PLAN-021, which are about identity across documents.

`examples/invalid/plan-budget-domain-below-governed.json` exists to prove the
distinction is real: the schema **accepts** it and the semantic check
**rejects** it. Without such a document, a check that only visited already
consistent examples could be deleted or inverted while the suite stayed green.

A validator that reports a document as conforming to this schema has checked
shape, not conformance to the contract.
