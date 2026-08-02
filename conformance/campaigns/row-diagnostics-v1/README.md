# Row-scoped rejection diagnostics corpus v1

This campaign verifies `plenora-row-diagnostics-v1` from ICD rules R9.9–R9.14 and R14.6.

## Cases

- `read-shapefile-invalid-geometry`: 128 real Shapefile records, with invalid geometry at source indices 17, 89, and 113; configured DBF key `ID_PART`; an explicit case policy permits cleartext emission encoded as an exact decimal string; example limit 2.
- `read-invalid-date`: 1,025 CSV rows, with invalid dates at indices 4 and 1,004 so the second defect crosses a typical batch boundary; no configured key.
- `write-constraint-confirmed-rollback`: 5,200 CSV source rows; row 4,999 violates `area_m2 >= 0`; rollback is confirmed.
- `write-constraint-rollback-outcome-unknown`: the same row-specific rejection with lost rollback acknowledgement; the known cause is preserved while the remote row effects remain explicitly unknown.

`reference_observations` in `cases.json` are contract oracles. They are **not** evidence that any component currently conforms. Component adapters must execute the operation, retain their observed envelope, and pass that observation to `judge_row_diagnostics.py`.

## Generate fixtures

```text
python conformance/campaigns/row-diagnostics-v1/generate_fixtures.py --out <directory>
```

Generation uses only the Python standard library and is byte-reproducible on the same runtime and platform. Generated fixtures are intentionally not committed; tests generate them in temporary directories and compare SHA-256 digests across two runs. Cross-platform byte identity is not claimed because the Shapefile payload uses floating-point trigonometry.

Database adapters convert `write-constraint.csv` to the component's native `RecordBatch` input without changing source order. Provider-specific fixture setup must enforce the logical constraint `area_m2 >= 0` and must not infer committed row identities when rollback or commit acknowledgement is unavailable.

## Judge and mutation gate

```text
python -m unittest \
  conformance.tests.test_row_diagnostics \
  conformance.tests.test_row_diagnostics_corpus
```

The mutation gate separates oracle mutations from validator mutations. A source-index mutation must fail by exact oracle mismatch. Cause, count, total, diagnostic-state partition, example-index uniqueness, read/write field scope, and fabricated values in unknown buckets are mutated in both observation and oracle, so exact equality still holds and only schema/semantic validation can reject them. Every mutation must produce campaign status `fail` for the expected reason.
