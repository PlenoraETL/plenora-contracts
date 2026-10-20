# Conformance vectors

The published vector files are immutable. New cases are additive.

Decision [0022](../decisions/0022-field-id-across-operations-and-the-mixed-form.md)
adds these cases:

| Case | Vector | Validator |
|---|---|---|
| Rule 1: preserve an incoming ID across database write/read | [round trip](interop-v1/handoff-field-id-round-trip.json) | `tools/interop_vectors.py` |
| Rule 2: assign an ID to a field written without one | [store assignment](interop-assignment-v1/handoff-store-assigned-field-id.json) | `tools/interop_vectors.py` |
| Rule 4: accept `mixed` without a type list | [mixed](arrow-v1/mixed-without-types.json) | `tools/validate_specs.py` |
| Vocabulary section 3: reject an empty type list | [empty types](arrow-v1/invalid-mixed-empty-types.json) | `tools/validate_specs.py` |

Run `python tools/validate_specs.py` for the repository gate and
`python -m unittest discover -s tools` for the validator tests.

The additive [assignment schema](../schemas/interop-assignment-vector-v1.schema.json)
reuses the interop v1 handoff structures. `assigned_field_ids` lists zero-based
field positions whose input and expected metadata omit `plenora.field_id`.
The output comparison requires a canonical decimal ID at each position and
uniqueness within the output schema; all other content is compared exactly.
It does not prescribe a particular assigned value. The reference evaluator
uses `assign_field_ids` to produce a sample result; a component harness passes
its actual output to `interop_vectors.output_errors(vector, input, actual)`.
In this new format, the assignment predicate allows any canonical decimal
that is unique in the schema. The exact comparison and smallest-free-ID
expectation of published interop v1 vectors remain unchanged.
The declared positions must have no incoming ID, so this allowance cannot
mask replacement of an existing identity.

The round trip uses a non-positional incoming ID to distinguish preservation
from reassignment. Assignment is exercised through a writer that supplies
no ID, one of the store-born cases in rule 2. These fixtures check the
reference rules locally; running the chain against a component remains the
component harness's responsibility. Error messages contain structural
positions and fixed text, never fixture data (decision 0021).
