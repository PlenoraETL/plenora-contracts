# 0024: Geometric operation expectations before implementation

Status: accepted
Date: 2026-11-16

## Context

The owner approved all recommendations D1–D12 of the geometry inventory's
PIANO.md on 2026-11-16. The family baseline is
`38d68b402389855edbcecb7ce57c31e91282cb4e`; the implementation inventory
describes data-tools 6.0.0 at `c9641c18d4cb2117c0b249293a7600fd5a9b7cda`.
This decision records authority, not implementation or ArcGIS certification.
The source inventory and its fixed documents are identified by digest in the
[oracle plan](../conformance/GEOMETRY-ORACLES-1.0.md).

## Decision

Adopt [Geometry Operations 1.0](../specs/data/GEOMETRY-OPERATIONS-1.0.md),
an opt-in family contract for new boundaries shared by geometry producers
and consumers. Its product selections make the first domain deterministic;
they are not claims that the owner approved unobserved ArcGIS behavior.

| Decision | Family rule and rationale | Rejected alternatives |
|---|---|---|
| D1 | Explicit planar computation in the SR's coordinates, including angular coordinates; geodesic is a different model. Prevent unit/model confusion. | Blanket geographic ban on new APIs; implicit projection. |
| D2 | Keep Web Mercator rejection. A future clamp is explicit, threshold documented and qualified. The existing 85.06 degree limit is not the tile limit 85.0511. | Automatic clamp; silently narrowing today's valid latitude interval. |
| D3 | Parametric extrapolation only by opt-in, outside accuracy assurance; no fictitious grid samples outside coverage. | Unconditional application; treating a selected transformation as unlimited accuracy. |
| D4 | Structural Esri WKT parsing with a declared verified alias subset, parameters and units checked. | Resolving by the CRS name alone. |
| D5 | Qualified output repair is opt-in in a new API. Whether to retain the service's existing generalize fallback remains an owner decision. | Implicit repair; treating approval as permission to retain or remove that fallback. |
| D6 | New APIs count actual candidate evaluations, temporary bytes and cancellation; old budget meanings remain. | Product/square estimates as new admission rules; u64::MAX as a general solution. |
| D7 | Dimensional hull opt-in; separate splitLine attachment and cut-merging tolerances. | Changing existing hull result types or the current double-use tolerance. |
| D8 | Internal budgets plus isolation; shared duplicate geometry must preserve external cardinality. Streaming needs declared atomic/partial semantics. | Isolation alone; silently dropping duplicates; truncated success. |
| D9 | Distinct planar, shortest-geodesic and preserveShape models, explicit domains and certified errors. | Local approximations without a bound; vertex-only geometric distance. |
| D10 | Reusable DE-9IM semantics and an explicit Esri subset with dimension table and grammar. Line-boundary ambiguity is fenced by domain. | Calling OGC Within Esri Within; universal BB=1 for lines; implicit mixed output. |
| D11 | Documented editing domain, explicit ambiguous-case errors, declared XY/Z/M behavior. | Region-selection heuristics; silent repair or ordinate loss. |
| D12 | Separate standard-derived and Esri text profiles, cell point, datum, rounding and invalid-input rules. | Permissive guessing; a round trip used as the only correctness oracle. |

## Consequences

The first possible component release is **6.1.0, additive**. This is not a
promise that every family ships together. New APIs/types/options preserve
old defaults, accepted inputs, result bytes where promised, order and errors.
Successive additive minors may deliver remaining families.

New refusals of formerly valid requests, changed tolerance/repair/CRS defaults,
different coordinate interpretation, output cardinality, duplicate removal,
observable order or broken public Rust signatures require **7.0.0**. Adding
variants to exhaustive public enums or required struct fields can break Rust
even when JSON stays compatible. A safety change is not exempt by being
called a bug fix. Optimizations with unchanged public behavior are additive.

As [decision 0003](0003-version-boundaries.md) requires, component release,
operation/kernel semantic version, configuration schema, contract-analysis
version, family contract, CLI and runtime versions are independent. Increment
only affected axes, with a new immutable identity when meaning changes.
No existing schema, catalog, profile, binding or vector is rewritten here.

This step does not register executable operation IDs or Rust signatures.
The new contract specifies shared expectations, not a plan node format.
Public Catalogs 2.0 section 6 requires registered identities and an appropriate
target profile when new plan kernels are named. COMPATIBILITY.md allows additive
kernel entries; incompatible changes require a successor identity/registry.
CAP-009 forbids advertising the
design as available; CAP-013 keeps detailed selection in the component's
versioned descriptor. Existing data-tools DT-ARROW-004 is not overridden.

## Alternatives

A single universal Esri compatibility claim would turn unresolved server
behavior into invented expectations. The bounded product subset instead
rejects those requests explicitly and permits a later, versioned qualification.
Changing Arrow Geometry Semantics 1.0 in place would alter the fixed CRS alias
grammar for existing adopters. A separately named ingress adapter may resolve
new aliases before producing canonical Arrow; it must not reinterpret an
already received v1 Arrow field.

## Verification and adoption

The [oracle plan](../conformance/GEOMETRY-ORACLES-1.0.md) separates analytic
and reference-implementation fixtures from cases requiring a real ArcGIS
build. No server was queried. Repository vectors cover existing Arrow and
runtime obligations, not numerical qualification of an absent engine.
Adopters must add black-box evidence and pinned fixture provenance before
claiming each supported domain. D5's interim fallback and selection of an
ArcGIS Enterprise qualification build remain owner actions.
