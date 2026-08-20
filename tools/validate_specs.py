from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

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
    "error-v1.schema.json",
    "operation-registry-v1.schema.json",
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
    },
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
    "plenora-storage-tools": set(),
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


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


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
                errors = instance_errors(
                    schemas[schema_name], load_json(ROOT / relative_path), registry
                )
                if expectation == "valid" and errors:
                    failures.append(f"{relative_path} must validate: {errors[0]}")
                if expectation == "invalid" and not errors:
                    failures.append(f"{relative_path} must be rejected")
    return failures


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
    cases = {
        "examples/valid/error-details-bounded.json": False,
        "examples/invalid/error-details-too-deep.json": True,
    }
    for relative_path, must_violate in cases.items():
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
            (ROOT / "catalogs").glob("*-tools-v1.json")
        ),
        "operation-registry-v1.schema.json": [ROOT / "catalogs/data-kernels-v1.json"],
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


def load_catalogs() -> dict[str, dict[str, Any]]:
    catalogs: dict[str, dict[str, Any]] = {}
    for path in sorted((ROOT / "catalogs").glob("*-tools-v1.json")):
        document = load_json(path)
        catalogs[document["component"]] = document
    return catalogs


def operation_index(
    catalogs: dict[str, dict[str, Any]],
) -> dict[tuple[str, str, int], dict[str, Any]]:
    return {
        (component, operation["id"], operation["version"]): operation
        for component, catalog in catalogs.items()
        for operation in catalog["operations"]
    }


