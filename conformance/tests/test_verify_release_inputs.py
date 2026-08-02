from __future__ import annotations

import copy
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import jsonschema

from conformance.verify_release_inputs import (
    ReleaseVerificationError,
    collect_observation,
    main,
    validate_manifest,
    validate_observation,
    verify_releases,
)


ROOT = Path(__file__).resolve().parents[2]


VALID_COMPONENT = {
    "name": "plenora-data-tools",
    "repository": "PlenoraETL/plenora-data-tools",
    "tag": "v1.0.0",
    "tag_object": "b4a5bcd827c1c815460029681e3ce25bff915c2c",
    "revision": "7a47504482569636b6c0e268477d155010d3b030",

    "release": {
        "id": 363535950,
        "url": "https://github.com/PlenoraETL/plenora-data-tools/releases/tag/v1.0.0",
        "draft": False,
        "prerelease": False,
    },
    "source_archive": {
        "sha256": "471a80438832fc62564b14675cf0a7581bd3e4df96ace1cf7374ac4be7b8d545",
        "bytes": 1403268,
    },
    "crates_publish": False,
}

IO_COMPONENT = {
    **copy.deepcopy(VALID_COMPONENT),
    "name": "plenora-IO-tools",
    "repository": "PlenoraETL/plenora-IO-tools",
    "tag_object": "679d023a311bb5b42c7dc7f8663e6d766c0b9973",
    "revision": "ca7f34c6b732700fa79f579f7b003df27ce54b09",

    "release": {
        "id": 363535956,
        "url": "https://github.com/PlenoraETL/plenora-IO-tools/releases/tag/v1.0.0",
        "draft": False,
        "prerelease": False,
    },
    "source_archive": {
        "sha256": "97a75cb3d09e16efd8b9d8eed3f8c2ec73983336d90ed94c9379821d382f033d",
        "bytes": 766222,
    },
}

DATABASE_COMPONENT = {
    **copy.deepcopy(VALID_COMPONENT),
    "name": "plenora-database-tools",
    "repository": "PlenoraETL/plenora-database-tools",
    "tag_object": "b0b83ddc0fcabcb47b98eb361e35a0587965af94",
    "revision": "89c82c4c700550decc394bb1e43b22c8a32e44e1",

    "release": {
        "id": 363535961,
        "url": "https://github.com/PlenoraETL/plenora-database-tools/releases/tag/v1.0.0",
        "draft": False,
        "prerelease": False,
    },
    "source_archive": {
        "sha256": "52462c6cd0acd5338c432c6deccfc02664a1486dc7e6fc39394cd3f7df305a62",
        "bytes": 579822,
    },
}

ALL_COMPONENTS = (VALID_COMPONENT, IO_COMPONENT, DATABASE_COMPONENT)

DATA_PATCH_COMPONENT = {
    **copy.deepcopy(VALID_COMPONENT),
    "tag": "v1.0.1",
    "tag_object": "c47a82f5b63a2c5cdf264057e5dbcc1a69a58d62",
    "revision": "aab8152902a209955b2ea657dfeaeea10408f866",

    "release": {
        "id": 363567976,
        "url": "https://github.com/PlenoraETL/plenora-data-tools/releases/tag/v1.0.1",
        "draft": False,
        "prerelease": False,
    },
    "source_archive": {
        "sha256": "c9474bfc9aaceb5ac4fe7598755adfe5b09ef83f7defb06d5ba24edcb9dcee69",
        "bytes": 1405535,
    },
}


def valid_manifest() -> dict:
    return {
        "schema_version": 1,
        "gate_id": "plenora-release-inputs-v1",
        "inventory_id": "plenora-system-v1.0.0",
        "contracts": {
            "revision": "e81c3ce7941bacbdb0e083f03c512ae22a6b924a",
            "icd": "2.0-rc16",
        },
        "components": copy.deepcopy(list(ALL_COMPONENTS)),
    }


def patched_manifest() -> dict:
    manifest = valid_manifest()
    manifest["inventory_id"] = "plenora-system-v1.0.1"
    manifest["components"][0] = copy.deepcopy(DATA_PATCH_COMPONENT)
    return manifest


def valid_observation() -> dict:
    component = VALID_COMPONENT
    return {
        "tag": component["tag"],
        "tag_object": component["tag_object"],
        "revision": component["revision"],
        "release": copy.deepcopy(component["release"]),
        "source_archive": copy.deepcopy(component["source_archive"]),
    }


