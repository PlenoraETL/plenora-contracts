"""Runtime Binding 2.0 RT-026 and RT-027 (decision 0015): the negotiation
between 1.0 and 2.0 is decided where a hop selects the destination, with
the negotiation context that the ingress of a new request fixes and every
forwarding carries. The vectors of `vectors/runtime-negotiation-v1` are
sequences of hops; the validator derives the decision from the sequence,
and a vector cannot state another."""

import copy
import unittest
from unittest.mock import patch

import validate_specs as validator

ROOT = validator.ROOT
VECTORS = ROOT / "vectors/runtime-negotiation-v1"
V1, V2 = "plenora-runtime-binding-v1", "plenora-runtime-binding-v2"


def vector(name):
    return validator.load_json(VECTORS / name)


def context(requires, downgrade=False):
    return {"requires": requires, "accepts_downgrade": downgrade}


def interface(contract, version):
    return {"kind": "runtime", "contract": contract, "version": version}


def hop(source, receives, forwards=None, record="readable", carries=True):
    return {"from": source, "record": record, "carries": carries, "receives": receives, "forwards": forwards}


def refuse(at):
    return {"decision": "refuse", "at_hop": at, "category": "unsupported", "phase": "validate",
            "remote_effect": "none", "retry": "never"}


def derive(hops, destination, minimum=None):
    return validator.runtime_negotiation_outcome(
        {"ingress": {"minimum": minimum}, "hops": hops, "destination": {"interface": destination}})[0]


class SequenceTests(unittest.TestCase):
    def test_the_selection_of_rt_026(self):
        cases = [
            (context(V1), interface(V1, 1), {"decision": "send", "governed_by": V1}),
            (context(V1), interface(V2, 2), {"decision": "send", "governed_by": V2}),
            (context(V2), interface(V2, 2), {"decision": "send", "governed_by": V2}),
            (context(V2), interface(V1, 1), refuse(0)),
            (context(V2, True), interface(V1, 1), {"decision": "send", "governed_by": V1}),
            (context(V2, True), None, refuse(0)),
            (context(V2), interface("plenora-runtime-binding-v3", 3), refuse(0)),
            (context(V1), interface(V2, 1), refuse(0)),
        ]
        for stated, destination, expected in cases:
            with self.subTest(stated=stated, destination=destination):
                self.assertEqual(derive([hop("sender", stated)], destination), expected)

    def test_the_ingress_of_a_new_request(self):
        # Silent: the default of 1.0, unless the ingress requires 2.0.
        self.assertEqual(derive([hop("sender", None)], interface(V1, 1)),
                         {"decision": "send", "governed_by": V1})
        self.assertEqual(derive([hop("sender", None)], interface(V2, 2), V2), refuse(0))
        self.assertEqual(derive([hop("sender", context(V1))], interface(V2, 2), V2), refuse(0))
        self.assertEqual(derive([hop("sender", context(V2))], interface(V2, 2), V2),
                         {"decision": "send", "governed_by": V2})
        # A first reception from another hop has no acceptance record: it
        # cannot be a new request.
        self.assertEqual(derive([hop("hop", context(V2))], interface(V2, 2)), refuse(0))

    def test_forwardings_keep_the_context_of_the_first_acceptance(self):
        stated = context(V2)
        kept = [hop("sender", stated, stated), hop("hop", stated, stated), hop("hop", stated)]
        self.assertEqual(derive(kept, interface(V2, 2)), {"decision": "send", "governed_by": V2})
        lost = [hop("sender", stated, stated), hop("hop", stated, None), hop("hop", None)]
        self.assertEqual(derive(lost, interface(V1, 1)), refuse(2))
        altered = [hop("sender", stated, stated), hop("hop", stated, context(V1)), hop("hop", context(V1))]
        self.assertEqual(derive(altered, interface(V1, 1)), refuse(2))
        cannot = [hop("sender", stated, stated), hop("hop", stated, None, carries=False), hop("hop", None)]
        self.assertEqual(derive(cannot, interface(V2, 2)), refuse(1))
        # A redrive republished from outside, or a resend by the sender, is a
        # forwarding: never the default of 1.0.
        redrive = [hop("sender", stated, stated), hop("hop", stated, None), hop("sender", None)]
        self.assertEqual(derive(redrive, interface(V1, 1)), refuse(2))
        resend = [hop("sender", stated, stated), hop("hop", stated, None), hop("sender", stated)]
        self.assertEqual(derive(resend, interface(V2, 2)), {"decision": "send", "governed_by": V2})
        unreadable = [hop("sender", stated, stated), hop("hop", stated, record="unreadable")]
        self.assertEqual(derive(unreadable, interface(V2, 2)), refuse(1))


