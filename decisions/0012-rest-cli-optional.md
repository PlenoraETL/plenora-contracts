# 0012: The rest-tools CLI as an optional surface

Status: accepted

Date: 2026-10-06

## Context

The rest-tools profile said "CLI: not required", the catalog selected the CLI
as `not_applicable`, and the CLI binding map had an empty rest-tools section.
rest-tools now ships a `plenora-rest` command that follows CLI 2.0 (PR #25 of
plenora-rest-tools). Without a binding its spellings stay component-owned and
not normative (Surface Bindings 1.0 §6), and a capability document that lists
`cli` for a REST operation contradicts the catalog.

## Decision

- The catalog selects the CLI as `conditional` and adds `cli` to the surfaces
  of the five operations. Both are additions COMPATIBILITY.md admits: a
  `not_applicable` target may become decided, and an operation may gain a
  surface.
- `bindings/cli-v1.json` names the artifact `plenora-rest`, the three
  discovery entrypoints and `<operation> --input REQUEST.json --format json`
  for each operation.
- The profile makes the CLI optional: an artifact with the command follows
  CLI 2.0 and the binding map; an artifact without it omits `cli` from its
  capability document and remains conforming.
- The validator compared the surfaces of a REST capability document with the
  catalog's for equality. With a conditional surface that would reject every
  artifact without the command, so a document now lists every required target
  surface, may omit a conditional one and may not add one the catalog does not
  select.

## Change statement

- **Consumers affected:** callers that want a process-level REST surface.
- **Before:** no shared CLI for rest-tools.
- **After:** an optional CLI with canonical spellings.
- **Compatible:** yes; Rust, Python and runtime surfaces are unchanged, and an
  artifact without the command is still conforming.
- **Schemas, examples and profiles:** catalog and CLI binding map extended;
  profile and profile index updated; no schema or vector changes.
- **Adoption impact:** rest-tools may declare `plenora-cli-v2` for its command
  after moving its pin.
