from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

from conformance_checks import example_inventory_errors, public_semantic_errors

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"

MAX_ERROR_BYTES = 524_288
MAX_ERROR_DETAILS_BYTES = 262_144
MAX_ERROR_DETAILS_DEPTH = 8
MAX_ERROR_DETAILS_OBJECT_PROPERTIES = 128
MAX_ERROR_DETAILS_ARRAY_ITEMS = 128
MAX_ERROR_DETAILS_STRING_BYTES = 4_096
MAX_ERROR_DETAILS_NODES = 2_048

EXPECTED_SCHEMAS = {
    "adoption-manifest-v1.schema.json",
    "adoption-manifest-v2.schema.json",
    "adoption-manifest-v3.schema.json",
    "adoption-manifest-v4.schema.json",
    "arrow-metadata-vector-v1.schema.json",
    "capabilities-v1.schema.json",
    "capabilities-v2.schema.json",
    "cli-envelope-v2.schema.json",
    "composition-v1.schema.json",
    "data-execution-input-v3.schema.json",
    "data-execution-result-v3.schema.json",
    "data-plan-v1.schema.json",
    "error-v1.schema.json",
    "operation-registry-v1.schema.json",
    "plan-budget-v1.schema.json",
    "public-catalog-v1.schema.json",
    "row-diagnostics-v1.schema.json",
    "runtime-vector-v1.schema.json",
    "surface-bindings-v1.schema.json",
}

CASES = {
    "valid": {
        "cli-envelope-v2.schema.json": [
            "examples/valid/cli-success.json",
            "examples/valid/cli-error.json",
        ],
        "capabilities-v1.schema.json": ["examples/valid/capabilities.json"],
        "capabilities-v2.schema.json": [
            "examples/valid/capabilities-v2.json",
            "examples/valid/capabilities-rest-v2.json",
        ],
        "error-v1.schema.json": ["examples/valid/error-details-bounded.json"],
        "row-diagnostics-v1.schema.json": ["examples/valid/row-diagnostics.json"],
        "adoption-manifest-v1.schema.json": ["examples/valid/adoption-manifest.json"],
        "adoption-manifest-v2.schema.json": [
            "examples/valid/adoption-manifest-v2.json"
        ],
        "adoption-manifest-v3.schema.json": [
            "examples/valid/adoption-manifest-v3.json",
            "examples/valid/adoption-manifest-v3-deviation.json",
        ],
        "adoption-manifest-v4.schema.json": [
            "examples/valid/adoption-manifest-v4.json"
        ],
        "plan-budget-v1.schema.json": [
            "examples/valid/plan-budget-v6.json",
            "examples/valid/plan-budget-v6-absent.json",
            "examples/valid/plan-budget-v5.json",
        ],
        "data-plan-v1.schema.json": [
            "examples/valid/data-plan-v1.json",
            "examples/valid/data-plan-v1-geo.json",
            "examples/valid/data-plan-v1-identity.json",
        ],
    },
    "invalid": {
        "cli-envelope-v2.schema.json": ["examples/invalid/cli-missing-protocol.json"],
        "error-v1.schema.json": ["examples/invalid/error-after-missing-delay.json"],
        "capabilities-v1.schema.json": [
            "examples/invalid/capabilities-unavailable-without-reason.json"
        ],
        "capabilities-v2.schema.json": [
            "examples/invalid/capabilities-v2-unavailable-without-reason.json"
        ],
        "row-diagnostics-v1.schema.json": [
            "examples/invalid/row-diagnostics-redacted-value.json"
        ],
        "adoption-manifest-v1.schema.json": [
            "examples/invalid/adoption-floating-revision.json"
        ],
        "adoption-manifest-v2.schema.json": [
            "examples/invalid/adoption-v2-floating-revision.json"
        ],
        "adoption-manifest-v3.schema.json": [
            "examples/invalid/adoption-v3-python-missing-api-modes.json",
            "examples/invalid/adoption-v3-deviation-missing-scope.json",
        ],
        "adoption-manifest-v4.schema.json": [
            "examples/invalid/adoption-v4-artifact-missing-identity.json",
            "examples/invalid/adoption-v4-python-missing-api-modes.json",
            "examples/invalid/adoption-v4-deviation-missing-scope.json",
        ],
        "runtime-vector-v1.schema.json": [
            "examples/invalid/runtime-correlation-not-uuid.json",
            "examples/invalid/runtime-message-id-missing.json",
            "examples/invalid/runtime-message-id-not-uuid.json",
        ],
        "plan-budget-v1.schema.json": [
            "examples/invalid/plan-budget-v5-with-domain.json",
            "examples/invalid/plan-budget-zero.json",
            "examples/invalid/plan-budget-unknown-version.json",
        ],
        "data-plan-v1.schema.json": [
            "examples/invalid/data-plan-v1-schema-version.json",
            "examples/invalid/data-plan-v1-domain-budget.json",
            "examples/invalid/data-plan-v1-zero-budget.json",
            "examples/invalid/data-plan-v1-integer-overflow.json",
            "examples/invalid/data-plan-v1-zero-arity.json",
            "examples/invalid/data-plan-v1-operation-spelling.json",
            "examples/invalid/data-plan-v1-no-inputs.json",
        ],
    },
}

ERROR_BOUND_CASES = {
    "examples/valid/error-details-bounded.json": False,
    "examples/invalid/error-details-too-deep.json": True,
}

REST_CAPABILITY_CASES = {
    "examples/valid/capabilities-rest-v2.json": None,
    "examples/invalid/rest-capabilities-attributes-missing-contract.json": "attribute contract ID",
}

REST_BOUNDARY_CASES = {
    "examples/valid/rest-runtime-artifact-request.json": None,
    "examples/invalid/rest-runtime-artifact-local-path.json": "private local path",
    "examples/invalid/rest-runtime-artifact-relative-path.json": "private local path",
    "examples/invalid/rest-download-artifact-source-only.json": "forbids artifact_source",
    "examples/invalid/rest-upload-artifact-sink-only.json": "forbids artifact_sink",
    "examples/invalid/rest-runtime-upload-inline-credentials.json": "inline credential",
    "examples/invalid/rest-download-local-mutating-method.json": "mutating REST download",
}

PUBLIC_SEMANTIC_CASES = {
    "examples/invalid/capabilities-v2-duplicate-identity.json": [
        "capabilities-v2.schema.json",
        "CAP-005"
    ],
    "examples/invalid/capabilities-v2-undeclared-surface.json": [
        "capabilities-v2.schema.json",
        "CAP-007"
    ],
    "examples/invalid/adoption-v4-duplicate-contract.json": [
        "adoption-manifest-v4.schema.json",
        "duplicate contract"
    ],
    "examples/invalid/adoption-v4-undeclared-artifact.json": [
        "adoption-manifest-v4.schema.json",
        "undeclared artifact"
    ],
    "examples/invalid/adoption-v4-duplicate-artifact.json": [
        "adoption-manifest-v4.schema.json",
        "ambiguous artifact"
    ],
    "examples/invalid/adoption-v4-conflicting-surface.json": [
        "adoption-manifest-v4.schema.json",
        "surface differs"
    ]
}

COMPONENTS = {
    "plenora-database-tools",
    "plenora-data-tools",
    "plenora-io-tools",
    "plenora-rest-tools",
    "plenora-storage-tools",
}

REST_COMPONENT = "plenora-rest-tools"
REST_ATTRIBUTE_CONTRACT = "plenora-rest-capability-attributes-v1"
REST_FILE_TRANSFER_INPUT = "plenora-rest-file-transfer-input-v1"
DATABASE_COMPONENT = "plenora-database-tools"
DATABASE_ATTRIBUTE_CONTRACT = "plenora-database-capability-attributes-v1"
STORAGE_COMPONENT = "plenora-storage-tools"
STORAGE_ATTRIBUTE_CONTRACT = "plenora-storage-capability-attributes-v1"
STORAGE_OPERATIONS = {
    "storage.test",
    "storage.list",
    "storage.stat",
    "storage.get",
    "storage.put",
    "storage.copy",
    "storage.delete",
}

DATA_COMPONENT = "plenora-data-tools"
DATA_PLAN_CONTRACT = "plenora-data-plan-v1"
DATA_KERNEL_COUNT = 146

REQUIRED_OPERATIONS = {
    "plenora-database-tools": {
        "database.test_connection",
        "database.list_catalogs",
        "database.list_schemas",
        "database.list_objects",
        "database.describe_object",
        "database.read",
        "database.write",
    },
    "plenora-data-tools": {
        "data.catalog",
        "data.describe",
        "data.validate",
        "data.run",
    },
    "plenora-io-tools": {
        "io.catalog",
        "io.inspect",
        "io.layers",
        "io.read",
        "io.write",
        "io.convert",
    },
    "plenora-rest-tools": {
        "rest.test",
        "rest.generate",
        "rest.enrich",
        "rest.download",
        "rest.upload",
    },
    "plenora-storage-tools": STORAGE_OPERATIONS,
}

ARROW_TYPES = [
    "point",
    "linestring",
    "polygon",
    "multipoint",
    "multilinestring",
    "multipolygon",
    "geometrycollection",
    "circularstring",
    "compoundcurve",
    "curvepolygon",
    "multicurve",
    "multisurface",
    "polyhedralsurface",
    "tin",
    "triangle",
    "unknown",
]

MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def reject_constant(name: str) -> Any:
    raise ValueError(f"{name} is not JSON")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, parse_constant=reject_constant)


