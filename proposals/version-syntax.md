# Component version syntax

Status: proposal; not an adopted contract or a new accepted wire format.

The component-version patterns in the published CLI envelope v2 and capability
document v2 accept a numeric triplet and at most one suffix introduced by `-`
or `+`. This is the grammar currently accepted by those schemas, not a complete
implementation of [Semantic Versioning 2.0.0](https://semver.org/).

## Observable difference

| Component version | Published patterns | SemVer 2.0.0 |
| --- | --- | --- |
| `1.2.3` | accepted | accepted |
| `1.2.3-rc.1` | accepted | accepted |
| `1.2.3-rc.1+build.9` | rejected | accepted |
| `1.2.3-01` | accepted | rejected |
| `1.2.3+build..9` | accepted | rejected |

Replacing the patterns in place would both admit previously rejected data and
reject previously admitted data. It would violate schema immutability even if
the replacement were described as a bug fix. Existing consumers and published
adoption manifests therefore retain their current schema identifiers and pins.

## Proposed successor

A successor to the CLI envelope and capability document can specify SemVer
2.0.0 explicitly, with shared positive and negative vectors for pre-release
identifiers, leading zeroes, build metadata and empty identifiers. Ratification
must assign new schema and contract identifiers and document how a consumer
selects the new protocol. An optional field added to the old closed shape is
not a substitute for a protocol transition.

The adoption impact includes CLI producers and readers, SDK capability readers,
runtime discovery and the component-owned publication gates. Component version,
operation version and contract version remain distinct concepts. No component
release or adopted pin is changed by this proposal.

The regression suite records the published patterns' behavior so a future
cleanup cannot accidentally perform this migration under the old identifiers.
