# 0020: The cause of an unknown commit outcome, checked in the vectors

Status: accepted

Date: 2026-10-10

## Context

[Decision 0019](0019-category-of-an-unknown-commit-outcome.md) added ERR-016:
the cause of an unknown commit outcome decides the category (`io` for a lost
confirmation, `timeout` for an elapsed deadline, `internal` for a defect of
the component). It added a vector for the lost confirmation; the elapsed
deadline had none, and nothing checked that a vector's category matches its
cause.

## Decision

- New runtime vector `database-write-commit-timeout-error.json` (`timeout`,
  phase `commit`, `unknown`, `requires_recovery`).
- The validator checks every runtime error vector with phase `commit` and
  an unknown remote effect: when its `code` is in a closed map
  (`COMMIT_CONFIRMATION_LOST`, `COMMIT_DEADLINE_ELAPSED`,
  `COMMIT_OUTCOME_UNKNOWN`) the category is the one the map gives; with
  another code, such as the published `storage-put-unknown-error.json`
  (`timeout`), the category is one of `io`, `timeout` and `internal`; the
  retry is always one ERR-006 admits. Runtime Vectors 1.0 section 5 states the map.
  The codes are those of the vectors, not a requirement on the codes a
  component emits: a component's own code is component-owned (ERR-013).

## Change statement

- **Consumers affected:** adopters that exercise the runtime vectors.
- **Before:** one vector per cause missing; no check between cause and
  category.
- **After:** the timeout vector and the check.
- **Compatible:** yes; the published vectors pass the check unchanged.
- **Schemas, examples and profiles:** one runtime vector; prose in Runtime
  Vectors 1.0.
- **Adoption impact:** database-tools exercises the new vector with
  `database.write` on the runtime.