def validate_catalog_semantics(catalogs: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    if set(catalogs) != COMPONENTS:
        failures.append(
            "public catalog component inventory differs from the five-library contract"
        )
        return failures

    for component, catalog in catalogs.items():
        profile_path = ROOT / "profiles" / f"{component.removeprefix('plenora-')}.md"
        if not profile_path.exists():
            failures.append(f"{component} has no profile document")
        elif (
            f"Profile identifier: `{catalog['profile']}`"
            not in profile_path.read_text(encoding="utf-8")
        ):
            failures.append(
                f"{component} profile identifier does not match its catalog"
            )

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

            rest_operations = {item["id"]: item for item in catalog["operations"]}
            for operation in rest_operations.values():
                attributes = operation.get("attributes")
                if (
                    not isinstance(attributes, dict)
                    or attributes.get("contract") != REST_ATTRIBUTE_CONTRACT
                ):
                    failures.append(
                        f"rest-tools {operation['id']} lacks its capability attributes contract"
                    )

            download = rest_operations.get("rest.download")
            upload = rest_operations.get("rest.upload")
            if download is not None and upload is not None:
                if download["input"]["contract"] != upload["input"]["contract"]:
                    failures.append(
                        "REST download and upload use different transfer inputs"
                    )
                if download["input"]["contract"] != REST_FILE_TRANSFER_INPUT:
                    failures.append(
                        "REST file transfer operations use the wrong input contract"
                    )
                if download["side_effect"] != "remote":
                    failures.append(
                        "REST download must use the conservative remote side-effect class"
                    )
                if "application/octet-stream" in upload["input"]["content_types"]:
                    failures.append(
                        "REST upload v1 embeds raw bytes in its JSON invocation envelope"
                    )

        if component == DATABASE_COMPONENT:
            database_operations = {
                item["id"]: item for item in catalog["operations"]
            }
            if catalog["status"] != "provisional":
                failures.append(
                    "database-tools must remain provisional until its component-owned schemas exist"
                )
            if any(name.startswith("arcgis.") for name in database_operations):
                failures.append(
                    "database-tools must not own ArcGIS operations before ownership is ratified"
                )
            write = database_operations.get("database.write")
            if write is not None:
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
            query = database_operations.get("database.query")
            if query is not None and query["side_effect"] != "none":
                failures.append("database.query must remain read-only")
            execute = database_operations.get("database.execute")
            if execute is not None and execute["side_effect"] != "remote":
                failures.append("database.execute must declare remote side effects")

    storage = catalogs["plenora-storage-tools"]
    if storage["status"] != "provisional" or storage["operations"]:
        failures.append(
            "storage-tools v1 must remain provisional and empty until reviewed"
        )

    registry = load_json(ROOT / "catalogs/data-kernels-v1.json")
    kernel_ids = [item["id"] for item in registry["operations"]]
    if len(kernel_ids) != 146 or len(set(kernel_ids)) != 146:
        failures.append(
            "data kernel registry must contain 146 unique operation identities"
        )
    for item in registry["operations"]:
        if item["id"].split(".", 1)[0] != item["family"]:
            failures.append(f"data kernel {item['id']} has an inconsistent family")
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
        for component, section in components.items():
            applicability = catalogs[component]["target_surfaces"][surface]
            if applicability == "required" and section["artifact"] is None:
                failures.append(f"{path.name} lacks the required {component} artifact")
            if applicability in {"not_applicable", "undecided"} and any(
                (
                    section["artifact"] is not None,
                    section["discovery"],
                    section["bindings"],
                )
            ):
                failures.append(
                    f"{path.name} exposes {component} despite target applicability {applicability}"
                )
            entrypoints: list[str] = []
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
                entrypoints.extend(binding["entrypoints"])

                if surface == "runtime":
                    capability = f"plenora.{component.removeprefix('plenora-')}"
                    expected = (
                        f"{capability}#{binding['operation']}@{binding['version']}"
                    )
                    if binding["entrypoints"] != [expected]:
                        failures.append(
                            f"{path.name} has a non-canonical runtime selector for {binding['operation']}"
                        )

            if len(entrypoints) != len(set(entrypoints)):
                failures.append(
                    f"{path.name} has duplicate entrypoints for {component}"
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
        item
        for item in python_document["components"]
        if item["component"] == DATABASE_COMPONENT
    )
    database_bindings = {
        item["operation"]: set(item["entrypoints"])
        for item in database_section["bindings"]
    }
    if database_bindings.get("database.test_connection") != {
        "plenora_database.test_connection",
        "plenora_database.atest_connection",
    }:
        failures.append(
            "database.test_connection must use dedicated SDK verification entrypoints"
        )
    if database_bindings.get("database.query") != {
        "Session.select",
        "AsyncSession.select",
    }:
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
    if not mutating_entrypoints.issubset(
        database_bindings.get("database.execute", set())
    ):
        failures.append(
            "mutating database SDK entrypoints must bind to database.execute"
        )
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
    operations = {item["id"]: item for item in catalog["operations"]}
    operation = operations.get(document.get("operation"))
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
    capability_cases = {
        "examples/valid/capabilities-rest-v2.json": None,
        "examples/invalid/rest-capabilities-attributes-missing-contract.json": "attribute contract ID",
    }
    for relative_path, expected_error in capability_cases.items():
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

    boundary_cases = {
        "examples/valid/rest-runtime-artifact-request.json": None,
        "examples/invalid/rest-runtime-artifact-local-path.json": "private local path",
        "examples/invalid/rest-runtime-artifact-relative-path.json": "private local path",
        "examples/invalid/rest-download-artifact-source-only.json": "forbids artifact_source",
        "examples/invalid/rest-upload-artifact-sink-only.json": "forbids artifact_sink",
        "examples/invalid/rest-runtime-upload-inline-credentials.json": "inline credential",
        "examples/invalid/rest-download-local-mutating-method.json": "mutating REST download",
    }
    for relative_path, expected_error in boundary_cases.items():
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


def validate_runtime_vectors(
    catalogs: dict[str, dict[str, Any]],
    schemas: dict[str, dict[str, Any]],
    registry: Registry,
) -> list[str]:
    failures: list[str] = []
    operations: dict[str, tuple[str, dict[str, Any]]] = {}
    for component, catalog in catalogs.items():
        for operation in catalog["operations"]:
            if operation["id"] in operations:
                failures.append(
                    f"runtime vector lookup has duplicate operation {operation['id']}"
                )
            operations[operation["id"]] = (component, operation)

    for path in sorted((ROOT / "vectors/runtime-v1").glob("*.json")):
        vector = load_json(path)
        metadata = vector["metadata"]
        operation_id = metadata.get("plenora.capability.operation")
        resolved = operations.get(operation_id)
        if resolved is None:
            failures.append(
                f"{path.relative_to(ROOT)} refers to unknown operation {operation_id}"
            )
            continue
        component, operation = resolved
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
    failures.extend(validate_error_bound_vectors(schemas, registry))
    failures.extend(validate_machine_documents(schemas, registry))
    failures.extend(validate_catalog_semantics(catalogs))
    failures.extend(validate_rest_examples(schemas, registry, catalogs[REST_COMPONENT]))
    failures.extend(validate_bindings(catalogs))
    failures.extend(validate_composition(catalogs))
    failures.extend(validate_arrow_vectors())
    failures.extend(validate_runtime_vectors(catalogs, schemas, registry))
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
        f"{invalid_count} schema-rejected examples, 7 semantic error-bound probes, "
        f"{len(catalogs)} public catalogs, "
        f"3 binding maps, {composition_count} composition edges and "
        f"{vector_count} conformance vectors"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
