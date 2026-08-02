from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import struct
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "conformance" / "campaigns" / "row-diagnostics-v1" / "cases.json"
JUDGE = ROOT / "conformance" / "judge_row_diagnostics.py"
GENERATOR = ROOT / "conformance" / "campaigns" / "row-diagnostics-v1" / "generate_fixtures.py"


def load_judge():
    if not JUDGE.is_file():
        raise AssertionError("row diagnostics corpus judge is required")
    spec = importlib.util.spec_from_file_location("judge_row_diagnostics", JUDGE)
    if spec is None or spec.loader is None:
        raise AssertionError("row diagnostics corpus judge is not loadable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RowDiagnosticsCorpusTests(unittest.TestCase):
    def test_declared_cases_pass_the_corpus_judge(self) -> None:
        self.assertTrue(CAMPAIGN.is_file(), "row diagnostics cases are required")
        campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
        judge = load_judge()

        report = judge.judge_campaign(campaign, campaign["reference_observations"])

        self.assertEqual(report["status"], "pass", report)
        self.assertEqual(
            [case["id"] for case in report["cases"]],
            [
                "read-shapefile-invalid-geometry",
                "read-invalid-date",
                "write-constraint-confirmed-rollback",
                "write-constraint-rollback-outcome-unknown",
            ],
        )

    def test_duplicate_observation_ids_are_rejected(self) -> None:
        campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
        observations = deepcopy(campaign["reference_observations"])
        observations.append(deepcopy(observations[0]))
        judge = load_judge()

        with self.assertRaisesRegex(ValueError, "duplicate observation id"):
            judge.judge_campaign(campaign, observations)

    def test_duplicate_declared_case_ids_are_rejected(self) -> None:
        campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
        campaign["cases"].append(deepcopy(campaign["cases"][0]))

        with self.assertRaisesRegex(ValueError, "duplicate declared case id"):
            load_judge().judge_campaign(campaign, campaign["reference_observations"])

    def test_campaign_identity_and_version_are_validated(self) -> None:
        campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
        judge = load_judge()

        for field, value in (
            ("schema_version", 2),
            ("campaign_id", "other-campaign"),
            ("contract", "other-contract"),
        ):
            with self.subTest(field=field):
                mutated = deepcopy(campaign)
                mutated[field] = value
                with self.assertRaisesRegex(ValueError, "unsupported campaign"):
                    judge.judge_campaign(mutated, mutated["reference_observations"])

    def test_mutations_fail_closed(self) -> None:
        campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
        judge = load_judge()

        def event(observations: list[dict[str, object]], identifier: str) -> dict[str, object]:
            return next(row for row in observations if row["id"] == identifier)

        def declared_case(manifest: dict[str, object], identifier: str) -> dict[str, object]:
            return next(row for row in manifest["cases"] if row["id"] == identifier)

        def assign(root: object, path: tuple[object, ...], value: object) -> None:
            cursor = root
            for part in path[:-1]:
                cursor = cursor[part]
            cursor[path[-1]] = value

        mutations: list[tuple[str, dict[str, object], list[dict[str, object]], str, str]] = []

        observations = deepcopy(campaign["reference_observations"])
        identifier = "read-shapefile-invalid-geometry"
        assign(event(observations, identifier)["diagnostics"], ("examples", 0, "source_index"), 18)
        mutations.append(("source_index_oracle", campaign, observations, identifier, "row diagnostics mismatch"))

        semantic_specs = [
            ("cause", "read-invalid-date", ("examples", 0, "cause"), "conversion.other"),
            (
                "count",
                "read-shapefile-invalid-geometry",
                ("counts", "shapefile.unclosed_ring"),
                2,
            ),
            ("total", "read-invalid-date", ("total",), 3),
            (
                "unknown_with_value",
                "write-constraint-rollback-outcome-unknown",
                ("write_outcome", "certainly_rolled_back", "value"),
                4_999,
            ),
            (
                "rejected_count_mismatch",
                "write-constraint-confirmed-rollback",
                ("diagnostic_state_counts", "certainly_rejected"),
                2,
            ),
            (
                "duplicate_source_index",
                "read-shapefile-invalid-geometry",
                ("examples", 1, "source_index"),
                17,
            ),
            (
                "read_write_state",
                "read-invalid-date",
                ("examples", 0, "write_state"),
                "certainly_rejected",
            ),
        ]
        for name, identifier, path, value in semantic_specs:
            mutated_campaign = deepcopy(campaign)
            observations = deepcopy(campaign["reference_observations"])
            assign(event(observations, identifier)["diagnostics"], path, value)
            assign(
                declared_case(mutated_campaign, identifier)["expected_diagnostics"],
                path,
                value,
            )
            mutations.append(
                (name, mutated_campaign, observations, identifier, "invalid diagnostics")
            )

        for name, mutated_campaign, observations, identifier, expected_issue in mutations:
            with self.subTest(mutation=name):
                report = judge.judge_campaign(mutated_campaign, observations)
                self.assertEqual(report["status"], "fail", report)
                case_report = next(row for row in report["cases"] if row["id"] == identifier)
                self.assertTrue(
                    any(expected_issue in issue for issue in case_report["issues"]),
                    case_report,
                )

    def test_semantic_mutation_is_isolated_from_oracle_equality(self) -> None:
        campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
        observations = deepcopy(campaign["reference_observations"])
        identifier = "read-shapefile-invalid-geometry"
        observed = next(row for row in observations if row["id"] == identifier)
        declared = next(row for row in campaign["cases"] if row["id"] == identifier)
        observed["diagnostics"]["counts"]["shapefile.unclosed_ring"] = 2
        declared["expected_diagnostics"]["counts"]["shapefile.unclosed_ring"] = 2
        judge = load_judge()
        original_loader = judge._load_validator
        judge._load_validator = lambda: (lambda _report: None)
        try:
            report = judge.judge_campaign(campaign, observations)
        finally:
            judge._load_validator = original_loader

        self.assertEqual(report["status"], "pass", report)

    def test_generator_produces_deterministic_real_fixtures(self) -> None:
        self.assertTrue(GENERATOR.is_file(), "row diagnostics fixture generator is required")
        spec = importlib.util.spec_from_file_location("generate_row_fixtures", GENERATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        def hashes(root: Path) -> dict[str, str]:
            return {
                str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(root.rglob("*"))
                if path.is_file()
            }

        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = Path(first_dir)
            second = Path(second_dir)
            module.generate(first)
            module.generate(second)
            self.assertEqual(hashes(first), hashes(second))

            with (first / "read-invalid-date.csv").open(newline="", encoding="utf-8") as stream:
                dates = list(csv.DictReader(stream))
            self.assertEqual(len(dates), 1025)
            self.assertEqual(dates[4]["effective_date"], "2026-02-30")
            self.assertEqual(dates[1004]["effective_date"], "not-a-date")

            with (first / "write-constraint.csv").open(newline="", encoding="utf-8") as stream:
                writes = list(csv.DictReader(stream))
            self.assertEqual(len(writes), 5200)
            self.assertGreater(float(writes[4998]["area_m2"]), 0)
            self.assertLess(float(writes[4999]["area_m2"]), 0)

            shp = first / "read-shapefile-invalid-geometry" / "particelle.shp"
            facts = self._shapefile_ring_facts(shp)
            self.assertEqual(facts[17], [(False, True)])
            self.assertEqual(facts[89], [(True, False)])
            self.assertEqual(facts[113], [(False, True)])
            for index, ring_facts in enumerate(facts):
                if index not in {17, 89, 113}:
                    self.assertEqual(ring_facts, [(True, True)], f"record {index}")

            dbf = (first / "read-shapefile-invalid-geometry" / "particelle.dbf").read_bytes()
            header_length = struct.unpack_from("<H", dbf, 8)[0]
            record_length = struct.unpack_from("<H", dbf, 10)[0]
            field_names = [
                dbf[offset : offset + 11].split(b"\0", 1)[0].decode("ascii")
                for offset in range(32, header_length - 1, 32)
            ]
            self.assertIn("ID_PART", field_names)
            row_17 = header_length + 17 * record_length
            self.assertEqual(dbf[row_17 + 1 : row_17 + 19].decode("ascii").strip(), "9007199254741009")

            campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
            fixture = campaign["cases"][0]["fixture"]
            self.assertEqual(fixture["configured_key"], "ID_PART")
            self.assertEqual(
                fixture["key_policy"],
                {"emit_value": True, "encoding": "decimal_string"},
            )

    @staticmethod
    def _shapefile_ring_facts(path: Path) -> list[list[tuple[bool, bool]]]:
        payload = path.read_bytes()
        offset = 100
        records: list[list[tuple[bool, bool]]] = []
        while offset < len(payload):
            _number, words = struct.unpack_from(">ii", payload, offset)
            body = payload[offset + 8 : offset + 8 + words * 2]
            parts_count, points_count = struct.unpack_from("<ii", body, 36)
            starts = list(struct.unpack_from(f"<{parts_count}i", body, 44))
            points_offset = 44 + parts_count * 4
            points = [struct.unpack_from("<2d", body, points_offset + index * 16) for index in range(points_count)]
            starts.append(points_count)
            ring_facts = []
            for start, end in zip(starts, starts[1:]):
                ring = points[start:end]
                area_twice = sum(
                    x1 * y2 - x2 * y1
                    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1])
                )
                ring_facts.append((area_twice < 0, ring[0] == ring[-1]))
            records.append(ring_facts)
            offset += 8 + words * 2
        return records


if __name__ == "__main__":
    unittest.main()
