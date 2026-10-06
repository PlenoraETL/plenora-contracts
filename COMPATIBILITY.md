# Public compatibility policy

Compatibility is evaluated from the point of view of a conforming external
consumer.

## Compatible changes

A change is compatible only when an existing conforming consumer can continue
to invoke the same operation and interpret the result with the same meaning.

Typical compatible changes are:

- adding an optional field whose absence preserves the previous behavior;
- exposing a new operation under a new stable identifier;
- adding a new public surface to an existing operation;
- adding an unavailable capability with an explicit reason;
- clarifying prose without changing accepted data or semantics.

## Incompatible changes

The following are incompatible:

- removing or renaming an operation, required field or public symbol;
- changing the meaning, type, units or default of a field;
- changing a success into a partial outcome, or an acknowledged partial
  outcome into success;
- weakening remote-effect or retry information;
- silently replacing one output contract or content type with another;
- changing CLI stream selection or exit-code projection;
- dropping a supported SDK runtime version outside the component's declared
  compatibility policy;
- changing a closed enumeration without an explicit version transition.

An incompatible change requires a new public contract version. A component may
temporarily expose old and new versions together and advertise both through
capability discovery.

## Operation evolution

Operation identity and operation contract version are independent from package
and component release versions. A component patch or minor release may expose a
new compatible operation. It must not change an existing operation contract
incompatibly without incrementing that contract version.

## Consumer behavior

Consumers must select only advertised operations and versions. They must ignore
unknown optional fields where the enclosing schema permits them and must fail
closed on unknown required contract versions.

## Immutability of published documents

A versioned JSON Schema may be changed in place only when the edit cannot alter
whether an existing instance validates. Otherwise a new schema identifier and
file are required.

The machine-readable documents that carry operation identities are fixed in the
same way once published on `main`:

- a public catalog (`catalogs/*-tools-v<N>.json`) may add a new operation
  identity `(id, version)`, add a surface to an existing operation, select a
  target surface that was `undecided` or `not_applicable`, clarify an
  operation `summary`, and move its `status` from `provisional` to
  `normative`. Every other field of a published operation identity, and of
  the catalog itself, is fixed; an identity is never removed;
- an operation registry (`catalogs/*-v<N>.json` with contract
  `plenora-operation-registry-v1`) may add kernels; a listed kernel keeps its
  entry;
- a surface binding map (`bindings/*-v<N>.json`) may name the artifact of a
  component section that had none, add discovery entrypoints and bind new
  operation versions; a published binding keeps its requirement and
  entrypoints, and no section is removed;
- a normative vector (`vectors/**/*.json`) is never changed or removed; a
  corrected or replaced vector is a new file.

A protected document whose kind the gate does not recognize is compared whole.

### Errata before adoption

The only exception is a declared erratum: a schema or another protected
document found wrong before any component adopted it and before any release
used it may be corrected in place once, by a decision that states the defect,
the date and the absence of adopters. The immutability gate (`ERRATA` in
`tools/check_schema_immutability.py`) admits exactly that transition, from the
published content to the corrected one, only while the decision exists and
names the file in its `## Erratum` section, and only against a base that still
published the erroneous content (the declared last base or one of its
ancestors); against a later base the erratum admits nothing. Recorded errata:
`data-execution-result-v3.schema.json` and `data-run-success-v3.json`
([decision 0008](decisions/0008-data-run-runtime.md)).

CI compares the protected documents against three revisions: the base of
the change, the ratified floor recorded in
`tools/check_schema_immutability.py` and the commit where the checked revision
left `origin/main` (`tools/ci_comparison_base.py`). The base of a push to
`main`, forced or not, is the previous tip of `main`; the base of a release
tag `v*` is the tagged commit, which must be a commit of `main`; the base of a
pull request, or of a push to another branch, is the commit where it leaves
`main`, because a branch's previous tip may predate changes that `main` made
legitimately. In addition, every document the checked tree changed since it
left `main` is compared with the current `origin/main`, so a branch cannot
rewrite a document `main` published after the branch forked; a document the
branch did not touch takes `main`'s content when merged and is not compared.
In CI `origin/main` is fetched first and must equal the remote's
`refs/heads/main`; an older ref fails the check instead of hiding what `main`
published since.
The fork point also protects documents published after the floor on the first
push of a new branch. Without
`origin/main` the gate fails; outside CI, `PLENORA_ALLOW_NO_FORK_POINT=1`
waives that revision explicitly and the gate checks the other two (the waiver
is ignored when `CI`, `GITHUB_ACTIONS` or `GITHUB_RUN_ID` is set). Files of
the checked tree are listed by Git, ignored files under the protected
directories included, and each counts only with the exact spelling it has on
disk, so a rename that changes only letter case is a removal on every file
system. It rejects removed documents, changed assertions and identities, and reused schema
identifiers. The guard treats only schema annotations as editable prose; a
property or literal named `description` remains part of the validation rules.

## Repository releases

A repository release is an annotated Git tag `vMAJOR.MINOR.PATCH` on a commit
of `main`, with a matching section in [CHANGELOG.md](CHANGELOG.md); the tag
carries the date. The tag is a readable name for that commit and for the
changes the CHANGELOG lists up to it; it does not replace the pin. An adoption manifest records the full
commit SHA (see [ADOPTION.md](ADOPTION.md)) and may cite the tag next to it.
A tag is never moved or reused.

The repository version follows the documents it publishes:

- MAJOR: a published document, identifier or rule is withdrawn or changes
  meaning, which the immutability rules above admit only through a declared
  erratum or a governance decision;
- MINOR: new contract versions, operations, surfaces, schemas, catalogs or
  vectors, next to the existing ones;
- PATCH: compatible prose clarifications, errata, validator and tooling
  changes that do not alter any published document.

Every commit of `main` remains a valid pin; a release only names one.