class VectorTests(unittest.TestCase):
    def test_every_published_vector_agrees_with_the_rules(self):
        self.assertEqual(validator.validate_runtime_negotiation_vectors(), [])

    def test_the_vectors_exercise_every_branch_of_the_derivation(self):
        """Each branch of RT-026 and RT-027 the validator can take is taken by
        at least one vector. This is branch coverage of the derivation, not a
        claim that every sequence of hops is covered."""
        taken = set()
        for path in VECTORS.glob("*.json"):
            taken |= set(validator.runtime_negotiation_outcome(vector(path.name))[1])
        self.assertEqual(sorted(validator.NEGOTIATION_BRANCHES - taken), [])

    def test_a_wrong_decision_is_reported(self):
        original = validator.load_json

        def wrong(path):
            document = original(path)
            if path.parent.name == "runtime-negotiation-v1" and path.name == "context-lost-on-the-route-refused.json":
                document = copy.deepcopy(document)
                document["expect"] = {"decision": "send", "governed_by": V1}
            return document

        with patch.object(validator, "load_json", wrong):
            errors = validator.validate_runtime_negotiation_vectors()
        self.assertEqual(len(errors), 1)
        self.assertIn("context-lost-on-the-route-refused.json", errors[0])

    def test_a_sequence_must_be_consistent(self):
        """A hop receives from another hop what that hop forwarded, and the
        selecting hop forwards nothing; otherwise the vector is not a route."""
        original = validator.load_json
        for mutation in ("received differs", "selector forwards", "missing request", "not a request"):
            def changed(path, mutation=mutation):
                document = original(path)
                if path.parent.name == "runtime-negotiation-v1" and path.name == "intermediary-preserves-context.json":
                    document = copy.deepcopy(document)
                    if mutation == "received differs":
                        document["hops"][1]["receives"] = None
                    elif mutation == "selector forwards":
                        document["hops"][-1]["forwards"] = document["hops"][-1]["receives"]
                    elif mutation == "missing request":
                        document["request"] = "../runtime-v1/absent-request.json"
                    else:
                        document["request"] = "../runtime-v1/database-query-success.json"
                return document

            with self.subTest(mutation), patch.object(validator, "load_json", changed):
                errors = [error for error in validator.validate_runtime_negotiation_vectors()
                          if "intermediary-preserves-context.json" in error]
                self.assertEqual(len(errors), 1, errors)

    def test_nothing_travels_past_a_refusal(self):
        """The refusing hop ends the route: a vector whose ingress refuses (an
        unreadable record) but still forwards to a later hop is refused, even
        when it states the refusal it derives."""
        original = validator.load_json

        def after_refusal(path):
            document = original(path)
            if path.parent.name == "runtime-negotiation-v1" and path.name == "declared-2-0-to-server-2-0.json":
                document = copy.deepcopy(document)
                document["hops"][0]["record"] = "unreadable"
                document["expect"] = {"decision": "refuse", "at_hop": 0, "category": "unsupported",
                                      "phase": "validate", "remote_effect": "none", "retry": "never"}
            return document

        with patch.object(validator, "load_json", after_refusal):
            errors = validator.validate_runtime_negotiation_vectors()
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("hops follow the hop that refuses", errors[0])
        # The published negative example, registered in the inventory.
        schemas = {name: validator.load_json(ROOT / "schemas" / name) for name in validator.EXPECTED_SCHEMAS}
        self.assertEqual(validator.validate_negotiation_violating(schemas, validator.schema_registry(schemas)), [])
        for relative in validator.NEGOTIATION_VIOLATING:
            example = validator.load_json(ROOT / relative)
            self.assertIsNotNone(example["hops"][0]["forwards"])
            self.assertEqual(validator.negotiation_vector_errors(example),
                             ["hops follow the hop that refuses the request (RT-027)"])

    def test_the_gate_validates_their_schema(self):
        schemas = {name: validator.load_json(ROOT / "schemas" / name) for name in validator.EXPECTED_SCHEMAS}
        registry = validator.schema_registry(schemas)
        self.assertEqual(validator.validate_machine_documents(schemas, registry), [])
        bad = vector("declared-2-0-to-server-2-0.json")
        bad["expect"] = {"decision": "refuse"}
        self.assertTrue(validator.instance_errors(
            schemas["runtime-negotiation-vector-v1.schema.json"], bad, registry))


if __name__ == "__main__":
    unittest.main()