class ManifestValidationTests(unittest.TestCase):
    def test_release_inventories_match_json_schema(self) -> None:
        schema = json.loads(
            (ROOT / "conformance/schemas/release-inventory.schema.json").read_text(
                encoding="utf-8"
            )
        )
        for path in sorted((ROOT / "conformance/releases").glob("*.json")):
            with self.subTest(path=path.name):
                jsonschema.validate(
                    json.loads(path.read_text(encoding="utf-8")), schema
                )

    def test_valid_manifest_has_no_errors(self) -> None:
        self.assertEqual(validate_manifest(valid_manifest()), [])

    def test_data_patch_release_is_allowed(self) -> None:
        self.assertEqual(validate_manifest(patched_manifest()), [])

    def test_versioned_inventory_files_match_the_trusted_authority(self) -> None:
        for filename in ("v1.0.0.json", "v1.0.1.json"):
            with self.subTest(filename=filename):
                manifest = json.loads(
                    (ROOT / "conformance" / "releases" / filename).read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(validate_manifest(manifest), [])

    def test_repository_is_pinned_by_component(self) -> None:
        manifest = valid_manifest()
        manifest["components"][0]["repository"] = "OtherOrg/plenora-data-tools"
        self.assertIn("trusted authority", "\n".join(validate_manifest(manifest)))

    def test_historical_inventory_cannot_authorize_data_patch(self) -> None:
        manifest = valid_manifest()
        manifest["components"][0] = copy.deepcopy(DATA_PATCH_COMPONENT)
        self.assertIn("trusted authority", "\n".join(validate_manifest(manifest)))

    def test_well_formed_untrusted_revision_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["components"][0]["revision"] = "0" * 40
        self.assertIn("trusted authority", "\n".join(validate_manifest(manifest)))

    def test_patch_tag_is_rejected_for_non_data_component(self) -> None:
        manifest = patched_manifest()
        manifest["components"][1]["tag"] = "v1.0.1"
        manifest["components"][1]["release"]["url"] = (
            "https://github.com/PlenoraETL/plenora-IO-tools/releases/tag/v1.0.1"
        )
        self.assertIn(
            "trusted authority",
            "\n".join(validate_manifest(manifest)),
        )

    def test_duplicate_component_name_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["components"].append(copy.deepcopy(VALID_COMPONENT))
        self.assertIn("duplicate component name", "\n".join(validate_manifest(manifest)))

    def test_missing_required_component_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["components"].pop()
        self.assertIn("component set", "\n".join(validate_manifest(manifest)))

    def test_critical_mutations_are_rejected(self) -> None:
        mutations = (
            (("schema_version",), 2),
            (("gate_id",), "other"),
            (("inventory_id",), "other"),
            (("contracts", "revision"), "0" * 40),
            (("components", 0, "tag"), "v2.0.0"),
            (("components", 0, "tag_object"), "bad"),
            (("components", 0, "revision"), "bad"),

            (("components", 0, "release", "id"), 0),
            (("components", 0, "release", "url"), "http://example.invalid"),
            (("components", 0, "release", "draft"), True),
            (("components", 0, "release", "prerelease"), True),
            (("components", 0, "source_archive", "sha256"), "bad"),
            (("components", 0, "source_archive", "bytes"), 0),
            (("components", 0, "crates_publish"), True),
        )
        for path, value in mutations:
            with self.subTest(path=path):
                manifest = valid_manifest()
                cursor = manifest
                for part in path[:-1]:
                    cursor = cursor[part]
                cursor[path[-1]] = value
                self.assertTrue(validate_manifest(manifest))


class ObservationValidationTests(unittest.TestCase):
    def test_matching_live_observation_has_no_errors(self) -> None:
        self.assertEqual(
            validate_observation(VALID_COMPONENT, valid_observation()), []
        )

    def test_each_live_identity_mismatch_is_rejected(self) -> None:
        mutations = (
            (("tag_object",), "0" * 40),
            (("revision",), "0" * 40),
            (("release", "id"), 1),
            (("release", "url"), "https://github.com/wrong/release"),
            (("release", "draft"), True),
            (("release", "prerelease"), True),
            (("source_archive", "sha256"), "0" * 64),
            (("source_archive", "bytes"), 1),
        )
        for path, value in mutations:
            with self.subTest(path=path):
                observed = valid_observation()
                cursor = observed
                for part in path[:-1]:
                    cursor = cursor[part]
                cursor[path[-1]] = value
                self.assertTrue(validate_observation(VALID_COMPONENT, observed))


class LiveCollectionTests(unittest.TestCase):
    def api_json(self, endpoint: str) -> dict:
        responses = {
            "repos/PlenoraETL/plenora-data-tools/git/ref/tags/v1.0.0": {
                "object": {
                    "type": "tag",
                    "sha": VALID_COMPONENT["tag_object"],
                }
            },
            (
                "repos/PlenoraETL/plenora-data-tools/git/tags/"
                + VALID_COMPONENT["tag_object"]
            ): {
                "object": {
                    "type": "commit",
                    "sha": VALID_COMPONENT["revision"],
                }
            },
            "repos/PlenoraETL/plenora-data-tools/releases/tags/v1.0.0": {
                "id": VALID_COMPONENT["release"]["id"],
                "html_url": VALID_COMPONENT["release"]["url"],
                "tag_name": VALID_COMPONENT["tag"],
                "draft": False,
                "prerelease": False,
            },
        }
        return copy.deepcopy(responses[endpoint])

    def test_collects_annotated_tag_release_and_download_digest(self) -> None:
        archive = b"stable source archive"
        component = copy.deepcopy(VALID_COMPONENT)
        import hashlib

        component["source_archive"] = {
            "sha256": hashlib.sha256(archive).hexdigest(),
            "bytes": len(archive),
        }
        observation = collect_observation(
            component,
            api_json=self.api_json,
            api_bytes=lambda endpoint: archive,
        )
        self.assertEqual(validate_observation(component, observation), [])

    def test_lightweight_tag_is_rejected_before_release_claim(self) -> None:
        def lightweight(endpoint: str) -> dict:
            if "/git/ref/tags/" in endpoint:
                return {
                    "object": {
                        "type": "commit",
                        "sha": VALID_COMPONENT["revision"],
                    }
                }
            return self.api_json(endpoint)

        with self.assertRaisesRegex(ReleaseVerificationError, "annotated"):
            collect_observation(
                VALID_COMPONENT,
                api_json=lightweight,
                api_bytes=lambda endpoint: b"unused",
            )

    def test_tag_object_must_peel_to_commit(self) -> None:
        def nested_tag(endpoint: str) -> dict:
            value = self.api_json(endpoint)
            if "/git/tags/" in endpoint:
                value["object"]["type"] = "tag"
            return value

        with self.assertRaisesRegex(ReleaseVerificationError, "commit"):
            collect_observation(
                VALID_COMPONENT,
                api_json=nested_tag,
                api_bytes=lambda endpoint: b"unused",
            )


class ReleaseGateTests(unittest.TestCase):
    @staticmethod
    def observation_for(component: dict) -> dict:
        return {
            "tag": component["tag"],
            "tag_object": component["tag_object"],
            "revision": component["revision"],
            "release": copy.deepcopy(component["release"]),
            "source_archive": copy.deepcopy(component["source_archive"]),
        }

    def test_all_exact_releases_pass_the_gate(self) -> None:
        report = verify_releases(valid_manifest(), self.observation_for)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(len(report["components"]), 3)
        self.assertTrue(all(not row["errors"] for row in report["components"]))

    def test_one_identity_mismatch_fails_the_whole_gate(self) -> None:
        def mismatch(component: dict) -> dict:
            observed = self.observation_for(component)
            if component["name"] == "plenora-IO-tools":
                observed["revision"] = "0" * 40
            return observed

        report = verify_releases(valid_manifest(), mismatch)
        self.assertEqual(report["status"], "fail")
        failed = [row for row in report["components"] if row["errors"]]
        self.assertEqual([row["name"] for row in failed], ["plenora-IO-tools"])

    def test_collection_error_is_a_component_failure_not_a_crash(self) -> None:
        def broken(component: dict) -> dict:
            if component["name"] == "plenora-database-tools":
                raise ReleaseVerificationError("remote release missing")
            return self.observation_for(component)

        report = verify_releases(valid_manifest(), broken)
        self.assertEqual(report["status"], "fail")
        self.assertIn(
            "remote release missing",
            "\n".join(report["components"][2]["errors"]),
        )

    def test_invalid_manifest_prevents_remote_collection(self) -> None:
        manifest = valid_manifest()
        manifest["components"].pop()

        def must_not_run(component: dict) -> dict:
            self.fail("collector must not run for an invalid manifest")

        report = verify_releases(manifest, must_not_run)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(report["manifest_errors"])
        self.assertEqual(report["components"], [])


class CommandLineTests(unittest.TestCase):
    def test_main_writes_a_passing_live_report(self) -> None:
        manifest = valid_manifest()

        def observe(component: dict, **_: object) -> dict:
            return ReleaseGateTests.observation_for(component)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            report_path = root / "report.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with (
                patch(
                    "conformance.verify_release_inputs.collect_observation",
                    side_effect=observe,
                ),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "--manifest",
                        str(manifest_path),
                        "--json-out",
                        str(report_path),
                    ],
                )
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(len(report["components"]), 3)


if __name__ == "__main__":
    unittest.main()
