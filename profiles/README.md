# Component public profiles

Profiles tell an adopter which public functionality families and boundary
contracts apply. They do not describe internal architecture and do not report
current implementation status.

## Surface terms

- **required**: the component profile expects a released public artifact on this
  surface.
- **conditional**: required for each operation intentionally exposed on that
  surface.
- **not required**: the profile does not require this surface; if published, it
  must still follow the applicable common contract.
- **undecided**: no stable public product decision has been made.

| Domain component | Rust | CLI | Python SDK | Runtime |
|---|---:|---:|---:|---:|
| database-tools | required | required | required | conditional |
| data-tools | required | required | not required | conditional |
| io-tools | required | required | not required | conditional |
| rest-tools | required | not required | required | required |
| storage-tools | required | required | not required | required |

The exact target operations are machine-readable in:

- [`database-tools-v1.json`](../catalogs/database-tools-v1.json);
- [`data-tools-v1.json`](../catalogs/data-tools-v1.json) and the
  [`data kernel registry`](../catalogs/data-kernels-v1.json);
- [`io-tools-v1.json`](../catalogs/io-tools-v1.json);
- [`rest-tools-v1.json`](../catalogs/rest-tools-v1.json);
- [`storage-tools-v1.json`](../catalogs/storage-tools-v1.json).

Canonical public entrypoints are in [`bindings`](../bindings/) and reviewed
cross-library handoffs are in
[`composition/pipelines-v1.json`](../composition/pipelines-v1.json).

## Common obligations

Every domain profile requires:

- stable component and operation identity;
- truthful Capability Discovery 2.0;
- versioned input and output contract identifiers;
- typed public errors;
- secure public defaults and redacted boundary data;
- equivalent semantics across every surface advertising the same operation;
- black-box conformance evidence owned by the component.

Arrow and row diagnostics apply only to operations declaring those public
representations.

Operations listing the `runtime` surface follow Runtime Binding 1.0.
The transport that consumes those operations follows the separate
[runtime-tools profile](runtime-tools.md); it is not a sixth domain profile.

## Status

Profiles are target applicability documents. The component-owned adoption
manifest records what is implemented, which revision was tested and any
temporary deviations.

## Profiles

- [database-tools](database-tools.md)
- [data-tools](data-tools.md)
- [io-tools](io-tools.md)
- [rest-tools](rest-tools.md)
- [storage-tools](storage-tools.md)

Transport consumer:

- [runtime-tools](runtime-tools.md)
