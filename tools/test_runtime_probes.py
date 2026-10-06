"""Runtime rejection probes (RT-016 to RT-022, decision 0010).

The validator derives the expected rejection of every probe from the rules
and refuses a probe that disagrees with them, or that relies on behavior
Runtime Binding 1.0 does not decide. ERR-015 is checked on error vectors.
"""

import contextlib
import copy
import io
import json
import unittest
from unittest.mock import patch

import validate_specs as validator

ROOT = validator.ROOT
PROBES = ROOT / "vectors/runtime-probes-v1"


def probe(name):
    return json.loads((PROBES / name).read_text(encoding="utf-8"))


def errors_of(document):
    schemas = {
        path.name: validator.load_json(path)
        for path in sorted(validator.SCHEMA_DIR.glob("*.schema.json"))
    }
    registry = validator.schema_registry(schemas)
    structural = validator.instance_errors(
        schemas["runtime-probe-v1.schema.json"], document, registry
    )
    if structural:
        return structural
    operations = validator.operation_index(validator.load_catalogs())
    return validator.runtime_probe_errors(document, operations, schemas, registry)


def mutated(name, key, value):
    document = probe(name)
    document["mutation"] = {"set": {key: value}}
    return document


class RepositoryProbeTests(unittest.TestCase):
    def test_every_probe_agrees_with_the_rules(self):
        for path in sorted(PROBES.glob("*.json")):
            self.assertEqual(errors_of(probe(path.name)), [], path.name)

    def test_every_rule_and_category_is_probed(self):
        documents = [probe(path.name) for path in PROBES.glob("*.json")]
        self.assertEqual(
            {document["rule"] for document in documents},
            {"RT-017", "RT-018", "RT-021", "RT-022"},
        )
        self.assertEqual(
            {document["expected"]["error"]["category"] for document in documents},
            {"protocol", "unsupported", "timeout"},
        )


class ProbeClassTests(unittest.TestCase):
    def test_malformed_value_is_protocol_not_unsupported(self):
        document = probe("io-read-binding-version-leading-zero.json")
        document["expected"]["error"]["category"] = "unsupported"
        self.assertTrue(errors_of(document))

    def test_well_formed_unsupported_value_is_not_protocol(self):
        document = probe("io-read-binding-version-unsupported.json")
        document["expected"]["error"]["category"] = "protocol"
        self.assertTrue(errors_of(document))

    def test_rejection_is_never_retried(self):
        document = probe("io-read-deadline-expired.json")
        document["expected"]["error"]["retry"] = {"kind": "safe"}
        self.assertTrue(errors_of(document))

    def test_malformed_version_is_not_reflected_or_normalized(self):
        for reflected in ("01", "1"):
            document = probe("io-read-operation-version-leading-zero.json")
            document["expected"]["metadata"]["plenora.operation.version"] = reflected
            self.assertTrue(errors_of(document), reflected)

    def test_well_formed_unknown_version_is_reflected(self):
        document = probe("io-read-operation-version-unknown.json")
        del document["expected"]["metadata"]["plenora.operation.version"]
        self.assertTrue(errors_of(document))

    def test_non_canonical_correlation_is_omitted(self):
        document = probe("database-read-correlation-uppercase.json")
        document["expected"]["metadata"]["plenora.trace.correlation_id"] = (
            "018f3d84-7b2c-7f00-8000-000000000001"
        )
        self.assertTrue(errors_of(document))

    def test_wrong_rule_is_rejected(self):
        document = probe("io-read-deadline-offset.json")
        document["rule"] = "RT-017"
        self.assertTrue(errors_of(document))

    def test_undecided_deadline_spellings_are_refused(self):
        for value in (
            "2020-01-01T00:00:00+00:00", "2020-01-01t00:00:00z",
            "2020-01-01 00:00:00Z", "2020-01-01T00:00:00.1234567890Z",
        ):
            errors = errors_of(mutated("io-read-deadline-expired.json", "plenora.execution.deadline", value))
            self.assertTrue(any("not decided" in error for error in errors), value)

    def test_unreserved_key_is_refused(self):
        errors = errors_of(mutated("io-read-deadline-expired.json", "plenora.idempotency_key", "k"))
        self.assertTrue(any("not reserved" in error for error in errors))

    def test_mutation_that_is_not_a_rejection_is_refused(self):
        errors = errors_of(mutated(
            "io-read-deadline-expired.json", "plenora.execution.deadline", "2031-01-01T00:00:00Z"
        ))
        self.assertTrue(any("not rejected" in error for error in errors))

    def test_removing_an_optional_key_is_refused(self):
        document = probe("io-read-deadline-expired.json")
        document["mutation"] = {"remove": "plenora.execution.deadline"}
        self.assertTrue(errors_of(document))

    def test_two_mutations_are_refused_by_the_schema(self):
        document = probe("io-read-deadline-expired.json")
        document["mutation"] = {"set": {
            "plenora.execution.deadline": "2020-01-01T00:00:00Z",
            "plenora.operation.version": "01",
        }}
        self.assertTrue(errors_of(document))

    def test_unknown_base_is_refused(self):
        document = probe("io-read-deadline-expired.json")
        document["base"] = "io-read-success.json"
        self.assertTrue(errors_of(document))


class CleanupAfterPublicationTests(unittest.TestCase):
    def test_retrying_a_cleanup_after_publication_is_rejected(self):
        original = validator.load_json

        def loader(path):
            document = original(path)
            if str(path).replace("\\", "/").endswith("storage-put-cleanup-local-error.json"):
                document = copy.deepcopy(document)
                document["payload"]["retry"] = {"kind": "safe"}
            return document

        stderr = io.StringIO()
        with patch.object(validator, "load_json", loader), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            self.assertNotEqual(validator.main(), 0)
        self.assertIn("ERR-015", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
