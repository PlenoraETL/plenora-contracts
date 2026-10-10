# 0019: The category of an unknown commit outcome

Status: accepted

Date: 2026-10-10

## Context

database-tools (PR #114) turns an unknown commit outcome into an error with
category `internal`, phase `commit`, `remote_effect: unknown` and retry
`requires_recovery`, exit code 70, on CLI, SDK and runtime. The published
runtime vector `database-write-error.json` has the same axes. The question is
whether an uncertain outcome is `internal`.

## Decision

**ERR-016** (Typed Errors 1.0, a clarification): the uncertainty is the
remote effect, not the category. The category names the cause: `io` for a
lost connection or stream after the commit was sent (exit 5), `timeout` for
an elapsed deadline (exit 5), `internal` only for a defect of the component
(exit 70). In every case `remote_effect: unknown` and, normally,
`requires_recovery`.

The published vector is not rewritten (COMPATIBILITY.md): Runtime Vectors 1.0
now states that it illustrates the defect case. A new vector,
`database-write-commit-io-error.json`, shows the lost confirmation.

## Compatibility

As in [decision 0010](0010-runtime-rejection-and-identity.md): `io`,
`timeout` and `internal` are all admitted by `error-v1` and project to exit
codes CLI 2.0 already defines; a consumer that acts on `remote_effect` and
`retry`, as ERR-004 and ERR-006 require, behaves the same. A producer that
reports every unknown outcome as `internal` records an adoption impact.

## Change statement

- **Consumers affected:** callers and orchestrators of writes and commits.
- **Before:** the category of an unknown outcome was not stated; the only
  vector showed `internal`.
- **After:** ERR-016; the old vector's scope stated; one new vector.
- **Compatible:** yes, by the test above.
- **Schemas, examples and profiles:** one runtime vector; prose in Typed
  Errors 1.0 and Runtime Vectors 1.0.
- **Adoption impact:** database-tools (#114) reports a lost confirmation as
  `io` (exit 5) and a deadline as `timeout` (exit 5), keeping `internal`
  (exit 70) for its own defects; the axes `unknown` and `requires_recovery`
  stay as #114 has them.
