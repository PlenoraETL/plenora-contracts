# Plenora Typed Error Contract 1.0

Status: normative

Contract identifier: `plenora-error-v1`

The machine shape is defined by the
[error v1 schema](../../schemas/error-v1.schema.json).

## 1. Applicability

Every failure crossing a public Plenora boundary MUST expose these four
independent axes:

- `category`: what failed;
- `phase`: when it failed;
- `remote_effect`: what is known about externally visible effects;
- `retry`: which retry behavior is permitted.

Consumers MUST make decisions from typed fields, never by parsing `message`.

## 2. Category

**ERR-001** — `category` MUST use the most precise value admitted by the
schema. Provider or dependency exception names are not public categories.

**ERR-002** — Unsupported operations, versions or providers MUST fail with
`unsupported` or a more precise validation category. They MUST NOT be silently
ignored or emulated with different semantics.

## 3. Phase

**ERR-003** — `phase` identifies the last externally meaningful phase known to
have started. It does not expose private call stacks.

## 4. Remote effect

**ERR-004** — `remote_effect` MUST be conservative. When the component cannot
prove whether a remote mutation occurred, it MUST report `unknown`.

**ERR-005** — Timeout and cancellation MUST NOT be treated as proof of rollback.

## 5. Retry

**ERR-006** — `remote_effect: unknown` MUST NOT permit automatic safe retry.
It requires `never`, `quarantine` or `requires_recovery`.

**ERR-007** — `retry.kind: after` MUST include `delay_ms`. Other retry kinds
MUST NOT include it.

**ERR-008** — `requires_idempotency_key` is valid only when the public
operation advertises idempotency-key support.

## 6. Message and details

**ERR-009** — `message` is diagnostic text for people. It MUST be bounded and
redacted.

**ERR-010** — Public error data MUST NOT contain credentials, authorization
headers, connection strings, bound SQL, source rows, unbounded payloads or local
secret paths.

`code`, `provider`, `execution_id` and `details` MAY provide structured
context. Their absence MUST NOT change the meaning of the four common axes.

## 7. Surface projection

The CLI projects categories to exit codes as defined by CLI 2.0. Python exposes
the axes on `PlenoraError`. Rust and runtime bindings MAY use native tagged
types or serialized objects, but MUST preserve all four axes and their meaning.