def schema_registry(schemas: dict[str, dict[str, Any]]) -> Registry:
    resources = []
    for schema in schemas.values():
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str):
            raise ValueError("every schema must declare a string $id")
        resources.append((schema_id, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def instance_errors(
    schema: dict[str, Any], instance: Any, registry: Registry
) -> list[str]:
    validator = Draft202012Validator(schema, registry=registry)
    return [
        error.message
        for error in sorted(
            validator.iter_errors(instance), key=lambda item: list(item.path)
        )
    ]


def validate_examples(
    schemas: dict[str, dict[str, Any]], registry: Registry
) -> list[str]:
    failures: list[str] = []
    for expectation, schema_cases in CASES.items():
        for schema_name, relative_paths in schema_cases.items():
            for relative_path in relative_paths:
                document = load_json(ROOT / relative_path)
                errors = instance_errors(schemas[schema_name], document, registry)
                if expectation == "valid" and not errors:
                    errors.extend(public_semantic_errors(schema_name, document))
                if expectation == "valid" and errors:
                    failures.append(f"{relative_path} must validate: {errors[0]}")
                if expectation == "invalid" and not errors:
                    failures.append(f"{relative_path} must be rejected")
    return failures


def validate_public_semantics(schemas, registry) -> list[str]:
    failures = []
    for relative, (schema_name, expected) in PUBLIC_SEMANTIC_CASES.items():
        document = load_json(ROOT / relative)
        if instance_errors(schemas[schema_name], document, registry):
            failures.append(f"{relative} must satisfy its structural schema")
            continue
        errors = public_semantic_errors(schema_name, document)
        if not any(expected in error for error in errors):
            failures.append(f"{relative} did not exercise {expected}")
    return failures


def validate_example_inventory() -> list[str]:
    registrations = []
    for expectation, schemas in CASES.items():
        for schema, paths in schemas.items():
            registrations.extend((path, expectation, f"schema:{schema}") for path in paths)
    registrations.extend(
        (path, "invalid" if invalid else "valid", "error-bounds")
        for path, invalid in ERROR_BOUND_CASES.items()
    )
    for name, cases in [("rest-capabilities", REST_CAPABILITY_CASES), ("rest-boundary", REST_BOUNDARY_CASES)]:
        registrations.extend((path, "valid" if error is None else "invalid", name) for path, error in cases.items())
    registrations.extend((path, "valid", "plan-budget") for path in PLAN_BUDGET_CONFORMING)
    registrations.extend((path, "invalid", "plan-budget") for path in PLAN_BUDGET_VIOLATING)
    registrations.extend((path, "valid", "data-plan") for path in DATA_PLAN_CONFORMING)
    registrations.extend((path, "invalid", "data-plan") for path in DATA_PLAN_VIOLATING)
    registrations.extend((path, "invalid", "data-plan-number") for path in DATA_PLAN_NUMBER_VIOLATING)
    registrations.extend((path, "invalid", "public-semantics") for path in PUBLIC_SEMANTIC_CASES)
    return example_inventory_errors(ROOT, registrations)


def compact_json_size(value: Any) -> int:
    return len(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )


def error_bound_errors(error: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if compact_json_size(error) > MAX_ERROR_BYTES:
        errors.append("compact error JSON exceeds the byte limit")

    details = error.get("details")
    if not isinstance(details, dict):
        return errors
    if compact_json_size(details) > MAX_ERROR_DETAILS_BYTES:
        errors.append("compact error details JSON exceeds the byte limit")

    node_count = 0

    def visit(value: Any, depth: int) -> None:
        nonlocal node_count
        node_count += 1
        if depth > MAX_ERROR_DETAILS_DEPTH:
            errors.append("error details exceed the nesting-depth limit")
            return
        if isinstance(value, dict):
            if len(value) > MAX_ERROR_DETAILS_OBJECT_PROPERTIES:
                errors.append("error details object exceeds the property limit")
            for child in value.values():
                visit(child, depth + 1)
        elif isinstance(value, list):
            if len(value) > MAX_ERROR_DETAILS_ARRAY_ITEMS:
                errors.append("error details array exceeds the item limit")
            for child in value:
                visit(child, depth + 1)
        elif (
            isinstance(value, str)
            and len(value.encode("utf-8")) > MAX_ERROR_DETAILS_STRING_BYTES
        ):
            errors.append("error details string exceeds the byte limit")

    visit(details, 1)
    if node_count > MAX_ERROR_DETAILS_NODES:
        errors.append("error details exceed the JSON-node limit")
    return errors


def validate_error_bound_vectors(
    schemas: dict[str, dict[str, Any]], registry: Registry
) -> list[str]:
    failures: list[str] = []
    for relative_path, must_violate in ERROR_BOUND_CASES.items():
        error = load_json(ROOT / relative_path)
        schema_errors = instance_errors(
            schemas["error-v1.schema.json"], error, registry
        )
        if schema_errors:
            failures.append(f"{relative_path} must satisfy the structural error schema")
            continue
        bound_errors = error_bound_errors(error)
        if must_violate and not bound_errors:
            failures.append(f"{relative_path} must violate a semantic error bound")
        if not must_violate and bound_errors:
            failures.append(f"{relative_path} must satisfy semantic error bounds")

    probes = {
        "details byte limit": (
            {"items": ["x" * MAX_ERROR_DETAILS_STRING_BYTES] * 65},
            "details JSON exceeds the byte limit",
        ),
        "error byte limit": (
            {"items": ["x" * MAX_ERROR_DETAILS_STRING_BYTES] * 128},
            "error JSON exceeds the byte limit",
        ),
        "object property limit": (
            {f"field_{index}": index for index in range(129)},
            "object exceeds the property limit",
        ),
        "array item limit": (
            {"items": list(range(129))},
            "array exceeds the item limit",
        ),
        "string byte limit": (
            {"value": "x" * (MAX_ERROR_DETAILS_STRING_BYTES + 1)},
            "string exceeds the byte limit",
        ),
        "JSON node limit": (
            {"groups": [list(range(128)) for _ in range(16)]},
            "exceed the JSON-node limit",
        ),
    }
    base_error = {
        "category": "internal",
        "phase": "unknown",
        "remote_effect": "none",
        "retry": {"kind": "never"},
        "message": "Semantic bound probe.",
    }
    for name, (details, expected_fragment) in probes.items():
        probe_errors = error_bound_errors({**base_error, "details": details})
        if not any(expected_fragment in error for error in probe_errors):
            failures.append(f"generated {name} probe did not exercise its guard")
    return failures


def validate_machine_documents(
    schemas: dict[str, dict[str, Any]], registry: Registry
) -> list[str]:
    groups = {
        "public-catalog-v1.schema.json": sorted(
            (ROOT / "catalogs").glob("*-tools-v*.json")
        ),
        "operation-registry-v1.schema.json": sorted(
            (ROOT / "catalogs").glob("data-kernels-v*.json")
        ),
        "surface-bindings-v1.schema.json": sorted((ROOT / "bindings").glob("*.json")),
        "composition-v1.schema.json": [ROOT / "composition/pipelines-v1.json"],
        "arrow-metadata-vector-v1.schema.json": sorted(
            (ROOT / "vectors/arrow-v1").glob("*.json")
        ),
        "runtime-vector-v1.schema.json": sorted(
            (ROOT / "vectors/runtime-v1").glob("*.json")
        ),
    }
    failures: list[str] = []
    for schema_name, paths in groups.items():
        for path in paths:
            errors = instance_errors(schemas[schema_name], load_json(path), registry)
            if errors:
                failures.append(
                    f"{path.relative_to(ROOT)} must validate against {schema_name}: {errors[0]}"
                )
    return failures


CATALOG_FILE = re.compile(r"^(?P<name>[a-z]+-tools)-v(?P<version>[1-9][0-9]*)\.json$")


def load_catalog_versions() -> dict[str, dict[int, dict[str, Any]]]:
    """Every catalog version of every component, keyed by file version.

    A component may publish a later catalog version for incompatible
    operation changes (COMPATIBILITY.md); the earlier file stays as an
    available identity.
    """
    versions: dict[str, dict[int, dict[str, Any]]] = {}
    for path in sorted((ROOT / "catalogs").glob("*-tools-v*.json")):
        match = CATALOG_FILE.match(path.name)
        if match is None:
            raise ValueError(f"catalog file name {path.name} is not <name>-tools-v<N>.json")
        document = load_json(path)
        if document["component"] != f"plenora-{match['name']}":
            raise ValueError(f"{path.name} declares component {document['component']}")
        versions.setdefault(document["component"], {})[int(match["version"])] = document
    return versions


def load_catalogs() -> dict[str, dict[str, Any]]:
    """The current target catalog of each component: its highest version.

    Bindings, composition edges and runtime vectors describe the current
    target; earlier catalog versions are checked on their own.
    """
    return {
        component: by_version[max(by_version)]
        for component, by_version in load_catalog_versions().items()
    }


def profile_path(component: str, profile: str) -> Path:
    """`plenora-x-tools-profile-v1` lives in `profiles/x-tools.md`, later
    profile versions in `profiles/x-tools-v<N>.md`."""
    name = component.removeprefix("plenora-")
    version = profile.rsplit("-v", 1)[1]
    suffix = "" if version == "1" else f"-v{version}"
    return ROOT / "profiles" / f"{name}{suffix}.md"


def repeated_identity_errors(
    versions: dict[str, dict[int, dict[str, Any]]],
) -> list[str]:
    """An operation identity repeated by a later catalog version keeps its
    contract: same requirement, payloads, side effect and controls. Surfaces
    and attributes may only grow (a new surface or attribute is compatible,
    COMPATIBILITY.md); nothing may be dropped or changed."""
    failures: list[str] = []
    fixed = ("requirement", "input", "output", "side_effect", "controls")
    for component, by_version in versions.items():
        seen: dict[tuple[str, int], tuple[int, dict[str, Any]]] = {}
        for version in sorted(by_version):
            for operation in by_version[version]["operations"]:
                key = (operation["id"], operation["version"])
                if key not in seen:
                    seen[key] = (version, operation)
                    continue
                earlier_version, earlier = seen[key]
                label = f"{component} {key[0]}@{key[1]} in catalog v{version}"
                for field in fixed:
                    if operation[field] != earlier[field]:
                        failures.append(f"{label} changes {field} from catalog v{earlier_version}")
                if not set(earlier["surfaces"]) <= set(operation["surfaces"]):
                    failures.append(f"{label} drops surfaces of catalog v{earlier_version}")
                earlier_attributes = earlier.get("attributes", {})
                attributes = operation.get("attributes", {})
                for name, value in earlier_attributes.items():
                    if attributes.get(name) != value:
                        failures.append(f"{label} changes attribute {name} of catalog v{earlier_version}")
                seen[key] = (version, operation)
    return failures


def catalog_versions(
    catalogs: dict[str, dict[str, Any]],
) -> dict[str, dict[int, dict[str, Any]]]:
    """Every catalog version on disk, with each component's current version
    replaced by the document the caller passes (tests mutate that one)."""
    versions = load_catalog_versions()
    for component, catalog in catalogs.items():
        if component in versions:
            versions[component][max(versions[component])] = catalog
    return versions


def operation_index(
    catalogs: dict[str, dict[str, Any]],
) -> dict[tuple[str, str, int], dict[str, Any]]:
    """Every `(component, operation, version)` of every catalog version.

    A binding, an edge or a vector refers to one operation version, and the
    catalog version that declares it decides its surfaces and contracts.
    """
    index: dict[tuple[str, str, int], dict[str, Any]] = {}
    for component, by_version in catalog_versions(catalogs).items():
        for version in sorted(by_version):
            for operation in by_version[version]["operations"]:
                index[(component, operation["id"], operation["version"])] = operation
    return index


def validate_catalog_semantics(catalogs: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    if set(catalogs) != COMPONENTS:
        failures.append(
            "public catalog component inventory differs from the five-library contract"
        )
        return failures

    versions = catalog_versions(catalogs)
    every_version = [
        (component, version, catalog)
        for component, by_version in versions.items()
        for version, catalog in sorted(by_version.items())
    ]
    for component, by_version in versions.items():
        if sorted(by_version) != list(range(1, max(by_version) + 1)):
            failures.append(f"{component} catalog versions are not contiguous from 1")
    for component, version, catalog in every_version:
        expected_profile = f"{component}-profile-v{version}"
        if catalog["profile"] != expected_profile:
            failures.append(
                f"{component} catalog v{version} must select profile {expected_profile}"
            )
            continue
        path = profile_path(component, catalog["profile"])
        if not path.exists():
            failures.append(f"{component} v{version} has no profile document")
        elif (
            f"Profile identifier: `{catalog['profile']}`"
            not in path.read_text(encoding="utf-8")
        ):
            failures.append(
                f"{component} v{version} profile identifier does not match its catalog"
            )

    failures.extend(repeated_identity_errors(versions))

    for component, version, catalog in every_version:
        identities = [(item["id"], item["version"]) for item in catalog["operations"]]
        if len(identities) != len(set(identities)):
            failures.append(f"{component} has duplicate operation identities")

        required = {
            item["id"]
            for item in catalog["operations"]
            if item["requirement"] == "required"
        }
        missing = REQUIRED_OPERATIONS[component] - required
        if missing:
            failures.append(
                f"{component} is missing required operations: {sorted(missing)}"
            )

        for operation in catalog["operations"]:
            for surface in operation["surfaces"]:
                applicability = catalog["target_surfaces"][surface]
                if applicability in {"not_applicable", "undecided"}:
                    failures.append(
                        f"{component} {operation['id']} lists inapplicable surface {surface}"
                    )

        if component == REST_COMPONENT:
            required_runtime = [
                operation
                for operation in catalog["operations"]
                if operation["requirement"] == "required"
                and "runtime" in operation["surfaces"]
            ]
            if required_runtime and catalog["target_surfaces"]["runtime"] != "required":
                failures.append(
                    "rest-tools required runtime operations require a required runtime target"
                )

            # Every version of every operation is checked; a lookup by
            # identifier alone would let one version hide another.
            for operation in catalog["operations"]:
                attributes = operation.get("attributes")
                if (
                    not isinstance(attributes, dict)
                    or attributes.get("contract") != REST_ATTRIBUTE_CONTRACT
                ):
                    failures.append(
                        f"rest-tools {operation['id']} lacks its capability attributes contract"
                    )
                if not operation["controls"]["idempotency_key"]:
                    failures.append(
                        f"rest-tools {operation['id']} must accept idempotency keys"
                    )

            transfers = {
                (item["id"], item["version"]): item
                for item in catalog["operations"]
                if item["id"] in {"rest.download", "rest.upload"}
            }
            # Each transfer operation on its own, then each version pair.
            for (operation_id, operation_version), operation in sorted(transfers.items()):
                if operation["input"]["contract"] != REST_FILE_TRANSFER_INPUT:
                    failures.append(
                        "REST file transfer operations use the wrong input contract"
                    )
                if operation_id == "rest.download" and operation["side_effect"] != "remote":
                    failures.append(
                        "REST download must use the conservative remote side-effect class"
                    )
                if (
                    operation_id == "rest.upload"
                    and "application/octet-stream" in operation["input"]["content_types"]
                ):
                    failures.append(
                        "REST upload v1 embeds raw bytes in its JSON invocation envelope"
                    )
                other = transfers.get(("rest.upload", operation_version))
                if (
                    operation_id == "rest.download"
                    and other is not None
                    and operation["input"]["contract"] != other["input"]["contract"]
                ):
                    failures.append(
                        "REST download and upload use different transfer inputs"
                    )

        if component == DATABASE_COMPONENT:
            database_operations = catalog["operations"]
            if catalog["status"] != "normative":
                failures.append(
                    "database-tools v1 must be normative after component-owned schema publication"
                )
            if any(item["id"].startswith("arcgis.") for item in database_operations):
                failures.append(
                    "database-tools must not own ArcGIS operations before ownership is ratified"
                )
            for write in (item for item in database_operations if item["id"] == "database.write"):
                attributes = write.get("attributes")
                if (
                    not isinstance(attributes, dict)
                    or attributes.get("contract") != DATABASE_ATTRIBUTE_CONTRACT
                ):
                    failures.append(
                        "database.write lacks its capability attributes contract"
                    )
                if "write_modes" in (attributes or {}):
                    failures.append(
                        "the common database catalog must not advertise provider-independent write modes"
                    )
            for item in database_operations:
                if item["id"] == "database.query" and item["side_effect"] != "none":
                    failures.append("database.query must remain read-only")
                if item["id"] == "database.execute" and item["side_effect"] != "remote":
                    failures.append("database.execute must declare remote side effects")

    storage = catalogs[STORAGE_COMPONENT]
    if storage["status"] != "normative":
        failures.append("storage-tools v1 must be normative after reviewed policy ratification")
    expected_storage_surfaces = {
        "rust": "required",
        "cli": "required",
        "python_sdk": "required",
        "runtime": "required",
    }
    if storage["target_surfaces"] != expected_storage_surfaces:
        failures.append("storage-tools has the wrong target surface selection")
    # Every reviewed operation keeps its version 1; another version of one of
    # them may coexist (COMPATIBILITY.md) and every rule below applies to each
    # version, so none stands in for another.
    storage_identities = {(item["id"], item["version"]) for item in storage["operations"]}
    if {item["id"] for item in storage["operations"]} != STORAGE_OPERATIONS or not {
        (name, 1) for name in STORAGE_OPERATIONS
    } <= storage_identities:
        failures.append(
            "storage-tools v1 must define the seven reviewed operations, each at version 1"
        )
    for operation in storage["operations"]:
        operation_id = operation["id"]
        action = operation_id.removeprefix("storage.")
        suffix = f"v{operation['version']}" if operation["version"] == 1 else r"v[1-9][0-9]*"
        if set(operation["surfaces"]) != {"rust", "cli", "python_sdk", "runtime"}:
            failures.append(f"{operation_id} has the wrong selected surfaces")
        for direction in ("input", "output"):
            if not re.fullmatch(
                rf"plenora-storage-{action}-{direction}-{suffix}",
                operation[direction]["contract"],
            ):
                failures.append(f"{operation_id} has the wrong {direction} contract")
        for direction in ("input", "output"):
            payload = operation[direction]
            if payload["content_types"] != ["application/json"]:
                failures.append(f"{operation_id} {direction} must use JSON")
            if payload["interchange_contracts"]:
                failures.append(
                    f"{operation_id} must not imply an unreviewed interchange contract"
                )
        if operation["controls"] != {
            "cancellation": True,
            "deadline": True,
            "idempotency_key": False,
        }:
            failures.append(f"{operation_id} has the wrong execution controls")
        attributes = operation.get("attributes")
        if (
            not isinstance(attributes, dict)
            or attributes.get("contract") != STORAGE_ATTRIBUTE_CONTRACT
        ):
            failures.append(f"{operation_id} lacks its capability attribute contract")
        attributes = attributes if isinstance(attributes, dict) else {}
        if operation_id in {"storage.test", "storage.list", "storage.stat"}:
            if operation["side_effect"] != "none":
                failures.append(f"{operation_id} must remain side-effect free")
        elif operation["side_effect"] != "remote":
            failures.append(f"{operation_id} must use the conservative remote side effect")
        if operation_id == "storage.get" and attributes.get("artifact_role") != "sink":
            failures.append("storage.get must declare its artifact sink")
        if operation_id == "storage.put" and attributes.get("artifact_role") != "source":
            failures.append("storage.put must declare its artifact source")
        if operation_id in {"storage.put", "storage.copy"}:
            if attributes.get("publication_policy") != "required":
                failures.append(f"{operation_id} must require an explicit publication policy")
            if attributes.get("create_if_absent") != "provider_operation_capability":
                failures.append(
                    f"{operation_id} must scope create-if-absent to its provider operation capability"
                )

    failures.extend(data_registry_errors())
    for version, catalog in sorted(versions[DATA_COMPONENT].items()):
        failures.extend(data_catalog_errors(catalog, version))
    return failures


def data_registries() -> dict[int, dict[str, Any]]:
    return {
        int(path.stem.rsplit("-v", 1)[1]): load_json(path)
        for path in sorted((ROOT / "catalogs").glob("data-kernels-v*.json"))
    }


def data_registry_errors() -> list[str]:
    """Every registry version: the same 146 kernel identities, each in its
    family; a later registry renames nothing, its versions only move."""
    failures: list[str] = []
    registries = data_registries()
    if sorted(registries) != list(range(1, max(registries) + 1)):
        failures.append("data kernel registry versions are not contiguous from 1")
    first_ids = None
    for version, registry in sorted(registries.items()):
        if registry["registry"] != f"plenora-data-kernel-catalog-v{version}":
            failures.append(f"data-kernels-v{version} declares registry {registry['registry']}")
        kernel_ids = [item["id"] for item in registry["operations"]]
        if len(kernel_ids) != DATA_KERNEL_COUNT or len(set(kernel_ids)) != DATA_KERNEL_COUNT:
            failures.append(
                f"data kernel registry v{version} must contain {DATA_KERNEL_COUNT} unique operation identities"
            )
        for item in registry["operations"]:
            if item["id"].split(".", 1)[0] != item["family"]:
                failures.append(f"data kernel {item['id']} has an inconsistent family")
        if first_ids is None:
            first_ids = set(kernel_ids)
        elif set(kernel_ids) != first_ids:
            failures.append(f"data kernel registry v{version} changes kernel identities")
    return failures


DATA_CATALOG_RESULT = {2: "plenora-data-catalog-result-v2"}

# The operation identities of each data-tools catalog version.
DATA_OPERATION_VERSIONS = {
    1: [("data.catalog", 1), ("data.describe", 1), ("data.validate", 1), ("data.run", 1)],
    2: [
        ("data.catalog", 2), ("data.describe", 1), ("data.validate", 2),
        ("data.run", 2), ("data.run", 3),
    ],
}


def data_catalog_errors(catalog: dict[str, Any], version: int) -> list[str]:
    """Each data-tools catalog version against its own expectations.

    Version 1: `data.catalog` returns the registry itself and `data.run`
    names it. Version 2: `data.catalog` returns its own result contract
    (profile v2, DT-001) and names the registry; `data.validate` and
    `data.run` name the registry and the plan format; `data.run` writes local
    files and is not bound on the runtime surface.
    """
    failures: list[str] = []
    # Every lookup names the operation version: catalog v2 carries `data.run`
    # 2 and 3, and an order or a lookup by identifier alone would check the
    # wrong one.
    expected = DATA_OPERATION_VERSIONS[version]
    found = sorted((item["id"], item["version"]) for item in catalog["operations"])
    if found != sorted(expected):
        return [f"data-tools v{version} must declare exactly {sorted(expected)}"]
    by_identity = {(item["id"], item["version"]): item for item in catalog["operations"]}
    operations = {
        operation_id: by_identity[(operation_id, operation_version)]
        for operation_id, operation_version in expected
        if (operation_id, operation_version) != ("data.run", 3)
    }
    catalog_operation = operations.get("data.catalog")
    if catalog_operation is None:
        return [f"data-tools v{version} has no data.catalog operation"]
    attributes = catalog_operation.get("attributes", {})
    registry_path = ROOT / attributes.get("registry", "")
    if not registry_path.is_file():
        return [f"data-tools v{version} data.catalog does not name an existing kernel registry"]
    registry_id = load_json(registry_path)["registry"]
    run = operations.get("data.run", {})
    if version == 1:
        if catalog_operation["output"]["contract"] != registry_id:
            failures.append("data-tools v1 data.catalog output contract differs from its registry")
        if run.get("attributes", {}).get("kernel_registry") != registry_id:
            failures.append("data-tools v1 data.run names a different kernel registry")
        return failures
    if catalog_operation["output"]["contract"] != DATA_CATALOG_RESULT.get(version):
        failures.append(f"data-tools v{version} data.catalog has the wrong result contract")
    if attributes.get("kernel_registry") != registry_id:
        failures.append(f"data-tools v{version} data.catalog names a different kernel registry")
    for operation_id in ("data.validate", "data.run"):
        operation_attributes = operations.get(operation_id, {}).get("attributes", {})
        if operation_attributes.get("kernel_registry") != registry_id:
            failures.append(f"data-tools v{version} {operation_id} names a different kernel registry")
        if operation_attributes.get("plan_contract") != DATA_PLAN_CONTRACT:
            failures.append(
                f"data-tools v{version} {operation_id} must declare plan contract {DATA_PLAN_CONTRACT}"
            )
    if run.get("side_effect") != "local":
        failures.append("data.run writes its outputs to local files and must declare local")
    if "runtime" in run.get("surfaces", []):
        failures.append(
            "data.run with named outputs has no runtime representation (profile v2)"
        )
    failures.extend(data_run_3_errors(catalog, version, registry_id))
    return failures


DATA_RUN_3 = {
    "requirement": "conditional",
    "surfaces": ["rust", "runtime"],
    "input": {
        "contract": "plenora-data-execution-input-v3",
        "content_types": ["application/json"],
        "interchange_contracts": [],
    },
    "output": {
        "contract": "plenora-data-execution-result-v3",
        "content_types": ["application/json"],
        "interchange_contracts": [],
    },
    "side_effect": "remote",
    "controls": {"cancellation": True, "deadline": True, "idempotency_key": False},
}


def data_run_3_errors(catalog: dict[str, Any], version: int, registry_id: str) -> list[str]:
    """`data.run` 3 (profile v2, DT-RUN-001..DT-RUN-008): the runtime
    representation with named outputs. Its sources and sinks are artifacts,
    so its payloads are JSON; publication to sinks that may be remote makes
    it `remote`, and it is conditional on the runtime surface."""
    entries = [
        item for item in catalog["operations"]
        if item["id"] == "data.run" and item["version"] == 3
    ]
    if version < 2:
        return ["data-tools v1 cannot declare data.run 3"] if entries else []
    if len(entries) != 1:
        return [f"data-tools v{version} must declare data.run 3 once"]
    run = entries[0]
    failures = [
        f"data-tools v{version} data.run 3 has the wrong {field}"
        for field, expected in DATA_RUN_3.items()
        if run.get(field) != expected
    ]
    attributes = run.get("attributes", {})
    if attributes.get("kernel_registry") != registry_id:
        failures.append(f"data-tools v{version} data.run 3 names a different kernel registry")
    if attributes.get("plan_contract") != DATA_PLAN_CONTRACT:
        failures.append(f"data-tools v{version} data.run 3 must declare plan contract {DATA_PLAN_CONTRACT}")
    if attributes.get("bounded_materialization") is not True:
        failures.append(f"data-tools v{version} data.run 3 must declare bounded materialization")
    arrow = ["application/vnd.apache.arrow.stream", "application/vnd.apache.arrow.file"]
    if attributes.get("artifact_content_types") != {"source": arrow, "sink": arrow}:
        failures.append(f"data-tools v{version} data.run 3 has the wrong artifact content types")
    if attributes.get("artifact_interchange_contracts") != ["plenora-arrow-interchange-v1"]:
        failures.append(f"data-tools v{version} data.run 3 must carry Arrow Interchange artifacts")
    parquet = ["application/vnd.apache.parquet"]
    if attributes.get("extension_content_types") != {"source": parquet, "sink": parquet}:
        failures.append(f"data-tools v{version} data.run 3 has the wrong extension content types")
    return failures


def validate_bindings(catalogs: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    index = operation_index(catalogs)
    expected_files = {"cli-v1.json", "python-sdk-v1.json", "runtime-v1.json"}
    paths = sorted((ROOT / "bindings").glob("*.json"))
    if {path.name for path in paths} != expected_files:
        failures.append("surface binding inventory differs from the contract")
        return failures

    for path in paths:
        document = load_json(path)
        surface = document["surface"]
        components = {item["component"]: item for item in document["components"]}
        if set(components) != COMPONENTS:
            failures.append(
                f"{path.name} must contain all five components exactly once"
            )
            continue

        actual: set[tuple[str, str, int]] = set()
        versions = catalog_versions(catalogs)
        for component, section in components.items():
            applicabilities = {
                catalog["target_surfaces"][surface]
                for catalog in versions[component].values()
            }
            if "required" in applicabilities and section["artifact"] is None:
                failures.append(f"{path.name} lacks the required {component} artifact")
            if applicabilities <= {"not_applicable", "undecided"} and any(
                (
                    section["artifact"] is not None,
                    section["discovery"],
                    section["bindings"],
                )
            ):
                failures.append(
                    f"{path.name} exposes {component} despite target applicability "
                    f"{sorted(applicabilities)}"
                )
            if section["artifact"] is None and (section["discovery"] or section["bindings"]):
                failures.append(
                    f"{path.name} binds {component} operations without an artifact"
                )
            entrypoints: dict[str, set[str]] = {}
            for binding in section["bindings"]:
                key = (component, binding["operation"], binding["version"])
                operation = index.get(key)
                if operation is None:
                    failures.append(f"{path.name} binds unknown operation {key}")
                    continue
                if surface not in operation["surfaces"]:
                    failures.append(
                        f"{path.name} binds {binding['operation']} to undeclared surface {surface}"
                    )
                if binding["requirement"] != operation["requirement"]:
                    failures.append(
                        f"{path.name} requirement differs for {binding['operation']}"
                    )
                actual.add(key)
                for entrypoint in binding["entrypoints"]:
                    entrypoints.setdefault(entrypoint, set()).add(binding["operation"])

                if surface == "runtime":
                    capability = f"plenora.{component.removeprefix('plenora-')}"
                    expected = (
                        f"{capability}#{binding['operation']}@{binding['version']}"
                    )
                    if binding["entrypoints"] != [expected]:
                        failures.append(
                            f"{path.name} has a non-canonical runtime selector for {binding['operation']}"
                        )

            # SURFACE-BINDINGS-1.0 section 1: one spelling may serve several
            # versions of the SAME operation only when no catalog version
            # selects two of them (an artifact implements one catalog).
            if any(len(operations) > 1 for operations in entrypoints.values()):
                failures.append(
                    f"{path.name} has duplicate entrypoints for {component}"
                )
            spelling_versions: dict[str, set[tuple[str, int]]] = {}
            for binding in section["bindings"]:
                for entrypoint in binding["entrypoints"]:
                    spelling_versions.setdefault(entrypoint, set()).add(
                        (binding["operation"], binding["version"])
                    )
            for entrypoint, keys in spelling_versions.items():
                if len(keys) < 2:
                    continue
                for catalog in versions[component].values():
                    selected = {(item["id"], item["version"]) for item in catalog["operations"]}
                    if len(keys & selected) > 1:
                        failures.append(
                            f"{path.name} spelling {entrypoint!r} binds two versions "
                            f"selected by one {component} catalog"
                        )
            bound = [(binding["operation"], binding["version"]) for binding in section["bindings"]]
            if len(bound) != len(set(bound)):
                failures.append(
                    f"{path.name} binds one {component} operation version twice"
                )
            if section["artifact"] is not None and not section["discovery"]:
                failures.append(
                    f"{path.name} lacks discovery entrypoints for {component}"
                )

        expected = {
            key for key, operation in index.items() if surface in operation["surfaces"]
        }
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            failures.append(
                f"{path.name} binding coverage differs; missing={missing}, extra={extra}"
            )

    python_document = load_json(ROOT / "bindings/python-sdk-v1.json")
    database_section = next(
        (item for item in python_document["components"]
         if item["component"] == DATABASE_COMPONENT), None
    )
    if database_section is None:
        return failures
    def entrypoint_sets(section: dict[str, Any], operation_id: str) -> list[set[str]]:
        """The entrypoints of every version of one operation: each version is
        checked, none hides another."""
        return [
            set(item["entrypoints"])
            for item in section["bindings"]
            if item["operation"] == operation_id
        ]

    def every_binding(section: dict[str, Any], operation_id: str, expected: set[str]) -> bool:
        found = entrypoint_sets(section, operation_id)
        return bool(found) and all(entrypoints == expected for entrypoints in found)

    if not every_binding(database_section, "database.test_connection", {
        "plenora_database.test_connection",
        "plenora_database.atest_connection",
    }):
        failures.append(
            "database.test_connection must use dedicated SDK verification entrypoints"
        )
    if not every_binding(database_section, "database.query", {
        "Session.select",
        "AsyncSession.select",
    }):
        failures.append("database.query SDK bindings must remain read-only")
    mutating_entrypoints = {
        "Session.insert",
        "Session.update",
        "Session.delete",
        "Session.upsert",
        "AsyncSession.insert",
        "AsyncSession.update",
        "AsyncSession.delete",
        "AsyncSession.upsert",
    }
    execute_sets = entrypoint_sets(database_section, "database.execute")
    if not execute_sets or not all(
        mutating_entrypoints.issubset(entrypoints) for entrypoints in execute_sets
    ):
        failures.append(
            "mutating database SDK entrypoints must bind to database.execute"
        )
    storage_section = next(
        (item for item in python_document["components"]
         if item["component"] == STORAGE_COMPONENT), None
    )
    if storage_section is None:
        return failures
    if storage_section["artifact"] != "plenora-storage / plenora_storage":
        failures.append("storage SDK must declare its distribution and import identity")
    if set(storage_section["discovery"]) != {
        "plenora_storage.version", "Engine.capabilities", "AsyncEngine.capabilities"
    }:
        failures.append("storage SDK must expose version and discovery in both API modes")
    for operation_id in sorted(STORAGE_OPERATIONS):
        action = operation_id.removeprefix("storage.")
        if not every_binding(storage_section, operation_id, {
            f"Engine.{action}", f"AsyncEngine.{action}"
        }):
            failures.append(f"{operation_id} must bind both canonical SDK API modes")
    failures.extend(data_python_errors(python_document))
    return failures


def data_python_errors(python_document: dict[str, Any]) -> list[str]:
    """The data-tools SDK binds every operation as a module function in both
    API modes (`run` / `arun`), with version and capability discovery."""
    section = next(
        (item for item in python_document["components"]
         if item["component"] == DATA_COMPONENT), None
    )
    if section is None or (
        section["artifact"] is None and not section["discovery"] and not section["bindings"]
    ):
        return []
    failures: list[str] = []
    if section["artifact"] != "plenora-data / plenora_data":
        failures.append("data SDK must declare its distribution and import identity")
    if set(section["discovery"]) != {"plenora_data.version", "plenora_data.capabilities"}:
        failures.append("data SDK must expose version and capability discovery")
    for binding in section["bindings"]:
        action = binding["operation"].removeprefix("data.")
        if set(binding["entrypoints"]) != {f"plenora_data.{action}", f"plenora_data.a{action}"}:
            failures.append(f"{binding['operation']} must bind both canonical SDK API modes")
    return failures


def validate_composition(catalogs: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    index = operation_index(catalogs)
    document = load_json(ROOT / "composition/pipelines-v1.json")
    for position, edge in enumerate(document["edges"]):
        source_key = (
            edge["from"]["component"],
            edge["from"]["operation"],
            edge["from"]["version"],
        )
        target_key = (
            edge["to"]["component"],
            edge["to"]["operation"],
            edge["to"]["version"],
        )
        source = index.get(source_key)
        target = index.get(target_key)
        if source is None or target is None:
            failures.append(
                f"composition edge {position} refers to an unknown operation"
            )
            continue
        interchange = edge["interchange_contract"]
        content_type = edge["content_type"]
        if edge["mode"] == "adapter_required":
            declared_source_contracts = {
                source["output"]["contract"],
                *source["output"]["interchange_contracts"],
            }
            if interchange not in declared_source_contracts:
                failures.append(
                    f"composition edge {position} names undeclared source contract {interchange}"
                )
            if content_type not in source["output"]["content_types"]:
                failures.append(
                    f"composition edge {position} source lacks {content_type}"
                )
            continue
        if edge["mode"] != "direct":
            continue
        if interchange not in source["output"]["interchange_contracts"]:
            failures.append(f"composition edge {position} source lacks {interchange}")
        if interchange not in target["input"]["interchange_contracts"]:
            failures.append(f"composition edge {position} target lacks {interchange}")
        if content_type not in source["output"]["content_types"]:
            failures.append(f"composition edge {position} source lacks {content_type}")
        if content_type not in target["input"]["content_types"]:
            failures.append(f"composition edge {position} target lacks {content_type}")
    return failures


def rest_capability_errors(
    document: dict[str, Any], catalog: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if document.get("component") != REST_COMPONENT:
        return ["capability document has the wrong REST component identity"]

    expected = {(item["id"], item["version"]): item for item in catalog["operations"]}
    actual = {
        (item["id"], item["version"]): item for item in document.get("operations", [])
    }
    missing = sorted(set(expected) - set(actual))
    if missing:
        errors.append(f"REST capability document lacks catalog operations {missing}")

    for identity, operation in actual.items():
        target = expected.get(identity)
        if target is None:
            errors.append(
                f"REST capability document exposes unknown operation {identity}"
            )
            continue
        attributes = operation.get("attributes")
        if (
            not isinstance(attributes, dict)
            or attributes.get("contract") != REST_ATTRIBUTE_CONTRACT
        ):
            errors.append(f"{operation['id']} lacks the REST attribute contract ID")
        if set(operation["surfaces"]) != set(target["surfaces"]):
            errors.append(f"{operation['id']} surfaces differ from the REST catalog")
        for direction in ("input", "output"):
            if operation[direction]["contract"] != target[direction]["contract"]:
                errors.append(
                    f"{operation['id']} {direction} contract differs from the REST catalog"
                )
            if set(operation[direction]["content_types"]) != set(
                target[direction]["content_types"]
            ):
                errors.append(
                    f"{operation['id']} {direction} content types differ from the REST catalog"
                )
        if operation["side_effect"] != target["side_effect"]:
            errors.append(
                f"{operation['id']} side-effect class differs from the REST catalog"
            )
        if operation["controls"] != target["controls"]:
            errors.append(f"{operation['id']} controls differ from the REST catalog")
    return errors


def nested_items(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from nested_items(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_items(child)


def artifact_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from artifact_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from artifact_strings(child)


def is_local_path(value: str) -> bool:
    return bool(
        re.match(r"^[A-Za-z]:[\\/]", value)
        or value.startswith(("/", "\\"))
        or value.lower().startswith("file:")
        or any(
            segment == ".." for segment in value.replace(chr(92), "/").split("/")
        )
    )


def rest_boundary_errors(
    document: dict[str, Any], catalog: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    candidates = [
        item for item in catalog["operations"] if item["id"] == document.get("operation")
    ]
    if len(candidates) > 1:
        # Several versions: the example names the one it exercises.
        candidates = [item for item in candidates if item["version"] == document.get("version")]
    operation = candidates[0] if len(candidates) == 1 else None
    if document.get("surface") != "runtime":
        errors.append("REST artifact boundary example is not a runtime request")
    if operation is None or "runtime" not in operation["surfaces"]:
        return errors + [
            "REST artifact boundary example names an unknown runtime operation"
        ]
    if document.get("input_contract") != operation["input"]["contract"]:
        errors.append("REST runtime request has the wrong input contract")
    if document.get("content_type") not in operation["input"]["content_types"]:
        errors.append("REST runtime request has an unsupported envelope content type")
    if document.get("declared_side_effect") != operation["side_effect"]:
        errors.append("REST runtime request has a non-conservative side-effect class")

    payload = document.get("input", {})
    secret_keys = {
        "authorization",
        "credentials",
        "password",
        "token",
        "api_key",
        "secret",
    }
    for key, _value in nested_items(payload):
        if key.lower() in secret_keys:
            errors.append(
                f"REST runtime request contains inline credential field {key}"
            )

    has_source = "artifact_source" in payload
    has_sink = "artifact_sink" in payload
    if operation["id"] == "rest.download":
        if not has_sink:
            errors.append("REST download requires artifact_sink")
        if has_source:
            errors.append("REST download forbids artifact_source")
    if operation["id"] == "rest.upload":
        if not has_source:
            errors.append("REST upload requires artifact_source")
        if has_sink:
            errors.append("REST upload forbids artifact_sink")
    artifact_nodes = [
        payload[key] for key in ("artifact_source", "artifact_sink") if key in payload
    ]
    for node in artifact_nodes:
        if any(is_local_path(value) for value in artifact_strings(node)):
            errors.append("REST runtime artifact contains a private local path")

    method = payload.get("connection", {}).get("method")
    if (
        operation["id"] == "rest.download"
        and isinstance(method, str)
        and method.upper() not in {"GET", "HEAD", "OPTIONS"}
        and document.get("declared_side_effect") == "local"
    ):
        errors.append("mutating REST download cannot declare a local side effect")
    return errors


def validate_rest_examples(
    schemas: dict[str, dict[str, Any]],
    registry: Registry,
    catalog: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    for relative_path, expected_error in REST_CAPABILITY_CASES.items():
        document = load_json(ROOT / relative_path)
        structural = instance_errors(
            schemas["capabilities-v2.schema.json"], document, registry
        )
        if structural:
            failures.append(
                f"{relative_path} must satisfy the common capabilities structure"
            )
            continue
        errors = rest_capability_errors(document, catalog)
        if expected_error is None and errors:
            failures.append(
                f"{relative_path} must satisfy REST capability semantics: {errors[0]}"
            )
        if expected_error is not None and not any(
            expected_error in error for error in errors
        ):
            failures.append(f"{relative_path} did not exercise {expected_error}")

    for relative_path, expected_error in REST_BOUNDARY_CASES.items():
        errors = rest_boundary_errors(load_json(ROOT / relative_path), catalog)
        if expected_error is None and errors:
            failures.append(
                f"{relative_path} must satisfy REST runtime invariants: {errors[0]}"
            )
        if expected_error is not None and not any(
            expected_error in error for error in errors
        ):
            failures.append(f"{relative_path} did not exercise {expected_error}")
    return failures


def arrow_semantic_errors(vector: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if vector["schema_metadata"].get("plenora.contract.version") != "1":
        errors.append("schema contract version must be 1")

    field_ids: list[int] = []
    required_geometry = {
        "plenora.field_id",
        "plenora.geometry.encoding",
        "plenora.geometry.dimensions",
        "plenora.geometry.spatial_semantics",
        "plenora.geometry.precision",
        "plenora.geometry.types_declaration",
        "plenora.geometry.crs_resolution",
    }
    enums = {
        "plenora.geometry.encoding": {"wkb", "ewkb"},
        "plenora.geometry.dimensions": {"xy", "xyz", "xym", "xyzm", "unknown"},
        "plenora.geometry.spatial_semantics": {"geometry", "geography"},
        "plenora.geometry.precision": {"float64", "float32", "native"},
        "plenora.geometry.types_declaration": {"exact", "mixed", "unresolved"},
        "plenora.geometry.crs_resolution": {
            "resolved",
            "declared_unresolved",
            "missing",
        },
        "plenora.geometry.crs_definition_format": {"wkt", "wkt2", "projjson"},
        "plenora.geometry.axis_order": {
            "lon_lat",
            "lat_lon",
            "easting_northing",
            "northing_easting",
            "other",
            "unknown",
        },
    }

    for field in vector["fields"]:
        metadata = field["metadata"]
        field_id = metadata.get("plenora.field_id")
        if field_id is not None:
            try:
                parsed_id = int(field_id)
                if parsed_id < 0 or str(parsed_id) != field_id:
                    raise ValueError
                field_ids.append(parsed_id)
            except ValueError:
                errors.append(f"{field['name']} has an invalid field id")

        extension = metadata.get("ARROW:extension:name")
        has_geometry_keys = any(key.startswith("plenora.geometry.") for key in metadata)
        if extension != "geoarrow.wkb":
            if has_geometry_keys:
                errors.append(
                    f"{field['name']} has geometry metadata without geoarrow.wkb"
                )
            continue

        if field["type"] not in {"binary", "large_binary"}:
            errors.append(f"{field['name']} has incompatible GeoArrow storage")
        missing = required_geometry - set(metadata)
        if missing:
            errors.append(f"{field['name']} lacks geometry keys {sorted(missing)}")
        for key, values in enums.items():
            if key in metadata and metadata[key] not in values:
                errors.append(f"{field['name']} has invalid {key}")

        declaration = metadata.get("plenora.geometry.types_declaration")
        type_text = metadata.get("plenora.geometry.types")
        if declaration == "exact" and not type_text:
            errors.append(f"{field['name']} exact geometry types are empty")
        if declaration == "unresolved" and type_text is not None:
            errors.append(f"{field['name']} unresolved geometry types are present")
        if type_text is not None:
            values = type_text.split(",") if type_text else []
            try:
                positions = [ARROW_TYPES.index(value) for value in values]
            except ValueError:
                errors.append(f"{field['name']} has an unknown geometry type")
            else:
                if positions != sorted(set(positions)):
                    errors.append(
                        f"{field['name']} geometry types are not unique and ordered"
                    )

        resolution = metadata.get("plenora.geometry.crs_resolution")
        crs_id = metadata.get("plenora.geometry.crs_id")
        definition = metadata.get("plenora.geometry.crs_definition")
        definition_format = metadata.get("plenora.geometry.crs_definition_format")
        axis = metadata.get("plenora.geometry.axis_order")
        if (definition is None) != (definition_format is None):
            errors.append(f"{field['name']} CRS definition and format disagree")
        if resolution in {"resolved", "declared_unresolved"}:
            if not crs_id and not definition:
                errors.append(f"{field['name']} declared CRS has no identity")
            if axis is None:
                errors.append(f"{field['name']} declared CRS has no axis order")
        if resolution == "missing" and any(
            value is not None for value in (crs_id, definition, definition_format, axis)
        ):
            errors.append(f"{field['name']} missing CRS carries CRS metadata")

    if len(field_ids) != len(set(field_ids)):
        errors.append("field identifiers are not unique")
    return errors


def validate_arrow_vectors() -> list[str]:
    failures: list[str] = []
    for path in sorted((ROOT / "vectors/arrow-v1").glob("*.json")):
        vector = load_json(path)
        errors = arrow_semantic_errors(vector)
        if vector["expect"] == "valid" and errors:
            failures.append(
                f"{path.relative_to(ROOT)} must be semantically valid: {errors[0]}"
            )
        if vector["expect"] == "invalid" and not errors:
            failures.append(
                f"{path.relative_to(ROOT)} must contain a semantic violation"
            )
    return failures


def storage_vector_errors(
    vector: dict[str, Any], operation: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    payload = vector.get("payload", {})
    operation_id = operation["id"]

    def validate_artifact_metadata(node: Any, label: str) -> None:
        if not isinstance(node, dict) or set(node) != {
            "content_type",
            "size",
            "sha256",
        }:
            errors.append(f"{label} requires bounded artifact metadata")
            return
        content_type = node["content_type"]
        if content_type is not None and (
            not isinstance(content_type, str)
            or len(content_type) > 255
            or re.fullmatch(
                r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+",
                content_type,
            )
            is None
        ):
            errors.append(f"{label} has invalid content type metadata")
        size = node["size"]
        if size is not None and (
            not isinstance(size, int) or isinstance(size, bool) or size < 0
        ):
            errors.append(f"{label} has invalid size metadata")
        sha256 = node["sha256"]
        if sha256 is not None and (
            not isinstance(sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", sha256) is None
        ):
            errors.append(f"{label} has invalid SHA-256 metadata")

    if vector["kind"] == "request":
        if payload.get("schema_version") != 1:
            errors.append("storage request lacks schema_version 1")
        connection = payload.get("connection")
        if not isinstance(connection, dict):
            errors.append("storage request lacks its connection object")
        else:
            credential_ref = connection.get("credential_ref")
            if not isinstance(credential_ref, str) or not re.match(
                r"^[a-z][a-z0-9+.-]{1,31}:(//)?[^\s\\]+$", credential_ref
            ):
                errors.append("storage request has a non-opaque credential reference")

        secret_keys = {
            "authorization",
            "credentials",
            "password",
            "passwd",
            "token",
            "api_key",
            "secret",
            "private_key",
            "access_key",
            "secret_key",
        }
        for key, _value in nested_items(payload):
            if key.lower() in secret_keys:
                errors.append(f"storage request contains inline credential field {key}")
        if any(is_local_path(value) for value in artifact_strings(payload)):
            errors.append("storage runtime request contains a private local path")

        source = payload.get("artifact_source")
        sink = payload.get("artifact_sink")
        if operation_id == "storage.get":
            if not isinstance(sink, dict):
                errors.append("storage.get requires artifact_sink")
            elif not isinstance(sink.get("overwrite"), bool):
                errors.append("storage.get requires explicit sink overwrite")
            if source is not None:
                errors.append("storage.get forbids artifact_source")
        if operation_id == "storage.put":
            if not isinstance(source, dict):
                errors.append("storage.put requires artifact_source")
            if sink is not None:
                errors.append("storage.put forbids artifact_sink")
            if not isinstance(payload.get("overwrite"), bool):
                errors.append("storage.put requires explicit overwrite")
            if payload.get("publication_policy") not in {
                "best_effort",
                "atomic_required",
            }:
                errors.append("storage.put requires an explicit publication policy")
        for name, node in (("artifact_source", source), ("artifact_sink", sink)):
            if node is None:
                continue
            reference = node.get("reference") if isinstance(node, dict) else None
            # The component-owned artifact reference v1 is opaque and bounded;
            # accepting the scheme alone would allow an empty or unsafe handle.
            if (
                not isinstance(reference, str)
                or len(reference) > 512
                or re.fullmatch(
                    r"artifact://[A-Za-z0-9][A-Za-z0-9._~!$&'()*+,;=:@/?#%-]*",
                    reference,
                ) is None
                or is_local_path(reference)
            ):
                errors.append(f"storage {name} must use an opaque artifact reference")
            if isinstance(node, dict):
                validate_artifact_metadata(node.get("metadata"), name)
        if operation_id == "storage.list":
            cursor = payload.get("cursor")
            if cursor is not None and (
                not isinstance(cursor, str)
                or re.fullmatch(r"cursor://[0-9a-f]{64}", cursor) is None
                or len(cursor) > 512
            ):
                errors.append("storage.list cursor must be opaque and bounded")
        if operation_id == "storage.copy":
            if not isinstance(payload.get("overwrite"), bool):
                errors.append("storage.copy requires explicit overwrite")
            if payload.get("publication_policy") not in {
                "best_effort",
                "atomic_required",
            }:
                errors.append("storage.copy requires an explicit publication policy")
        if operation_id == "storage.delete" and not isinstance(
            payload.get("ignore_missing"), bool
        ):
            errors.append("storage.delete requires explicit missing behavior")

    if vector["kind"] == "success" and operation_id in {
        "storage.get",
        "storage.put",
    }:
        byte_count = payload.get("bytes_transferred")
        if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count < 0:
            errors.append("storage transfer success has an invalid byte count")
        checksum = payload.get("checksum")
        if (
            not isinstance(checksum, dict)
            or checksum.get("algorithm") != "sha256"
            or not isinstance(checksum.get("value"), str)
            or re.fullmatch(r"[0-9a-f]{64}", checksum["value"]) is None
        ):
            errors.append("storage transfer success lacks SHA-256 integrity metadata")
        artifact = payload.get("artifact")
        validate_artifact_metadata(artifact, "storage transfer result")
        if isinstance(artifact, dict) and isinstance(checksum, dict):
            if artifact.get("sha256") != checksum.get("value"):
                errors.append("storage transfer artifact SHA-256 conflicts with checksum")
            if artifact.get("size") != payload.get("bytes_transferred"):
                errors.append("storage transfer artifact size conflicts with byte count")
    if vector["kind"] == "success" and operation_id == "storage.list":
        cursor = payload.get("next_cursor")
        if cursor is not None and (
            not isinstance(cursor, str)
            or re.fullmatch(r"cursor://[0-9a-f]{64}", cursor) is None
            or len(cursor) > 512
        ):
            errors.append("storage.list result cursor must be opaque and bounded")
    if vector["kind"] == "error" and payload.get("remote_effect") == "unknown":
        if payload.get("retry", {}).get("kind") != "requires_recovery":
            errors.append("ambiguous storage errors must require recovery")
    if vector["kind"] == "error" and payload.get("remote_effect") == "partial":
        if payload.get("retry", {}).get("kind") not in {
            "never", "quarantine", "requires_recovery"
        }:
            errors.append("partial storage errors must forbid automatic retry")
    return errors


def validate_runtime_vectors(
    catalogs: dict[str, dict[str, Any]],
    schemas: dict[str, dict[str, Any]],
    registry: Registry,
) -> list[str]:
    failures: list[str] = []
    operations: dict[tuple[str, str], tuple[str, dict[str, Any]]] = {}
    for (component, operation_id, version), operation in operation_index(catalogs).items():
        key = (operation_id, str(version))
        if key in operations:
            failures.append(
                f"runtime vector lookup has duplicate operation {operation_id}@{version}"
            )
        operations[key] = (component, operation)

    storage_coverage = set()
    data_run_3_coverage: set[str] = set()
    data_run_3_vectors: list[dict[str, Any]] = []
    for path in sorted((ROOT / "vectors/runtime-v1").glob("*.json")):
        vector = load_json(path)
        metadata = vector["metadata"]
        operation_id = metadata.get("plenora.capability.operation")
        resolved = operations.get((operation_id, metadata.get("plenora.operation.version")))
        if resolved is None:
            failures.append(
                f"{path.relative_to(ROOT)} refers to unknown operation {operation_id} "
                f"version {metadata.get('plenora.operation.version')}"
            )
            continue
        component, operation = resolved
        if "runtime" not in operation["surfaces"]:
            failures.append(
                f"{path.relative_to(ROOT)} exercises {operation_id} on runtime, "
                "which its catalog version does not select"
            )
        if metadata.get("plenora.operation.version") != str(operation["version"]):
            failures.append(f"{path.relative_to(ROOT)} has wrong operation version")
        identities = (
            ("plenora.message.id", "message"),
            ("plenora.trace.correlation_id", "correlation"),
        )
        for metadata_key, identity_name in identities:
            identity = metadata.get(metadata_key)
            if identity is None:
                failures.append(
                    f"{path.relative_to(ROOT)} lacks {identity_name} identity"
                )
                continue
            try:
                if str(UUID(identity)) != identity:
                    raise ValueError
            except (ValueError, AttributeError):
                failures.append(
                    f"{path.relative_to(ROOT)} has a non-canonical "
                    f"{identity_name} UUID"
                )

        if vector["kind"] == "request":
            expected_capability = f"plenora.{component.removeprefix('plenora-')}"
            if metadata.get("plenora.capability.name") != expected_capability:
                failures.append(f"{path.relative_to(ROOT)} has wrong capability name")
            if metadata.get("plenora.capability.version") != "1":
                failures.append(
                    f"{path.relative_to(ROOT)} has wrong capability version"
                )
            if metadata.get("plenora.input.contract") != operation["input"]["contract"]:
                failures.append(f"{path.relative_to(ROOT)} has wrong input contract")
            if vector["content_type"] not in operation["input"]["content_types"]:
                failures.append(
                    f"{path.relative_to(ROOT)} has unsupported input content type"
                )
            if (
                "plenora.execution.deadline" in metadata
                and not operation["controls"]["deadline"]
            ):
                failures.append(
                    f"{path.relative_to(ROOT)} uses an unsupported deadline"
                )
            if (
                "plenora.execution.idempotency_key" in metadata
                and not operation["controls"]["idempotency_key"]
            ):
                failures.append(
                    f"{path.relative_to(ROOT)} uses an unsupported idempotency key (RT-006)"
                )

        if vector["kind"] == "success":
            if (
                metadata.get("plenora.output.contract")
                != operation["output"]["contract"]
            ):
                failures.append(f"{path.relative_to(ROOT)} has wrong output contract")
            if vector["content_type"] not in operation["output"]["content_types"]:
                failures.append(
                    f"{path.relative_to(ROOT)} has unsupported output content type"
                )

        if vector["kind"] == "error":
            if vector["content_type"] != "application/vnd.plenora.error+json":
                failures.append(
                    f"{path.relative_to(ROOT)} has wrong error content type"
                )
            if metadata.get("plenora.output.contract") != "plenora-error-v1":
                failures.append(f"{path.relative_to(ROOT)} has wrong error contract")
            errors = instance_errors(
                schemas["error-v1.schema.json"], vector["payload"], registry
            )
            if errors:
                failures.append(
                    f"{path.relative_to(ROOT)} has invalid typed error: {errors[0]}"
                )
            bound_errors = error_bound_errors(vector["payload"])
            if bound_errors:
                failures.append(
                    f"{path.relative_to(ROOT)} has unbounded error: {bound_errors[0]}"
                )
            if (
                vector["payload"].get("retry", {}).get("kind") == "requires_idempotency_key"
                and not operation["controls"]["idempotency_key"]
            ):
                failures.append(
                    f"{path.relative_to(ROOT)} requires an idempotency key the operation "
                    "does not accept (ERR-008)"
                )
        if (operation_id, operation["version"]) == ("data.run", 3):
            data_run_3_coverage.add(vector["kind"])
            if vector["kind"] == "error":
                data_run_3_coverage.add(f"error:{vector['payload'].get('remote_effect')}")
            data_run_3_vectors.append(vector)
            errors = data_run_3_vector_errors(vector, schemas, registry)
            if vector["kind"] == "request":
                errors.extend(data_run_3_text_errors(read_text(path)))
            if errors:
                failures.append(
                    f"{path.relative_to(ROOT)} violates data.run 3 semantics: {errors[0]}"
                )
        if component == STORAGE_COMPONENT:
            storage_coverage.add((operation_id, vector["kind"]))
            errors = storage_vector_errors(vector, operation)
            if errors:
                failures.append(
                    f"{path.relative_to(ROOT)} violates storage runtime semantics: {errors[0]}"
                )
    required_storage = {(operation, "request") for operation in STORAGE_OPERATIONS}
    required_storage.update({
        ("storage.list", "success"), ("storage.get", "success"),
        ("storage.put", "success"), ("storage.get", "error"), ("storage.put", "error"),
    })
    missing_storage = required_storage - storage_coverage
    if missing_storage:
        failures.append(f"storage runtime vector coverage is incomplete: {sorted(missing_storage)}")
    missing_run = {
        "request", "success", "error", "error:partial", "error:unknown"
    } - data_run_3_coverage
    if missing_run:
        failures.append(f"data.run 3 runtime vector coverage is incomplete: {sorted(missing_run)}")
    failures.extend(data_run_3_manifest_errors(data_run_3_vectors))
    failures.extend(data_run_3_error_location_errors(data_run_3_vectors))
    return failures


def data_run_3_error_location_errors(vectors: list[dict[str, Any]]) -> list[str]:
    """No error carries a path or a reference location (DT-RUN-008); the plan
    names of the request with the same correlation are the caller's data and
    may appear as given."""
    plans = {
        vector["metadata"]["plenora.trace.correlation_id"]: vector["payload"].get("plan", {})
        for vector in vectors
        if vector["kind"] == "request"
    }
    failures: list[str] = []
    for vector in vectors:
        if vector["kind"] != "error":
            continue
        plan = plans.get(vector["metadata"]["plenora.trace.correlation_id"], {})
        names = frozenset(
            list(plan.get("inputs", []))
            + list(plan.get("outputs", []))
            + [step.get("out") for step in plan.get("steps", []) if isinstance(step.get("out"), str)]
        )
        payload = vector["payload"]
        texts = [key for key, _ in nested_items(payload)] + list(artifact_strings(payload))
        if any(contains_location(text, names) for text in texts):
            failures.append(
                "a data.run 3 error carries a path or a reference location (DT-RUN-008)"
            )
    return failures


def data_run_3_text_errors(text: str) -> list[str]:
    """The written request text: the plan inside it follows DPLAN-002 (no
    repeated key) and DPLAN-003 (exact numbers) like a plan document."""
    problems: list[str] = []

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        keys = [key for key, _ in pairs]
        if len(keys) != len(set(keys)):
            problems.append("a request object repeats a key (DPLAN-002)")
        return dict(pairs)

    json.loads(text, object_pairs_hook=unique)
    return problems + data_plan_number_errors(text)


def data_run_3_manifest_errors(vectors: list[dict[str, Any]]) -> list[str]:
    """A success vector is the manifest of the request with its correlation:
    every plan output in plan order with its sink reference and content type,
    and one step count per plan step, in plan order (DT-RUN-005)."""
    failures: list[str] = []
    requests = {
        vector["metadata"]["plenora.trace.correlation_id"]: vector["payload"]
        for vector in vectors
        if vector["kind"] == "request"
    }
    for vector in vectors:
        if vector["kind"] != "success":
            continue
        request = requests.get(vector["metadata"]["plenora.trace.correlation_id"])
        if request is None:
            failures.append("a data.run 3 success has no request with its correlation")
            continue
        plan = request["plan"]
        outputs = vector["payload"].get("outputs", [])
        expected = [
            (name, request["outputs"][name]["reference"], request["outputs"][name]["content_type"])
            for name in plan["outputs"]
            if name in request["outputs"]
        ]
        found = [
            (item.get("name"), item.get("reference"), item.get("artifact", {}).get("content_type"))
            for item in outputs
        ]
        if found != expected:
            failures.append(
                "a data.run 3 manifest differs from the plan outputs and sinks of its request (DT-RUN-005)"
            )
        steps = [(item.get("out"), item.get("op")) for item in vector["payload"].get("steps", [])]
        if steps != [(step["out"], step["op"]) for step in plan["steps"]]:
            failures.append(
                "a data.run 3 manifest differs from the plan steps of its request (DT-RUN-005)"
            )
    return failures


# Free text may name locations; a fixture guard, not a proof of redaction.
# A token is a location when it is an absolute or drive path, a UNC or
# `file:` path, a URI other than a public http(s) link, or a relative path
# whose last segment has an extension. `/` alone, `and/or` or a link to
# public documentation are not.
TOKEN_SEPARATORS = re.compile(r"[\s\"'`(),;<>\[\]{}=|*]+")
# Anywhere in the token: quoting or punctuation must not hide a reference.
URI_SCHEME = re.compile(r"([a-z][a-z0-9+.-]*)://", re.IGNORECASE)
RELATIVE_FILE = re.compile(r"[\\/][^\\/]*\.[A-Za-z0-9]{1,8}$")


# A public http(s) link, removed from the text before the tokens are read:
# what is left around it is still checked.
PUBLIC_LINK = re.compile(r"https?://[^\s\"'`<>|*:]*?(?=[.,;!?]*(?:[\s\"'`<>|*:]|$))", re.IGNORECASE)


def token_is_location(token: str) -> bool:
    token = token.rstrip(".:!?")
    if len(token) < 2:
        return False
    if URI_SCHEME.search(token) is not None:
        return True
    # A prefix such as `path:` must not hide what follows it.
    return any(
        is_local_path(part)
        or (part[:1] == "/" and len(part) > 1)
        or RELATIVE_FILE.search(part) is not None
        for part in [token, *token.split(":")[1:]]
        if part
    ) or is_local_path(token)


def contains_location(value: str, names: frozenset[str] = frozenset()) -> bool:
    """`names` are the caller's plan names: data, not locations (DT-RUN-008).

    Whole occurrences of the names (longest first) and public http(s) links
    are removed before the text is split into tokens, so a name with spaces
    or separators stays exempt and nothing else hides behind it or a link."""
    for name in sorted(names, key=len, reverse=True):
        value = value.replace(name, " ")
    value = PUBLIC_LINK.sub(" ", value)
    return any(token_is_location(token) for token in TOKEN_SEPARATORS.split(value))


def data_run_3_vector_errors(
    vector: dict[str, Any],
    schemas: dict[str, dict[str, Any]],
    registry: Registry,
) -> list[str]:
    """Payload semantics of a `data.run` 3 vector (profile v2, DT-RUN-*)."""
    payload = vector["payload"]
    if vector["kind"] == "request":
        errors = instance_errors(schemas["data-execution-input-v3.schema.json"], payload, registry)
        if errors:
            return [errors[0]]
        plan = payload["plan"]
        registries = data_registries()
        kernel_ids = {item["id"] for item in registries[max(registries)]["operations"]}
        errors = data_plan_errors(plan, kernel_ids)
        if set(payload["inputs"]) != set(plan["inputs"]):
            errors.append("sources do not name exactly the plan inputs (DT-RUN-001)")
        if set(payload["outputs"]) != set(plan["outputs"]):
            errors.append("sinks do not name exactly the plan outputs (DT-RUN-001)")
        references = [
            item["reference"]
            for group in ("inputs", "outputs")
            for item in payload[group].values()
        ]
        if any(is_local_path(reference) for reference in references):
            errors.append("an artifact reference is a private local path (DT-RUN-002)")
        sinks = [item["reference"] for item in payload["outputs"].values()]
        if len(set(sinks)) != len(sinks):
            errors.append("two sinks share one artifact reference (DT-RUN-002)")
        return errors
    if vector["kind"] == "success":
        errors = instance_errors(schemas["data-execution-result-v3.schema.json"], payload, registry)
        if errors:
            return [errors[0]]
        names = [item["name"] for item in payload["outputs"]]
        references = [item["reference"] for item in payload["outputs"]]
        if len(set(names)) != len(names) or len(set(references)) != len(references):
            return ["outputs repeat a name or an artifact reference (DT-RUN-005)"]
        if any(is_local_path(reference) for reference in references):
            return ["an artifact reference is a private local path (DT-RUN-002)"]
        return []
    errors = []
    if payload.get("remote_effect") == "partial" and payload.get("retry", {}).get("kind") not in {
        "never", "quarantine", "requires_recovery"
    }:
        errors.append("a partial publication must forbid automatic retry (DT-RUN-006)")
    if payload.get("remote_effect") == "unknown" and payload.get("retry", {}).get("kind") != "requires_recovery":
        errors.append("an unknown publication outcome must require recovery (DT-RUN-006)")
    return errors


PLAN_BUDGET_CONFORMING = (
    "examples/valid/plan-budget-v6.json",
    "examples/valid/plan-budget-v6-absent.json",
    "examples/valid/plan-budget-v5.json",
)

# Documenti che il JSON Schema ACCETTA e che il contratto rifiuta. Senza
# almeno uno, `plan_budget_errors` potrebbe essere cancellata o invertita e la
# suite resterebbe verde: visitare solo esempi gia' coerenti non prova nulla.
PLAN_BUDGET_VIOLATING = ("examples/invalid/plan-budget-domain-below-governed.json",)


def plan_budget_errors(document: dict[str, Any]) -> list[str]:
    """PLAN-011: the domain ceiling is at least the governed budget.

    JSON Schema cannot compare two sibling values, so the schema stops at
    shape. Only the case where the document declares BOTH is checkable here:
    when the governed budget is omitted the comparison is against a component
    default this repository does not own, and the contract says so.
    """
    limits = document.get("limits", {})
    domain = limits.get("max_domain_memory_bytes")
    governed = limits.get("max_governed_memory_bytes")
    if domain is None or governed is None:
        return []
    if domain < governed:
        return [
            f"max_domain_memory_bytes {domain} is below "
            f"max_governed_memory_bytes {governed} (PLAN-011)"
        ]
    return []


def validate_plan_budget(
    schemas: dict[str, dict[str, Any]], registry: Registry
) -> list[str]:
    failures: list[str] = []
    schema = schemas["plan-budget-v1.schema.json"]
    for relative in PLAN_BUDGET_CONFORMING:
        for problem in plan_budget_errors(load_json(ROOT / relative)):
            failures.append(f"{relative} {problem}")
    for relative in PLAN_BUDGET_VIOLATING:
        document = load_json(ROOT / relative)
        # Deve passare lo SCHEMA: se fallisse li', non proverebbe che il
        # controllo semantico serve — proverebbe solo che lo schema funziona.
        shape = instance_errors(schema, document, registry)
        if shape:
            failures.append(
                f"{relative} must be accepted by the schema so that it probes "
                f"the semantic check, but the schema rejected it: {shape[0]}"
            )
        if not plan_budget_errors(document):
            failures.append(f"{relative} must be rejected by PLAN-011")
    return failures


DATA_PLAN_CONFORMING = (
    "examples/valid/data-plan-v1.json",
    "examples/valid/data-plan-v1-geo.json",
    "examples/valid/data-plan-v1-identity.json",
)

# Accettati dallo SCHEMA e rifiutati dal contratto (DPLAN-004..006): senza,
# `data_plan_errors` potrebbe sparire e la suite resterebbe verde.
DATA_PLAN_VIOLATING = (
    "examples/invalid/data-plan-v1-forward-reference.json",
    "examples/invalid/data-plan-v1-redefined-name.json",
    "examples/invalid/data-plan-v1-unknown-kernel.json",
)


DATA_PLAN_NUMBER_VIOLATING = ("examples/invalid/data-plan-v1-inexact-number.json",)


def data_plan_number_errors(text: str) -> list[str]:
    """DPLAN-003 on the written text: integers within i64/u64, every other
    number equal to the shortest decimal of the binary64 it reads as."""
    import decimal

    problems: list[str] = []

    def integer(token: str) -> int:
        value = int(token)
        if not -(2**63) <= value <= 2**64 - 1:
            problems.append(f"integer {token} outside i64/u64 (DPLAN-003)")
        return value

    def number(token: str) -> decimal.Decimal:
        written = decimal.Decimal(token)
        nearest = float(token)
        if nearest in (float("inf"), float("-inf")) or decimal.Decimal(repr(nearest)) != written:
            problems.append(f"number {token} is not exactly a binary64 shortest decimal (DPLAN-003)")
        return written

    def constant(name: str) -> None:
        problems.append(f"{name} is not a JSON number (DPLAN-003)")

    json.loads(text, parse_int=integer, parse_float=number, parse_constant=constant)
    return problems


def data_plan_errors(document: dict[str, Any], kernel_ids: set[str]) -> list[str]:
    """DPLAN-004, DPLAN-005 and the registry part of DPLAN-006."""
    problems: list[str] = []
    defined: set[str] = set()
    for name in document.get("inputs", []):
        if name in defined:
            problems.append(f"name {name} defined twice (DPLAN-004)")
        defined.add(name)
    for position, step in enumerate(document.get("steps", [])):
        for name in step["in"]:
            if name not in defined:
                problems.append(f"step {position} reads undefined name {name} (DPLAN-005)")
        if step["op"] not in kernel_ids:
            problems.append(f"step {position} names unknown kernel {step['op']} (DPLAN-006)")
        if step["out"] in defined:
            problems.append(f"name {step['out']} defined twice (DPLAN-004)")
        defined.add(step["out"])
    for name in document.get("outputs", []):
        if name not in defined:
            problems.append(f"output {name} is not defined (DPLAN-005)")
    return problems


def validate_data_plan(
    schemas: dict[str, dict[str, Any]], registry: Registry
) -> list[str]:
    failures: list[str] = []
    schema = schemas["data-plan-v1.schema.json"]
    registries = data_registries()
    kernel_ids = {item["id"] for item in registries[max(registries)]["operations"]}
    for relative in DATA_PLAN_CONFORMING:
        for problem in data_plan_errors(load_json(ROOT / relative), kernel_ids):
            failures.append(f"{relative} {problem}")
        for problem in data_plan_number_errors((ROOT / relative).read_text(encoding="utf-8")):
            failures.append(f"{relative} {problem}")
    for relative in DATA_PLAN_NUMBER_VIOLATING:
        text = (ROOT / relative).read_text(encoding="utf-8")
        shape = instance_errors(schema, json.loads(text), registry)
        if shape or data_plan_errors(json.loads(text), kernel_ids):
            failures.append(f"{relative} must differ from a valid plan only by DPLAN-003")
        if not data_plan_number_errors(text):
            failures.append(f"{relative} must be rejected by DPLAN-003")
    for relative in DATA_PLAN_VIOLATING:
        document = load_json(ROOT / relative)
        shape = instance_errors(schema, document, registry)
        if shape:
            failures.append(
                f"{relative} must be accepted by the schema so that it probes "
                f"the semantic check, but the schema rejected it: {shape[0]}"
            )
        if not data_plan_errors(document, kernel_ids):
            failures.append(f"{relative} must be rejected by DPLAN-004..006")
    return failures


def validate_markdown_links() -> list[str]:
    failures: list[str] = []
    for document in ROOT.rglob("*.md"):
        text = document.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            if target.startswith(("http://", "https://", "#")):
                continue
            relative_target = target.split("#", 1)[0]
            if relative_target and not (document.parent / relative_target).exists():
                failures.append(
                    f"{document.relative_to(ROOT)} links to missing {target}"
                )
    return failures


def main() -> int:
    inventory_errors = validate_example_inventory()
    if inventory_errors:
        for error in inventory_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    schemas = {
        path.name: load_json(path) for path in sorted(SCHEMA_DIR.glob("*.schema.json"))
    }
    if set(schemas) != EXPECTED_SCHEMAS:
        print("schema inventory differs from the validation contract", file=sys.stderr)
        return 1

    for name, schema in schemas.items():
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as error:
            print(f"invalid schema {name}: {error}", file=sys.stderr)
            return 1

    registry = schema_registry(schemas)
    catalogs = load_catalogs()
    failures = validate_examples(schemas, registry)
    failures.extend(validate_public_semantics(schemas, registry))
    failures.extend(validate_error_bound_vectors(schemas, registry))
    failures.extend(validate_machine_documents(schemas, registry))
    failures.extend(validate_catalog_semantics(catalogs))
    failures.extend(validate_rest_examples(schemas, registry, catalogs[REST_COMPONENT]))
    failures.extend(validate_bindings(catalogs))
    failures.extend(validate_composition(catalogs))
    failures.extend(validate_arrow_vectors())
    failures.extend(validate_runtime_vectors(catalogs, schemas, registry))
    failures.extend(validate_plan_budget(schemas, registry))
    failures.extend(validate_data_plan(schemas, registry))
    failures.extend(validate_markdown_links())
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    valid_count = sum(len(paths) for paths in CASES["valid"].values())
    invalid_count = sum(len(paths) for paths in CASES["invalid"].values())
    vector_count = len(list((ROOT / "vectors").glob("**/*.json")))
    composition_count = len(load_json(ROOT / "composition/pipelines-v1.json")["edges"])
    print(
        f"validated {len(schemas)} schemas, {valid_count} valid examples, "
        f"{invalid_count} schema-rejected examples, "
        f"{len(PUBLIC_SEMANTIC_CASES)} public semantic counterexamples, 7 semantic error-bound probes, "
        f"{sum(len(item) for item in load_catalog_versions().values())} public catalogs, "
        f"3 binding maps, {composition_count} composition edges and "
        f"{vector_count} conformance vectors"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
