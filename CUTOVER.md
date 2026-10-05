# Cutover and adoption plan

Historical record of the repository replacement of 2026-08-18. It is not
maintained: the current status, verification and deviations of each component
live in that component's adoption manifest (see [ADOPTION.md](ADOPTION.md)),
and the current target surface in its [profile](profiles/README.md).

The repository replacement was completed on 2026-08-18. The former remote
history, branches and tags were not carried into this repository. The remaining
work is component-owned adoption.

## Guardrails used for replacement

- The former remote was kept intact until the replacement candidate was
  reviewed and explicit deletion confirmation was received.
- Do not rewrite immutable release manifests or historical evidence in component
  repositories.
- Do not claim compliance before a component has tests for the pinned contract.
- The final repository was recreated with a clean Git history (private at
  the time; its visibility is not part of this record).

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
- `storage-tools`: active experimental implementation with component-owned
  schemas and no qualified release claim yet.

## Completed replacement sequence

1. The candidate was reviewed and its normative scope was fixed.
2. A clean local Git history was initialized.
3. Explicit confirmation was obtained for the irreversible remote deletion.
4. `PlenoraETL/plenora-contracts` was deleted and recreated (as private).
5. Only the replacement history and branch `main` were published.
6. The specification validator was run locally and in GitHub Actions.

## Remaining adoption sequence

1. Add component-owned adoption manifests and tests, one repository at a time.
2. Classify every old reference as historical or live before changing it.
3. Keep immutable release manifests and historical evidence unchanged.
4. Verify that no active gate depends on files removed with the old repository.
5. Pin each component to an immutable replacement revision.

## Initial migration gaps

The migration gaps observed on 2026-08-18 were a snapshot of component status,
which this repository does not own. They were removed; each component's
adoption manifest records its status and deviations, and its profile the
target. Two decisions recorded with them still hold: IO-tools performs the CLI
protocol v2 cutover as a component major release, now `4.0.0`
([profile](profiles/io-tools.md)), and the storage profile has since selected
the Python SDK surface ([decision 0006](decisions/0006-storage-python-surface.md)).

## Scope after cutover

Decision 0004 expanded the replacement from CLI/SDK conventions to all shared
public surfaces. This does not change the cutover history above. New adoption
uses component profiles and adoption manifest v4; no internal implementation
architecture is centralized.
