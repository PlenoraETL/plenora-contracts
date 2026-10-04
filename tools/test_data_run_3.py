"""Regression probes for `data.run` 3, the runtime representation of a data
plan with named outputs (profile data-tools v2, DT-RUN-001..DT-RUN-008).

Each probe breaks one document in memory and expects the gate to notice.
"""

import contextlib
import copy
import io
import unittest
from unittest.mock import patch

import validate_specs as validator

VECTORS = validator.ROOT / "vectors/runtime-v1"


class DataRun3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = validator.load_catalogs()[validator.DATA_COMPONENT]
        cls.schemas = {
            name: validator.load_json(validator.ROOT / "schemas" / name)
            for name in validator.EXPECTED_SCHEMAS
        }
        cls.registry = validator.schema_registry(cls.schemas)
        cls.request = validator.load_json(VECTORS / "data-run-request-v3.json")
        cls.success = validator.load_json(VECTORS / "data-run-success-v3.json")
        cls.error = validator.load_json(VECTORS / "data-run-partial-error-v3.json")

    def run3(self, catalog):
        return next(
            item for item in catalog["operations"]
            if item["id"] == "data.run" and item["version"] == 3
        )

    def vector_errors(self, vector):
        return validator.data_run_3_vector_errors(vector, self.schemas, self.registry)

    def test_unchanged_documents_conform(self):
        self.assertEqual(validator.data_catalog_errors(self.catalog, 2), [])
        for vector in (self.request, self.success, self.error):
            self.assertEqual(self.vector_errors(vector), [])

    def test_catalog_entry_is_pinned(self):
        cases = {
            "local side effect": lambda op: op.update(side_effect="local"),
            "on the CLI": lambda op: op["surfaces"].append("cli"),
            "required": lambda op: op.update(requirement="required"),
            "arrow payload": lambda op: op["output"]["content_types"].append(
                "application/vnd.apache.arrow.stream"
            ),
            "another registry": lambda op: op["attributes"].update(
                kernel_registry="plenora-data-kernel-catalog-v1"
            ),
            "parquet as interchange": lambda op: op["attributes"]["artifact_content_types"][
                "sink"
            ].append("application/vnd.apache.parquet"),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                catalog = copy.deepcopy(self.catalog)
                mutate(self.run3(catalog))
                self.assertTrue(validator.data_catalog_errors(catalog, 2))
        missing = copy.deepcopy(self.catalog)
        missing["operations"].remove(self.run3(missing))
        self.assertTrue(validator.data_catalog_errors(missing, 2))

    def test_request_is_checked(self):
        cases = {
            "missing source": lambda p: p["inputs"].clear(),
            "extra source": lambda p: p["inputs"].update(
                other={"reference": "artifact://input/x", "content_type": "application/vnd.apache.arrow.file"}
            ),
            "extra sink": lambda p: p["outputs"].update(
                other={"reference": "artifact://output/x", "content_type": "application/vnd.apache.arrow.file", "overwrite": False}
            ),
            "file reference": lambda p: p["inputs"]["parcels"].update(reference="file:///tmp/parcels.parquet"),
            "dot-dot reference": lambda p: p["inputs"]["parcels"].update(reference="artifact://input/../secret"),
            "drive path": lambda p: p["inputs"]["parcels"].update(reference="C:\\data\\parcels.parquet"),
            "sink without overwrite": lambda p: p["outputs"]["large"].pop("overwrite"),
            "unknown content type": lambda p: p["outputs"]["large"].update(content_type="text/csv"),
            "bad digest": lambda p: p["inputs"]["parcels"]["expected"].update(sha256="ABC"),
            "empty expectation": lambda p: p["inputs"]["parcels"].update(expected={}),
            "unknown field": lambda p: p.update(path="/tmp"),
            "invalid plan": lambda p: p["plan"].update(outputs=["nowhere"]),
            "unknown kernel": lambda p: p["plan"]["steps"][0].update(op="table.filter_rows"),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                vector = copy.deepcopy(self.request)
                mutate(vector["payload"])
                self.assertTrue(self.vector_errors(vector))

    def test_two_sinks_cannot_share_a_reference(self):
        vector = copy.deepcopy(self.request)
        payload = vector["payload"]
        payload["plan"]["outputs"].append("parcels_copy")
        payload["plan"]["steps"].append(
            {"out": "parcels_copy", "op": "table.select_columns", "in": ["parcels"], "config": {"columns": ["area"]}}
        )
        payload["outputs"]["parcels_copy"] = dict(payload["outputs"]["large"])
        errors = self.vector_errors(vector)
        self.assertTrue(any("share" in error for error in errors), errors)

    def test_result_is_checked(self):
        cases = {
            "reference with newline": lambda p: p["outputs"][0].update(reference="artifact://output/x\n"),
            "dot-dot reference": lambda p: p["outputs"][0].update(reference="artifact://output/%2e%2e/x"),
            "relative reference": lambda p: p["outputs"][0].update(reference="tmp:./large.arrow"),
            "digest with newline": lambda p: p["outputs"][0]["artifact"].update(
                sha256=p["outputs"][0]["artifact"]["sha256"] + "\n"
            ),
            "repeated output": lambda p: p["outputs"].append(copy.deepcopy(p["outputs"][0])),
            "no digest": lambda p: p["outputs"][0]["artifact"].pop("sha256"),
            "negative size": lambda p: p["outputs"][0]["artifact"].update(size=-1),
            "local reference": lambda p: p["outputs"][0].update(reference="file:///tmp/large.arrow"),
            "no outputs": lambda p: p.update(outputs=[]),
            "path leaked": lambda p: p["outputs"][0].update(path="/tmp/large.arrow"),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                vector = copy.deepcopy(self.success)
                mutate(vector["payload"])
                self.assertTrue(self.vector_errors(vector))

    def test_partial_and_unknown_publication_forbid_retry(self):
        for effect, retry in (("partial", "safe"), ("unknown", "never")):
            with self.subTest(effect=effect):
                vector = copy.deepcopy(self.error)
                vector["payload"]["remote_effect"] = effect
                vector["payload"]["retry"] = {"kind": retry}
                self.assertTrue(self.vector_errors(vector))

    def test_gate_requires_every_vector_kind(self):
        original = validator.load_json

        def loader(path):
            document = original(path)
            if str(path).replace("\\", "/").endswith("vectors/runtime-v1/data-run-success-v3.json"):
                document = copy.deepcopy(document)
                document["metadata"]["plenora.operation.version"] = "1"
                document["metadata"]["plenora.output.contract"] = "plenora-data-execution-result-v1"
                document["content_type"] = "application/vnd.apache.arrow.stream"
                document["payload"] = {}
            return document

        stderr = io.StringIO()
        with patch.object(validator, "load_json", loader), contextlib.redirect_stdout(
            io.StringIO()
        ), contextlib.redirect_stderr(stderr):
            self.assertNotEqual(validator.main(), 0)
        self.assertIn("data.run 3 runtime vector coverage", stderr.getvalue())


    def test_bounded_materialization_and_controls_are_pinned(self):
        cases = {
            "materialization false": lambda op: op["attributes"].update(bounded_materialization=False),
            "materialization missing": lambda op: op["attributes"].pop("bounded_materialization"),
            "idempotency accepted": lambda op: op["controls"].update(idempotency_key=True),
            "no deadline": lambda op: op["controls"].update(deadline=False),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                catalog = copy.deepcopy(self.catalog)
                mutate(self.run3(catalog))
                self.assertTrue(validator.data_catalog_errors(catalog, 2))

    def test_catalog_order_does_not_matter(self):
        catalog = copy.deepcopy(self.catalog)
        catalog["operations"].reverse()
        self.assertEqual(validator.data_catalog_errors(catalog, 2), [])

    def test_every_version_of_an_operation_is_checked(self):
        """Two versions of one operation may coexist (COMPATIBILITY.md); each
        is checked, in any order, and none hides the other."""
        def with_version_2(component, operation_id, mutate):
            catalogs = copy.deepcopy(validator.load_catalogs())
            operations = catalogs[component]["operations"]
            extra = copy.deepcopy(next(item for item in operations if item["id"] == operation_id))
            extra["version"] = 2
            mutate(extra)
            operations.insert(0, extra)
            return validator.validate_catalog_semantics(catalogs)

        unchanged = lambda op: None
        self.assertEqual(with_version_2(validator.REST_COMPONENT, "rest.download", unchanged), [])
        self.assertEqual(with_version_2(validator.DATABASE_COMPONENT, "database.query", unchanged), [])
        self.assertEqual(with_version_2(validator.STORAGE_COMPONENT, "storage.get", unchanged), [])
        cases = [
            (validator.REST_COMPONENT, "rest.download", lambda op: op.update(side_effect="local"), "conservative remote"),
            (validator.REST_COMPONENT, "rest.upload", lambda op: op["controls"].update(idempotency_key=False), "idempotency keys"),
            (validator.DATABASE_COMPONENT, "database.query", lambda op: op.update(side_effect="remote"), "read-only"),
            (validator.DATABASE_COMPONENT, "database.execute", lambda op: op.update(side_effect="local"), "remote side effects"),
            (validator.STORAGE_COMPONENT, "storage.get", lambda op: op.update(side_effect="none"), "conservative remote"),
            (validator.STORAGE_COMPONENT, "storage.get", lambda op: op["attributes"].update(artifact_role="source"), "artifact sink"),
            (validator.STORAGE_COMPONENT, "storage.put", lambda op: op["attributes"].update(publication_policy="optional"), "publication policy"),
            (validator.STORAGE_COMPONENT, "storage.list", lambda op: op.update(side_effect="remote"), "side-effect free"),
        ]
        for component, operation_id, mutate, fragment in cases:
            with self.subTest(operation=operation_id):
                errors = with_version_2(component, operation_id, mutate)
                self.assertTrue(any(fragment in error for error in errors), errors)

    def test_every_sdk_binding_version_is_checked(self):
        original = validator.load_json

        def loader(path):
            document = original(path)
            if path.name == "python-sdk-v1.json":
                document = copy.deepcopy(document)
                section = next(
                    item for item in document["components"]
                    if item["component"] == validator.DATABASE_COMPONENT
                )
                extra = copy.deepcopy(next(
                    item for item in section["bindings"] if item["operation"] == "database.query"
                ))
                extra["version"] = 2
                extra["entrypoints"] = ["Session.insert", "AsyncSession.insert"]
                section["bindings"].insert(0, extra)
            return document

        with patch.object(validator, "load_json", loader):
            errors = validator.validate_bindings(validator.load_catalogs())
        self.assertTrue(any("read-only" in error for error in errors), errors)

    def test_reference_spellings_that_are_paths_are_rejected(self):
        for reference in (
            "artifact://input/x\n",
            "artifact://input/%2e%2e/secret",
            "tmp:./private/data.arrow",
            "tmp:../data.arrow",
            "artifact://input/a b",
        ):
            with self.subTest(reference=reference):
                vector = copy.deepcopy(self.request)
                vector["payload"]["inputs"]["parcels"]["reference"] = reference
                self.assertTrue(self.vector_errors(vector))
        vector = copy.deepcopy(self.request)
        vector["payload"]["inputs"]["parcels"]["expected"]["sha256"] += "\n"
        self.assertTrue(self.vector_errors(vector))

    def test_request_text_follows_the_plan_rules(self):
        text = (VECTORS / "data-run-request-v3.json").read_text(encoding="utf-8")
        self.assertEqual(validator.data_run_3_text_errors(text), [])
        self.assertTrue(validator.data_run_3_text_errors(text.replace('"value": 1000', '"value": 18446744073709551616')))
        self.assertTrue(validator.data_run_3_text_errors(text.replace('"value": 1000', '"value": 1000, "value": 2')))
        self.assertTrue(validator.data_run_3_text_errors(text.replace('"value": 1000', '"value": 0.1000000000000000055511151231257827')))

    def test_manifest_matches_its_request(self):
        self.assertEqual(validator.data_run_3_manifest_errors([self.request, self.success]), [])
        cases = {
            "renamed output": lambda p: p["outputs"][0].update(name="other"),
            "other sink": lambda p: p["outputs"][0].update(reference="artifact://output/other"),
            "other content type": lambda p: p["outputs"][0]["artifact"].update(content_type="application/vnd.apache.arrow.file"),
            "no steps": lambda p: p.update(steps=[]),
            "other step": lambda p: p["steps"][0].update(op="table.sort"),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                success = copy.deepcopy(self.success)
                mutate(success["payload"])
                self.assertTrue(validator.data_run_3_manifest_errors([self.request, success]))
        orphan = copy.deepcopy(self.success)
        orphan["metadata"]["plenora.trace.correlation_id"] = "018f3d84-7b2c-7f00-8000-0000000000ff"
        self.assertTrue(validator.data_run_3_manifest_errors([self.request, orphan]))

    def location_errors(self, mutate, request=None):
        vector = copy.deepcopy(self.error)
        mutate(vector["payload"])
        return validator.data_run_3_error_location_errors([request or self.request, vector])

    def test_errors_carry_no_location(self):
        for message in (
            "Could not write C:\\data\\out.arrow.",
            "Could not write /secret.",
            "Could not write path:/secret.",
            "Could not write relative/private.arrow.",
            "Publication failed for `artifact://private/output`.",
            "Could not write path:/secret:https://example.org/help.",
            "Could not write artifacthttps://example.org/help.",
            "See https://example.org/help?path=/secret.",
            # Conservative: harmless text with the marks is rejected too.
            "Rows and/or columns exceed the budget.",
            "/ is not a supported arithmetic operator.",
        ):
            with self.subTest(message=message):
                self.assertTrue(self.location_errors(lambda p, m=message: p.update(message=m)))
        for details in (
            {"path": "/tmp/private.arrow"},
            {"/tmp/private.arrow": True},
            {"path": "private"},
            {"output": "not-a-plan-name"},
            {"output": "large", "reason": "x"},
            {"output": []},
            {"output": {}},
            {"output": None},
        ):
            self.assertTrue(self.location_errors(lambda p, d=details: p.update(details=d)))
        self.assertEqual(self.location_errors(lambda p: p.update(details={"output": "large"})), [])
        self.assertEqual(self.location_errors(
            lambda p: p.update(message="The sink rejected the publication.")), [])

    def test_plan_names_may_appear_in_errors(self):
        request = copy.deepcopy(self.request)
        payload = request["payload"]
        payload["plan"]["outputs"] = ["/tmp/x"]
        payload["plan"]["steps"][0]["out"] = "/tmp/x"
        payload["outputs"] = {"/tmp/x": payload["outputs"].pop("large")}
        self.assertEqual(self.vector_errors(request), [])
        named = lambda p: p.update(details={"output": "/tmp/x"}, message="Output /tmp/x was not published.")
        self.assertEqual(self.location_errors(named, request), [])
        # The same spelling is a location for a request without that name.
        self.assertTrue(self.location_errors(named))
        # A name with spaces and separators stays whole; a path beside it, or a
        # name occurring only inside a longer path, does not.
        spaced = copy.deepcopy(self.request)
        payload = spaced["payload"]
        payload["plan"]["outputs"] = ["/tmp/x y`z"]
        payload["plan"]["steps"][0]["out"] = "/tmp/x y`z"
        payload["outputs"] = {"/tmp/x y`z": payload["outputs"].pop("large")}
        self.assertEqual(self.vector_errors(spaced), [])
        self.assertEqual(self.location_errors(
            lambda p: p.update(message="Output /tmp/x y`z was not published."), spaced), [])
        self.assertTrue(self.location_errors(
            lambda p: p.update(message="Output /tmp/x y`z was not published to /secret."), spaced))
        # Two names whose removal one after the other would create a boundary
        # (`/tmp/private[` is not delimited in the original text).
        for first, second in (
            ("/tmp/private[", "secretlonglonglong]"),
            ("\\\\srv\\share[", "secretlonglonglong]"),
            ("https://a/[", "secretlonglonglong]"),
        ):
            with self.subTest(first=first):
                self.assertTrue(validator.contains_location(
                    f"Could not write {first}secretlonglonglong].",
                    frozenset({first, second}),
                ))
        self.assertFalse(validator.contains_location(
            "Inputs /tmp/a and /tmp/a b, output /tmp/.* failed.",
            frozenset({"/tmp/a", "/tmp/a b", "/tmp/.*"}),
        ))
        self.assertTrue(validator.contains_location(
            "Output /tmp/a b/c failed.", frozenset({"/tmp/a b", "b/c"}),
        ))
        # Locations without a mark.
        for text in ("Could not write C:private.arrow.", "Could not write private.arrow."):
            with self.subTest(text=text):
                self.assertTrue(validator.contains_location(text))
        # Overlapping occurrences of one name are all exempt.
        self.assertFalse(validator.contains_location("/a /a /a", frozenset({"/a /a"})))
        # Marks without a slash, anywhere in what the names leave.
        for text in ("/a file:secret.arrow", "/a ..", "/a FILE:secret", "x /a ..\\y"):
            with self.subTest(text=text):
                self.assertTrue(validator.contains_location(text, frozenset({"/a"})))
        prefix = copy.deepcopy(self.request)
        payload = prefix["payload"]
        payload["plan"]["outputs"] = ["/tmp/private"]
        payload["plan"]["steps"][0]["out"] = "/tmp/private"
        payload["outputs"] = {"/tmp/private": payload["outputs"].pop("large")}
        self.assertTrue(self.location_errors(
            lambda p: p.update(message="Could not write /tmp/private.arrow."), prefix))
        self.assertEqual(self.location_errors(
            lambda p: p.update(message="Output /tmp/private, not published."), prefix), [])

    def gate_errors(self, name, mutate=None, text=None):
        """The whole gate with one vector changed, as a document or as text."""
        original_json = validator.load_json
        original_text = validator.read_text

        def loader(path):
            document = original_json(path)
            if mutate is not None and path.name == name:
                document = copy.deepcopy(document)
                mutate(document)
            return document

        def reader(path):
            content = original_text(path)
            return text(content) if text is not None and path.name == name else content

        stderr = io.StringIO()
        with patch.object(validator, "load_json", loader), patch.object(
            validator, "read_text", reader
        ), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            self.assertNotEqual(validator.main(), 0)
        return stderr.getvalue()

    def test_gate_checks_request_text_manifest_and_coverage(self):
        self.assertIn("DPLAN-003", self.gate_errors(
            "data-run-request-v3.json",
            text=lambda content: content.replace('"value": 1000', '"value": 18446744073709551616'),
        ))
        self.assertIn("DPLAN-002", self.gate_errors(
            "data-run-request-v3.json",
            text=lambda content: content.replace('"value": 1000', '"value": 1000, "value": 2'),
        ))
        self.assertIn("manifest differs", self.gate_errors(
            "data-run-success-v3.json",
            mutate=lambda document: document["payload"]["outputs"][0].update(name="other"),
        ))
        self.assertIn("sha256", self.gate_errors(
            "data-run-success-v3.json",
            mutate=lambda document: document["payload"]["outputs"][0]["artifact"].pop("sha256"),
        ))
        for message in ("Could not write /secret.", "See https://example.org/help,/secret.", "Could not write private.arrow."):
            self.assertIn("DT-RUN-008", self.gate_errors(
                "data-run-partial-error-v3.json",
                mutate=lambda document, m=message: document["payload"].update(message=m),
            ))
        # An unhashable detail is a violation, not a crash of the gate.
        self.assertIn("DT-RUN-008", self.gate_errors(
            "data-run-partial-error-v3.json",
            mutate=lambda document: document["payload"].update(details={"output": []}),
        ))
        self.assertIn("error:unknown", self.gate_errors(
            "data-run-unknown-error-v3.json",
            mutate=lambda document: document["payload"].update(
                remote_effect="partial", retry={"kind": "never"}
            ),
        ))

    def test_gate_rejects_unsupported_idempotency(self):
        original = validator.load_json

        def with_key(path):
            document = original(path)
            if str(path).replace("\\", "/").endswith("vectors/runtime-v1/data-run-request-v3.json"):
                document = copy.deepcopy(document)
                document["metadata"]["plenora.execution.idempotency_key"] = "key-1"
            return document

        def with_retry(path):
            document = original(path)
            if str(path).replace("\\", "/").endswith("vectors/runtime-v1/data-run-partial-error-v3.json"):
                document = copy.deepcopy(document)
                document["payload"]["remote_effect"] = "none"
                document["payload"]["retry"] = {"kind": "requires_idempotency_key"}
            return document

        for loader, fragment in ((with_key, "idempotency key (RT-006)"), (with_retry, "(ERR-008)")):
            stderr = io.StringIO()
            with patch.object(validator, "load_json", loader), contextlib.redirect_stdout(
                io.StringIO()
            ), contextlib.redirect_stderr(stderr):
                self.assertNotEqual(validator.main(), 0)
            self.assertIn(fragment, stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
