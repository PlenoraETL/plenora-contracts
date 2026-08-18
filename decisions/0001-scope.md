# Decision 0001: Narrow interface-contract scope

Status: accepted for the replacement candidate

## Context

The previous contracts repository combined an interface specification with
domain rules, conformance data, component snapshots, evidence, generated files
and release history. That made ownership ambiguous and allowed the central
repository to become stale while the component implementations evolved.

## Decision

The replacement repository specifies only common CLI and Python SDK behavior.
It contains no shared implementation and owns no component qualification.

Domain contracts stay in their implementing repositories. Components pin an
immutable contracts revision and test their own adoption locally.

## Consequences

- A change to a database or file-format contract does not require this
  repository to mirror the implementation.
- Current component status is not represented here.
- Common boundary behavior can evolve independently through explicit versions.
- Historical release records in component repositories remain historical and
  are not rewritten during the cutover.
