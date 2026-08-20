# Cutover and adoption plan

The repository replacement was completed on 2026-08-18. The former remote
history, branches and tags were not carried into this repository. The remaining
work is component-owned adoption.

## Guardrails used for replacement

- The former remote was kept intact until the replacement candidate was
  reviewed and explicit deletion confirmation was received.
- Do not rewrite immutable release manifests or historical evidence in component
  repositories.
- Do not claim compliance before a component has tests for the pinned contract.
- The final repository was recreated as private with a clean Git history.

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
- `storage-tools`: repository not yet developed; no live reference exists.

## Completed replacement sequence

1. The candidate was reviewed and its normative scope was fixed.
2. A clean local Git history was initialized.
3. Explicit confirmation was obtained for the irreversible remote deletion.
4. `PlenoraETL/plenora-contracts` was deleted and recreated as private.
5. Only the replacement history and branch `main` were published.
6. The specification validator was run locally and in GitHub Actions.

## Remaining adoption sequence

1. Add component-owned adoption manifests and tests, one repository at a time.
2. Classify every old reference as historical or live before changing it.
3. Keep immutable release manifests and historical evidence unchanged.
4. Verify that no active gate depends on files removed with the old repository.
5. Pin each component to an immutable replacement revision.

## Initial migration gaps

The inventory identified these expected migrations:

- `database-tools`: errors already use stdout and the four error axes, but exit
  codes and success envelopes are not common protocol v2 yet.
- `data-tools`: closest current implementation; its error stream and rich exit
  mapping are the basis for protocol v2, but success envelopes remain uneven.
- `IO-tools`: errors currently use stderr and its exit mapping differs; this is
  an explicit breaking migration. The adopted decision is a component major
  cutover: the first conforming release is `2.0.0` or later in the `2.x` line,
  and one artifact does not serve both CLI JSON protocols. Deprecated command
  aliases may remain only when they emit protocol v2.
- `runtime-tools`: no public common CLI or Python SDK surface was found; it may
  declare both contracts not applicable until such a surface exists.
- `rest-tools`: Python package naming, minimum Python version, lifecycle and
  error shape require alignment before it can claim SDK v1 adoption.
- `storage-tools`: no operations or public surfaces are standardized yet; its
  provisional profile must be completed before the first stable release.

## Scope after cutover

Decision 0004 expanded the replacement from CLI/SDK conventions to all shared
public surfaces. This does not change the cutover history above. New adoption
uses component profiles and adoption manifest v3; no internal implementation
architecture is centralized.
