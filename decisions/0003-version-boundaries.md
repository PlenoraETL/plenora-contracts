# Decision 0003: Do not redefine component-local v1 protocols

Status: accepted

## Context

Several components already publish a value named `protocol_version: 1`, but
their envelopes, streams and exit codes are not identical.

## Decision

The first common CLI protocol is version 2. Component-local version 1 contracts
remain historical facts and are not retroactively made equivalent.

The common Python SDK contract uses its own version sequence and starts at 1.
CLI and SDK versions are independent because they govern different boundaries.

## Consequences

- Adoption is an explicit migration, not a documentation-only claim.
- Consumers can distinguish old local envelopes from the common protocol.
- A future CLI breaking change increments `protocol_version`; an SDK breaking
  change increments the SDK contract version and the component's major version.
