# Decision 0002: One machine document on stdout

Status: accepted for CLI protocol v2

## Context

Current Plenora CLIs agree on structured JSON errors but disagree on the output
stream. Some write errors to stdout and leave stderr empty; another writes the
error document to stderr. Exit-code mappings also differ.

An orchestrator should not need component-specific stream handling to recover a
typed error.

## Decision

In JSON mode, every invocation writes exactly one JSON document to stdout.
This applies to both success and failure. Stderr is empty.

The process exit code remains non-zero on failure and follows the projection in
CLI protocol v2. The JSON error category is authoritative; the exit code is a
coarser convenience for process supervisors.

Human-readable output is permitted only when explicitly requested. Human mode
is outside the machine stream guarantee.

## Consequences

- Existing CLIs that emit errors on stderr require a breaking migration to
  protocol v2.
- Logs and progress cannot be mixed with the JSON document.
- A process supervisor can parse stdout once, regardless of outcome.
