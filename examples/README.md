# Examples

Files under `valid` must satisfy their registered structural and semantic
checks. Files under `invalid` are deliberate counterexamples and must fail the
specific check they exercise.

The executable inventory is maintained in
[`tools/validate_specs.py`](../tools/validate_specs.py). `CASES` registers
structural cases; the named semantic registries cover public capabilities,
adoption manifests, error bounds, REST boundaries and plan budgets. The
validator compares their union with every JSON example on disk and rejects
unregistered files, missing files and conflicting classifications.

A semantic counterexample must satisfy its structural schema before exercising
its rejection. For example, a duplicated operation identity with differing
availability is structurally valid but violates CAP-005; a plan whose domain
budget is below its governed budget violates PLAN-011. These examples prove
that schema validation alone is not conformance.

An example may be registered for several different checks, such as schema
validation and error bounds. The same registration cannot be repeated.
Regression tests for the inventory and semantic checks run in CI with:

```sh
python -m unittest discover -s tools -p 'test_*.py'
python tools/validate_specs.py
```

Examples use fictional artifact versions and revisions. They are not component
status records. REST runtime examples cover shared security and interoperability
invariants rather than the complete component-owned REST input schema.
