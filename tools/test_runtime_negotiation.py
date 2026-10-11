"""Runtime Binding 2.0 RT-026 (decision 0015): the negotiation between 1.0
and 2.0 happens where the sender selects the destination. The vectors of
`vectors/runtime-negotiation-v1` state each decision, which the validator
derives from the rule; a vector cannot state another."""

import copy
import unittest
from unittest.mock import patch

import validate_specs as validator

ROOT = validator.ROOT
VECTORS = ROOT / "vectors/runtime-negotiation-v1"
V1, V2 = "plenora-runtime-binding-v1", "plenora-runtime-binding-v2"
REFUSE = {"decision": "refuse", "category": "unsupported", "phase": "validate",
          "remote_effect": "none", "retry": "never"}


def vector(name):
    return validator.load_json(VECTORS / name)


def interface(contract, version):
    return {"kind": "runtime", "contract": contract, "version": version}


class DecisionTests(unittest.TestCase):
    def decide(self, requires, downgrade, destination, kind="client", context=None):
        sender = {"kind": kind, "requires": requires, "accepts_downgrade": downgrade}
        if context is not None:
            sender["context"] = context
        return validator.runtime_negotiation_decision(sender, destination)

    def test_a_lost_context_is_refused_whatever_the_destination(self):
        """RT-027: a hop that finds the negotiation context lost refuses; the
        same bytes would otherwise be routed as a request of 1.0."""
        for requires in (V1, V2):
            for downgrade in (False, True):
                for destination in (interface(V1, 1), interface(V2, 2), None):
                    with self.subTest(requires=requires, downgrade=downgrade, destination=destination):
                        self.assertEqual(self.decide(requires, downgrade, destination, "transport", "lost"), REFUSE)
                        preserved = self.decide(requires, downgrade, destination, "transport", "preserved")
                        self.assertEqual(preserved, self.decide(requires, downgrade, destination))

    def test_the_cases_of_rt_026(self):
        cases = [
            (V1, False, interface(V1, 1), {"decision": "send", "governed_by": V1}),
            (V1, False, interface(V2, 2), {"decision": "send", "governed_by": V2}),
            (V2, False, interface(V2, 2), {"decision": "send", "governed_by": V2}),
            # No implicit downgrade.
            (V2, False, interface(V1, 1), REFUSE),
            (V2, True, interface(V1, 1), {"decision": "send", "governed_by": V1}),
            # Unreadable capability document, unknown contract, version that
            # is not the contract's.
            (V2, True, None, REFUSE),
            (V1, False, None, REFUSE),
            (V2, False, interface("plenora-runtime-binding-v3", 3), REFUSE),
            (V1, False, interface(V2, 1), REFUSE),
            (V1, False, interface(V1, 2), REFUSE),
        ]
        for requires, downgrade, destination, expected in cases:
            with self.subTest(requires=requires, downgrade=downgrade, destination=destination):
                self.assertEqual(self.decide(requires, downgrade, destination), expected)


class VectorTests(unittest.TestCase):
    def test_every_published_vector_agrees_with_the_rule(self):
        self.assertEqual(validator.validate_runtime_negotiation_vectors(), [])

    def test_the_vectors_cover_every_case_for_clients_and_transports(self):
        """Every combination of RT-026 and RT-027, for a client and for a
        transport: a set of vectors that only refuses, or only covers the
        client, does not pass."""
        found = set()
        for path in VECTORS.glob("*.json"):
            document = vector(path.name)
            sender, destination = document["sender"], document["destination"]["interface"]
            found.add((
                sender["kind"], sender["requires"], sender["accepts_downgrade"],
                None if destination is None else (destination["contract"], destination["version"]),
                sender.get("context", "preserved"), document["expect"]["decision"],
            ))
        required = set()
        for kind in ("client", "transport"):
            required |= {
                (kind, V2, False, (V2, 2), "preserved", "send"),
                (kind, V2, False, (V1, 1), "preserved", "refuse"),
                (kind, V2, True, (V1, 1), "preserved", "send"),
                (kind, V1, False, (V2, 2), "preserved", "send"),
                (kind, V1, False, (V1, 1), "preserved", "send"),
                (kind, V2, True, None, "preserved", "refuse"),
            }
        required |= {
            ("client", V1, False, (V2, 1), "preserved", "refuse"),
            ("transport", V2, False, (V1, 1), "lost", "refuse"),
            ("transport", V2, False, (V2, 2), "lost", "refuse"),
        }
        self.assertEqual(sorted(required - found, key=str), [])

    def test_a_wrong_decision_is_reported(self):
        original = validator.load_json

        def wrong(path):
            document = original(path)
            if path.parent.name == "runtime-negotiation-v1" and path.name == "client-2-0-to-server-1-0-refused.json":
                document = copy.deepcopy(document)
                document["expect"] = {"decision": "send", "governed_by": V1}
            return document

        with patch.object(validator, "load_json", wrong):
            errors = validator.validate_runtime_negotiation_vectors()
        self.assertEqual(len(errors), 1)
        self.assertIn("client-2-0-to-server-1-0-refused.json", errors[0])
        self.assertIn("RT-026", errors[0])

    def test_the_request_is_a_runtime_request_of_wire_version_1(self):
        original = validator.load_json
        for mutation in ("missing", "not a request", "wire version 2"):
            def changed(path, mutation=mutation):
                document = original(path)
                if path.parent.name == "runtime-negotiation-v1" and path.name == "client-1-0-to-server-2-0.json":
                    document = copy.deepcopy(document)
                    if mutation == "missing":
                        document["request"] = "../runtime-v1/absent-request.json"
                    elif mutation == "not a request":
                        document["request"] = "../runtime-v1/database-query-success.json"
                if mutation == "wire version 2" and path.name == "database-read-request.json":
                    document = copy.deepcopy(document)
                    document["metadata"]["plenora.capability.version"] = "2"
                return document

            with self.subTest(mutation), patch.object(validator, "load_json", changed):
                errors = [error for error in validator.validate_runtime_negotiation_vectors()
                          if "client-1-0-to-server-2-0.json" in error]
                self.assertEqual(len(errors), 1, errors)

    def test_the_gate_validates_their_schema(self):
        schemas = {name: validator.load_json(ROOT / "schemas" / name) for name in validator.EXPECTED_SCHEMAS}
        registry = validator.schema_registry(schemas)
        self.assertEqual(validator.validate_machine_documents(schemas, registry), [])
        bad = vector("client-2-0-to-server-2-0.json")
        bad["expect"] = {"decision": "send"}
        self.assertTrue(validator.instance_errors(
            schemas["runtime-negotiation-vector-v1.schema.json"], bad, registry))
        self.assertIn("runtime-negotiation-vector-v1.schema.json", validator.EXPECTED_SCHEMAS)


if __name__ == "__main__":
    unittest.main()
