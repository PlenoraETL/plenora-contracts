# Plenora Interface Contracts

This repository defines the shared public conventions for Plenora command-line
interfaces and Python SDKs.

The contracts are deliberately small. They standardize the boundary that an
orchestrator or an SDK consumer can rely on, while each component remains the
owner of its domain behavior.

## Authority

The normative sources are:

- [CLI contract](specs/cli/CLI-2.0.md)
- [Python SDK contract](specs/sdk/PYTHON-SDK-1.0.md)
- the versioned JSON Schemas in [schemas](schemas)

Examples illustrate those sources but do not override them. Decisions explain
why a rule exists but are not a second specification.

## Scope

This repository owns only:

- process-level CLI behavior shared across Plenora components;
- machine-readable success and error envelopes;
- stable error axes and exit-code projection;
- capability discovery and interface-version reporting;
- common Python SDK naming, lifecycle, typing, error and security rules;
- an adoption manifest that components can keep in their own repositories.

## Explicit exclusions

This repository does not own:

- database, file-format, REST, geospatial or runtime domain semantics;
- Arrow schemas used by a specific operation;
- SQL dialects, plans, catalogs, provider capability matrices or wire formats;
- shared runtime code or Python wrappers;
- component release evidence, performance baselines or qualification campaigns;
- snapshots of the implementation status of individual repositories.

Those artifacts stay with the component that implements and verifies them.

## Versions

The first common CLI contract is protocol version 2. Existing component-local
protocols named version 1 are not silently redefined.

The Python SDK contract starts at version 1 because it describes a new common
behavioral surface rather than replacing a shared wire protocol.

Schema identifiers are immutable. A compatible clarification may update prose;
an incompatible machine contract requires a new schema and protocol version.

## Adoption

A component adopts these contracts by:

1. adding an adoption manifest that validates against
   `schemas/adoption-manifest-v1.schema.json`;
2. pinning an immutable revision of this repository;
3. testing its own CLI and SDK against that pinned revision;
4. recording temporary deviations explicitly instead of claiming compliance.

The component remains responsible for its tests. This repository validates the
specification itself; it is not a central integration-test harness.

## Repository status

This repository is the clean replacement for the former mixed-scope contracts
repository. The remote is private and contains only the new history. Component
adoption remains explicit: no component is conforming until its own pinned
manifest and verification are in place.
