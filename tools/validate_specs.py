from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"

EXPECTED_SCHEMAS = {
    "adoption-manifest-v1.schema.json",
    "adoption-manifest-v2.schema.json",
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
        "capabilities-v2.schema.json": ["examples/valid/capabilities-v2.json"],
        "row-diagnostics-v1.schema.json": ["examples/valid/row-diagnostics.json"],
        "adoption-manifest-v1.schema.json": ["examples/valid/adoption-manifest.json"],
        "adoption-manifest-v2.schema.json": ["examples/valid/adoption-manifest-v2.json"],
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
    },
}

COMPONENTS = {
    "plenora-database-tools",
    "plenora-data-tools",
    "plenora-io-tools",
    "plenora-rest-tools",
    "plenora-storage-tools",
}

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
    "plenora-data-tools": {"data.catalog", "data.describe", "data.validate", "data.run"},
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
        for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
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


def validate_machine_documents(
    schemas: dict[str, dict[str, Any]], registry: Registry
) -> list[str]:
    groups = {
        "public-catalog-v1.schema.json": sorted((ROOT / "catalogs").glob("*-tools-v1.json")),
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


def validate_catalog_semantics(
    catalogs: dict[str, dict[str, Any]]
) -> list[str]:
    failures: list[str] = []
    if set(catalogs) != COMPONENTS:
        failures.append("public catalog component inventory differs from the five-library contract")
        return failures

    for component, catalog in catalogs.items():
        profile_path = ROOT / "profiles" / f"{component.removeprefix('plenora-')}.md"
        if not profile_path.exists():
            failures.append(f"{component} has no profile document")
        elif f"Profile identifier: `{catalog['profile']}`" not in profile_path.read_text(
            encoding="utf-8"
        ):
            failures.append(f"{component} profile identifier does not match its catalog")

        identities = [(item["id"], item["version"]) for item in catalog["operations"]]
        if len(identities) != len(set(identities)):
            failures.append(f"{component} has duplicate operation identities")

        required = {
            item["id"] for item in catalog["operations"] if item["requirement"] == "required"
        }
        missing = REQUIRED_OPERATIONS[component] - required
        if missing:
            failures.append(f"{component} is missing required operations: {sorted(missing)}")

        for operation in catalog["operations"]:
            for surface in operation["surfaces"]:
                applicability = catalog["target_surfaces"][surface]
                if applicability in {"not_applicable", "undecided"}:
                    failures.append(
                        f"{component} {operation['id']} lists inapplicable surface {surface}"
                    )

    storage = catalogs["plenora-storage-tools"]
    if storage["status"] != "provisional" or storage["operations"]:
        failures.append("storage-tools v1 must remain provisional and empty until reviewed")

    registry = load_json(ROOT / "catalogs/data-kernels-v1.json")
    kernel_ids = [item["id"] for item in registry["operations"]]
    if len(kernel_ids) != 146 or len(set(kernel_ids)) != 146:
        failures.append("data kernel registry must contain 146 unique operation identities")
    for item in registry["operations"]:
        if item["id"].split(".", 1)[0] != item["family"]:
            failures.append(f"data kernel {item['id']} has an inconsistent family")
    return failures


def validate_bindings(
    catalogs: dict[str, dict[str, Any]]
) -> list[str]:
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
            failures.append(f"{path.name} must contain all five components exactly once")
            continue

        actual: set[tuple[str, str, int]] = set()
        for component, section in components.items():
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
                    expected = f"{capability}#{binding['operation']}@{binding['version']}"
                    if binding["entrypoints"] != [expected]:
                        failures.append(
                            f"{path.name} has a non-canonical runtime selector for {binding['operation']}"
                        )

            if len(entrypoints) != len(set(entrypoints)):
                failures.append(f"{path.name} has duplicate entrypoints for {component}")
            if section["artifact"] is not None and not section["discovery"]:
                failures.append(f"{path.name} lacks discovery entrypoints for {component}")

        expected = {
            key for key, operation in index.items() if surface in operation["surfaces"]
        }
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            failures.append(
                f"{path.name} binding coverage differs; missing={missing}, extra={extra}"
            )
    return failures


def validate_composition(
    catalogs: dict[str, dict[str, Any]]
) -> list[str]:
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
            failures.append(f"composition edge {position} refers to an unknown operation")
            continue
        if edge["mode"] != "direct":
            continue
        interchange = edge["interchange_contract"]
        content_type = edge["content_type"]
        if interchange not in source["output"]["interchange_contracts"]:
            failures.append(f"composition edge {position} source lacks {interchange}")
        if interchange not in target["input"]["interchange_contracts"]:
            failures.append(f"composition edge {position} target lacks {interchange}")
        if content_type not in source["output"]["content_types"]:
            failures.append(f"composition edge {position} source lacks {content_type}")
        if content_type not in target["input"]["content_types"]:
            failures.append(f"composition edge {position} target lacks {content_type}")
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
        "plenora.geometry.crs_resolution": {"resolved", "declared_unresolved", "missing"},
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
                errors.append(f"{field['name']} has geometry metadata without geoarrow.wkb")
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
                    errors.append(f"{field['name']} geometry types are not unique and ordered")

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
            failures.append(f"{path.relative_to(ROOT)} must be semantically valid: {errors[0]}")
        if vector["expect"] == "invalid" and not errors:
            failures.append(f"{path.relative_to(ROOT)} must contain a semantic violation")
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
                failures.append(f"runtime vector lookup has duplicate operation {operation['id']}")
            operations[operation["id"]] = (component, operation)

    for path in sorted((ROOT / "vectors/runtime-v1").glob("*.json")):
        vector = load_json(path)
        metadata = vector["metadata"]
        operation_id = metadata.get("plenora.capability.operation")
        resolved = operations.get(operation_id)
        if resolved is None:
            failures.append(f"{path.relative_to(ROOT)} refers to unknown operation {operation_id}")
            continue
        component, operation = resolved
        if metadata.get("plenora.operation.version") != str(operation["version"]):
            failures.append(f"{path.relative_to(ROOT)} has wrong operation version")
        if "plenora.message.correlation_id" not in metadata:
            failures.append(f"{path.relative_to(ROOT)} lacks correlation identity")

        if vector["kind"] == "request":
            expected_capability = f"plenora.{component.removeprefix('plenora-')}"
            if metadata.get("plenora.capability.name") != expected_capability:
                failures.append(f"{path.relative_to(ROOT)} has wrong capability name")
            if metadata.get("plenora.capability.version") != "1":
                failures.append(f"{path.relative_to(ROOT)} has wrong capability version")
            if metadata.get("plenora.input.contract") != operation["input"]["contract"]:
                failures.append(f"{path.relative_to(ROOT)} has wrong input contract")
            if vector["content_type"] not in operation["input"]["content_types"]:
                failures.append(f"{path.relative_to(ROOT)} has unsupported input content type")
            if (
                "plenora.execution.deadline" in metadata
                and not operation["controls"]["deadline"]
            ):
                failures.append(f"{path.relative_to(ROOT)} uses an unsupported deadline")

        if vector["kind"] == "success":
            if metadata.get("plenora.output.contract") != operation["output"]["contract"]:
                failures.append(f"{path.relative_to(ROOT)} has wrong output contract")
            if vector["content_type"] not in operation["output"]["content_types"]:
                failures.append(f"{path.relative_to(ROOT)} has unsupported output content type")

        if vector["kind"] == "error":
            if vector["content_type"] != "application/vnd.plenora.error+json":
                failures.append(f"{path.relative_to(ROOT)} has wrong error content type")
            if metadata.get("plenora.output.contract") != "plenora-error-v1":
                failures.append(f"{path.relative_to(ROOT)} has wrong error contract")
            errors = instance_errors(schemas["error-v1.schema.json"], vector["payload"], registry)
            if errors:
                failures.append(f"{path.relative_to(ROOT)} has invalid typed error: {errors[0]}")
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
                failures.append(f"{document.relative_to(ROOT)} links to missing {target}")
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
    failures.extend(validate_machine_documents(schemas, registry))
    failures.extend(validate_catalog_semantics(catalogs))
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
        f"{invalid_count} rejected examples, {len(catalogs)} public catalogs, "
        f"3 binding maps, {composition_count} composition edges and "
        f"{vector_count} conformance vectors"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
