# 0016: The IO-tools Python SDK as a declared surface

Status: accepted

Date: 2026-10-10

## Context

`io-tools-v2.json` selects the Python SDK as `not_applicable`, and the Python
binding map has an empty IO-tools section. IO-tools nevertheless ships
`plenora-io`, a pure-Python wrapper of the `plenora-io` CLI. Until now it was
outside the profile by choice: it covered six operations of seven, had no
capability discovery and exposed the error axes only inside an envelope
object.

plenora-IO-tools PR #44 (`sdk/capabilities-profilo-v1`, head `a2b5766`)
writes the package against Python SDK 1.0: `Client.capabilities()`,
`plenora_io.version()`, the five error axes as attributes of every public
exception, a method-to-operation map (`OPERAZIONI`) checked against the real
binary, Python 3.10 to 3.14, and an optional `plenora-io[pyarrow]` extra for
Arrow objects. The package does not claim the contract while the catalog
does not declare the surface.

## Decision

- The catalog selects `python_sdk` as `conditional` and adds it to the six
  operations of version 2. Both are additions COMPATIBILITY.md admits.
  Catalog version 1 keeps `not_applicable`.
- `bindings/python-sdk-v1.json` names `plenora-io / plenora_io`, discovery
  `plenora_io.version` and `Client.capabilities`, and one `Client` method
  per operation, as `OPERAZIONI` maps them: `catalog`, `inspect`, `layers`,
  `read` (with `read_table` and `validate`), `write`, `convert`.
- The profile makes the SDK optional and adds **IO-PY-001**: synchronous only,
  recorded in `api_modes`; the semantics of the operation on the CLI,
  including the effect `Client.read` adds by writing where the caller names
  (SB-001); `validate` and `read_table` bind `io.read`; without the PyArrow
  extra an Arrow object is refused with a typed error.
- The validator checks the IO-tools section like the data-tools one
  (`io_python_errors`).

## Merge condition

This change is merged only after plenora-IO-tools PR #44. Merged earlier, the
binding map would name methods (`Client.capabilities`, `Client.read_table`)
that no released package has, and the catalog would select a surface whose
only implementation does not yet expose the error axes as Python SDK 1.0
section 6 requires. The surface stays `conditional`: an IO-tools artifact
without the package remains conforming (CAT-001 of decision 0015, when
merged).

## Alternatives

- **Keep `not_applicable`.** The package exists and is used by the
  interoperability suite; leaving it outside the contracts leaves its
  spellings and semantics unchecked.
- **Require both API modes.** A wrapper of a process-level CLI gains nothing
  from a nominal async API, and Python SDK 1.0 section 4 admits a single mode
  recorded in the manifest.

## Change statement

- **Consumers affected:** Python callers of IO-tools.
- **Before:** no shared Python surface for IO-tools.
- **After:** an optional SDK with canonical spellings and IO-PY-001.
- **Compatible:** yes: a `not_applicable` target becomes decided and
  operations gain a surface; an artifact without the package is still
  conforming.
- **Schemas, examples and profiles:** catalog version 2 and Python binding
  map extended; IO-tools profile version 2 and Surface Bindings 1.0 section
  4 updated; no schema or vector changes.
- **Adoption impact:** IO-tools may declare `plenora-python-sdk-v1` for the
  package after PR #44 and after moving its pin; its manifest records
  `api_modes: ["sync"]`; `Client.capabilities()` must return a document
  that lists the `python_sdk` interface and surface (CAP-003, CAP-007), and
  `io.read` declares `{"python_sdk": "local"}` next to `{"cli": "local"}`
  in `plenora.surface_side_effects`. PR #44 notes that the document of the
  binary does not name the surface yet.
