# Cutover plan

This document describes the replacement sequence. It is not authorization to
delete or publish anything.

## Guardrails

- Keep the existing remote repository intact until this candidate is reviewed.
- Do not rewrite immutable release manifests or historical evidence in component
  repositories.
- Do not claim compliance before a component has tests for the pinned contract.
- Recreate the final repository as private with a clean Git history.

## Reference inventory

The current repositories use `plenora-contracts` references in two different
ways:

1. Historical provenance: release manifests, old ADRs and frozen evidence cite
   a tag or revision. These records must remain unchanged.
2. Live authority: current documentation, gates and contributor instructions
   treat the old repository as the active specification. These references must
   move to an immutable revision of the replacement.

Observed live-reference areas:

- `database-tools`: current release/readiness scripts and documentation;
- `data-tools`: contributor guidance, source comments and active documentation;
- `IO-tools`: active release-contract checks, assurance docs and conformance
  ownership statements;
- `runtime-tools`: no current reference found;
- `rest-tools`: no current reference found.

## Sequence

1. Review the local candidate and approve its normative rules.
2. Initialize a clean local Git history and tag the first candidate revision.
3. Add component-owned adoption manifests and tests, one repository at a time.
4. Classify every old reference as historical or live before changing it.
5. Verify that no active gate depends on files that will disappear.
6. Obtain explicit confirmation for the irreversible remote deletion.
7. Delete and recreate `PlenoraETL/plenora-contracts` as a private repository.
8. Push only the clean replacement history.
9. Pin component adoption to an immutable replacement revision.

## Initial migration gaps

The inventory identified these expected migrations:

- `database-tools`: errors already use stdout and the four error axes, but exit
  codes and success envelopes are not common protocol v2 yet.
- `data-tools`: closest current implementation; its error stream and rich exit
  mapping are the basis for protocol v2, but success envelopes remain uneven.
- `IO-tools`: errors currently use stderr and its exit mapping differs; this is
  an explicit breaking migration.
- `runtime-tools`: no public common CLI or Python SDK surface was found; it may
  declare both contracts not applicable until such a surface exists.
- `rest-tools`: Python package naming, minimum Python version, lifecycle and
  error shape require alignment before it can claim SDK v1 adoption.
