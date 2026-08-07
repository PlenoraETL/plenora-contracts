# Error axes corpus v1

This campaign verifies the four error axes and the session axis from ICD rules
R9.15–R9.18 and the amended R9.7.

## Why it exists

Three contradictions were found inside the specification on 2026-08-07, all in
the same area, none detected by any existing gate:

1. **The wire vocabulary was never stated.** The ICD lists category and phase in
   PascalCase (`DataMapping`, `Read`) and effect and retry in snake_case
   (`rolled_back`, `never`), without saying which form travels. The
   `row-diagnostics-v1` oracles read the tables as wire values; all three
   components serialise with `rename_all = "snake_case"`. Run against a real
   component observation, that campaign would fail on two axes out of four.
2. **`quarantine` existed in one half of the specification.** It appears in
   `row-diagnostics-v1/cases.json` but not in the R9.7 table. Database Tools
   implemented the cases; IO Tools and Data Tools implemented the table.
3. **The representation of `after` was unspecified.** Two components send
   `delay_ms` as an integer, one keeps a `Duration` and has no serde derives.

None of them was noticed because component gates verify their own component,
and `check_contract.py` states in its own docstring that it verifies the
document rather than the components.

## What it checks

| Gate | Rule | What fails it |
|---|---|---|
| Wire form of every value of every axis | R9.15 | a value serialised differently from the manifest, a value emitted but not declared, a declared value not observed |
| Exhaustiveness by construction | R9.15 | `expected_count` disagreeing with the listed values — so a new value added without pinning its form cannot pass silently |
| Degradation | R9.16, R9.17 | an envelope that becomes unreadable because of one unknown value; a conservative reading that is not applied; a received value that is not preserved |
| Forbidden degradations | R9.17 | an unknown value read as `safe`, `none` or `committed` — the readings that authorise the riskiest action precisely when the information is missing |
| Relay without loss | R9.16 | a component that normalises, on forwarding, a value it did not understand |

The relay gate is the one no single component can satisfy on its own. It is the
reason this campaign lives here rather than in the three repositories.

## Cases

- `retry-quarantine-da-database-tools`: the real 2026-08-07 defect. Category
  `data_mapping`, phase `rollback`, effect `unknown` — a rollback with an
  uncertain outcome, which is when error handling has to be most dependable.
  Before R9.16 the whole envelope was lost, not just the axis.
- `retry-valore-inventato`, `remote-effect-inventato`, `categoria-inventata`,
  `fase-inventata`, `sessione-inventata`: values that exist in no version, so
  the degradation cannot depend on knowing `quarantine` in particular.
- `asse-sessione-assente`: the session axis missing altogether must read
  `reusable`, so an emitter that does not declare it stays conformant.
- `inoltro-di-quarantine` and `inoltro-di-un-valore-inventato-su-due-assi`: an
  envelope crossing two or three components must come out unchanged on the axes
  that were not understood.

`reference_observations` in `cases.json` are contract oracles. They are **not**
evidence that any component currently conforms. Component adapters must produce
their own observation and pass it to `judge_error_axes.py`.

## Judge and mutation gate

```text
python -m unittest conformance.tests.test_error_axes
```

The second half of `test_error_axes.py` is a mutation gate: it builds a
conformant observation, breaks it in one place at a time, and requires the judge
to notice. A judge that does not reject is not a gate — which is exactly how an
oracle that had never been compared against a real observation let three
contradictions through.
