#!/usr/bin/env python3
"""Genera il corpus di conformità della catena.

Il corpus è prodotto con PyArrow e non con i componenti che deve verificare:
un writer e un reader difettosi nello stesso modo si annullerebbero, e il test
passerebbe. Vedi conformance/README.md.

Ogni caso produce due file:
  <nome>.arrow  il dataset in Arrow IPC, con i metadati canonici di §2
  <nome>.json   il contratto atteso in uscita dalla catena

Solo la standard library e pyarrow.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import pyarrow as pa
import pyarrow.ipc as ipc

CONTRACT_VERSION = "1"

# ---------------------------------------------------------------- WKB


def _wkb_point(x: float, y: float, z: float | None = None, m: float | None = None) -> bytes:
    """Point WKB little-endian, ISO: 1000 = Z, 2000 = M, 3000 = ZM."""
    base = 1
    if z is not None and m is not None:
        code = base + 3000
        coords = (x, y, z, m)
    elif z is not None:
        code = base + 1000
        coords = (x, y, z)
    elif m is not None:
        code = base + 2000
        coords = (x, y, m)
    else:
        code = base
        coords = (x, y)
    return struct.pack("<BI", 1, code) + struct.pack(f"<{len(coords)}d", *coords)


def _wkb_linestring(points: list[tuple[float, float]]) -> bytes:
    body = struct.pack("<BII", 1, 2, len(points))
    for x, y in points:
        body += struct.pack("<2d", x, y)
    return body


def _wkb_multipolygon_zm(rings: list[list[tuple[float, float, float, float]]]) -> bytes:
    """MultiPolygon ZM (3006) con un poligono (3003) e un anello per elemento."""
    out = struct.pack("<BII", 1, 3006, len(rings))
    for ring in rings:
        out += struct.pack("<BIII", 1, 3003, 1, len(ring))
        for x, y, z, m in ring:
            out += struct.pack("<4d", x, y, z, m)
    return out


# ---------------------------------------------------------------- casi


def _geometry_field(name: str, metadata: dict[str, str]) -> pa.Field:
    return pa.field(name, pa.binary(), nullable=True, metadata=metadata)


def _canonical(dimensions: str, **extra: str) -> dict[str, str]:
    keys = {
        "plenora.field_id": "1",
        "plenora.geometry.encoding": "wkb",
        "plenora.geometry.dimensions": dimensions,
        "plenora.geometry.crs_resolution": "resolved",
        "plenora.geometry.crs_id": "OGC:CRS84",
        "plenora.geometry.axis_order": "lon_lat",
        "plenora.geometry.types_declaration": "exact",
        "plenora.geometry.types": "point",
        "plenora.geometry.spatial_semantics": "geometry",
        "plenora.geometry.precision": "float64",
    }
    keys.update(extra)
    return keys


def case_point_z() -> tuple[pa.Table, dict]:
    """Dimensione xyz propagata, byte Z intatti fino all'uscita."""
    geoms = [_wkb_point(9.19, 45.46, 120.5), _wkb_point(12.49, 41.90, 21.0)]
    field = _geometry_field("geometry", _canonical("xyz"))
    table = pa.table(
        {"geometry": pa.array(geoms, type=pa.binary()), "id": pa.array([1, 2], pa.int64())},
        schema=pa.schema([field, pa.field("id", pa.int64())],
                         metadata={"plenora.contract.version": CONTRACT_VERSION}),
    )
    return table, {"dimensions": "xyz", "z_preserved": True, "rule": "R3.3"}


def case_point_zm() -> tuple[pa.Table, dict]:
    """La M sopravvive a tutti e tre gli anelli."""
    geoms = [_wkb_point(9.19, 45.46, 120.5, 3.25), _wkb_point(12.49, 41.90, 21.0, 7.75)]
    field = _geometry_field("geometry", _canonical("xyzm"))
    table = pa.table(
        {"geometry": pa.array(geoms, type=pa.binary()), "id": pa.array([1, 2], pa.int64())},
        schema=pa.schema([field, pa.field("id", pa.int64())],
                         metadata={"plenora.contract.version": CONTRACT_VERSION}),
    )
    return table, {"dimensions": "xyzm", "m_preserved": True, "rule": "R3.3"}


def case_dimensions_unknown() -> tuple[pa.Table, dict]:
    """`unknown` non deve essere degradato a `xy` da nessun anello."""
    geoms = [_wkb_point(9.19, 45.46), _wkb_point(12.49, 41.90)]
    field = _geometry_field("geometry", _canonical("unknown"))
    table = pa.table(
        {"geometry": pa.array(geoms, type=pa.binary()), "id": pa.array([1, 2], pa.int64())},
        schema=pa.schema([field, pa.field("id", pa.int64())],
                         metadata={"plenora.contract.version": CONTRACT_VERSION}),
    )
    return table, {"dimensions": "unknown", "must_not_become": "xy", "rule": "R3.4"}


def case_crs_unresolved() -> tuple[pa.Table, dict]:
    """`declared_unresolved` distinto da `missing`: il CRS c'è, non si risolve."""
    geoms = [_wkb_point(1_500_000.0, 4_900_000.0)]
    meta = _canonical("xy")
    meta["plenora.geometry.crs_resolution"] = "declared_unresolved"
    meta["plenora.geometry.crs_id"] = "EPSG:99999"
    meta.pop("plenora.geometry.axis_order")
    field = _geometry_field("geometry", meta)
    table = pa.table(
        {"geometry": pa.array(geoms, type=pa.binary()), "id": pa.array([1], pa.int64())},
        schema=pa.schema([field, pa.field("id", pa.int64())],
                         metadata={"plenora.contract.version": CONTRACT_VERSION}),
    )
    return table, {"crs_resolution": "declared_unresolved",
                   "must_not_become": "missing", "rule": "R4.1"}


def case_axis_lat_lon() -> tuple[pa.Table, dict]:
    """EPSG:4326 è lat/lon: non deve diventare OGC:CRS84 lon/lat."""
    geoms = [_wkb_point(45.46, 9.19)]  # lat, lon
    meta = _canonical("xy")
    meta["plenora.geometry.crs_id"] = "EPSG:4326"
    meta["plenora.geometry.axis_order"] = "lat_lon"
    field = _geometry_field("geometry", meta)
    table = pa.table(
        {"geometry": pa.array(geoms, type=pa.binary()), "id": pa.array([1], pa.int64())},
        schema=pa.schema([field, pa.field("id", pa.int64())],
                         metadata={"plenora.contract.version": CONTRACT_VERSION}),
    )
    return table, {"crs_id": "EPSG:4326", "axis_order": "lat_lon",
                   "must_not_become": "OGC:CRS84", "rule": "R4.2"}


def case_types_mixed() -> tuple[pa.Table, dict]:
    """`mixed` è una dichiarazione, non ignoranza: non diventa `unresolved`."""
    geoms = [_wkb_point(9.19, 45.46), _wkb_linestring([(9.0, 45.0), (9.5, 45.5)])]
    meta = _canonical("xy")
    meta["plenora.geometry.types_declaration"] = "mixed"
    meta["plenora.geometry.types"] = "point,linestring"
    field = _geometry_field("geometry", meta)
    table = pa.table(
        {"geometry": pa.array(geoms, type=pa.binary()), "id": pa.array([1, 2], pa.int64())},
        schema=pa.schema([field, pa.field("id", pa.int64())],
                         metadata={"plenora.contract.version": CONTRACT_VERSION}),
    )
    return table, {"types_declaration": "mixed",
                   "must_not_become": "unresolved", "rule": "R3.4.1"}


def case_int64_beyond_2_53() -> tuple[pa.Table, dict]:
    """Interi distinti oltre 2^53: collassano se confrontati come f64."""
    a = (1 << 53) + 1
    b = (1 << 53) + 2
    geoms = [_wkb_point(9.19, 45.46), _wkb_point(12.49, 41.90)]
    table = pa.table(
        {"geometry": pa.array(geoms, type=pa.binary()),
         "asset_id": pa.array([b, a], pa.int64())},
        schema=pa.schema([_geometry_field("geometry", _canonical("xy")),
                          pa.field("asset_id", pa.int64())],
                         metadata={"plenora.contract.version": CONTRACT_VERSION}),
    )
    return table, {"distinct_values": [b, a], "sorted_ascending": [a, b],
                   "rule": "R5.3", "note": "difetto reale trovato in revisione"}


def case_uint64_ordering() -> tuple[pa.Table, dict]:
    """Ordinati per valore: come stringhe darebbero 10 prima di 9."""
    values = [9, 10, 100, 99]
    geoms = [_wkb_point(9.0 + i, 45.0) for i in range(len(values))]
    table = pa.table(
        {"geometry": pa.array(geoms, type=pa.binary()),
         "code": pa.array(values, pa.uint64())},
        schema=pa.schema([_geometry_field("geometry", _canonical("xy")),
                          pa.field("code", pa.uint64())],
                         metadata={"plenora.contract.version": CONTRACT_VERSION}),
    )
    return table, {"sorted_ascending": [9, 10, 99, 100],
                   "rule": "R5.3", "note": "difetto reale trovato in revisione"}


def case_unknown_key() -> tuple[pa.Table, dict]:
    """Chiave non canonica: va propagata invariata da chi non la interpreta."""
    meta = _canonical("xy")
    meta["plenora.filegdb.ogr_field_type"] = "OFTString"
    field = _geometry_field("geometry", meta)
    table = pa.table(
        {"geometry": pa.array([_wkb_point(9.19, 45.46)], type=pa.binary()),
         "id": pa.array([1], pa.int64())},
        schema=pa.schema([field, pa.field("id", pa.int64())],
                         metadata={"plenora.contract.version": CONTRACT_VERSION}),
    )
    return table, {"preserved_key": "plenora.filegdb.ogr_field_type",
                   "expected_value": "OFTString", "rule": "R2.4"}


def case_multipolygon_xyzm_srid() -> tuple[pa.Table, dict]:
    """MultiPolygon ZM con SRID: la geometria composta non va appiattita."""
    ring = [(9.0, 45.0, 100.0, 1.0), (9.1, 45.0, 101.0, 2.0),
            (9.1, 45.1, 102.0, 3.0), (9.0, 45.0, 100.0, 1.0)]
    meta = _canonical("xyzm")
    meta["plenora.geometry.types"] = "multipolygon"
    meta["plenora.geometry.crs_id"] = "EPSG:32632"
    meta["plenora.geometry.srid"] = "32632"
    meta["plenora.geometry.axis_order"] = "easting_northing"
    field = _geometry_field("geometry", meta)
    table = pa.table(
        {"geometry": pa.array([_wkb_multipolygon_zm([ring])], type=pa.binary()),
         "id": pa.array([1], pa.int64())},
        schema=pa.schema([field, pa.field("id", pa.int64())],
                         metadata={"plenora.contract.version": CONTRACT_VERSION}),
    )
    return table, {"dimensions": "xyzm", "srid": "32632", "types": "multipolygon",
                   "rule": "R3.3", "gate_fixture": "exact_multipolygon_xyzm_with_srid"}


def case_crs_missing() -> tuple[pa.Table, dict]:
    """`missing` è l'assenza dichiarata: distinta da `declared_unresolved`."""
    meta = _canonical("xy")
    meta["plenora.geometry.crs_resolution"] = "missing"
    for key in ("plenora.geometry.crs_id", "plenora.geometry.axis_order"):
        meta.pop(key)
    field = _geometry_field("geometry", meta)
    table = pa.table(
        {"geometry": pa.array([_wkb_point(120.0, 340.0)], type=pa.binary()),
         "id": pa.array([1], pa.int64())},
        schema=pa.schema([field, pa.field("id", pa.int64())],
                         metadata={"plenora.contract.version": CONTRACT_VERSION}),
    )
    return table, {"crs_resolution": "missing",
                   "must_not_become": "declared_unresolved", "rule": "R4.1",
                   "gate_fixture": "missing_crs"}


def case_geography_semantics() -> tuple[pa.Table, dict]:
    """`geography` non è `geometry`: cambia il calcolo delle distanze a valle."""
    meta = _canonical("xy")
    meta["plenora.geometry.spatial_semantics"] = "geography"
    meta["plenora.geometry.crs_id"] = "EPSG:4326"
    meta["plenora.geometry.srid"] = "4326"
    meta["plenora.geometry.axis_order"] = "lat_lon"
    field = _geometry_field("geometry", meta)
    table = pa.table(
        {"geometry": pa.array([_wkb_point(45.46, 9.19)], type=pa.binary()),
         "id": pa.array([1], pa.int64())},
        schema=pa.schema([field, pa.field("id", pa.int64())],
                         metadata={"plenora.contract.version": CONTRACT_VERSION}),
    )
    return table, {"spatial_semantics": "geography",
                   "must_not_become": "geometry", "rule": "R4.4",
                   "gate_fixture": "geography_semantics"}


def case_conflicting_crs() -> tuple[pa.Table, dict]:
    """SRID e crs_id in disaccordo: la catena deve fallire chiusa, non scegliere.

    Unico caso il cui esito atteso è un errore. Se un anello concilia il
    conflitto in silenzio, sceglie per conto dell'utente su dati patrimoniali.
    """
    meta = _canonical("xy")
    meta["plenora.geometry.crs_id"] = "EPSG:4326"
    meta["plenora.geometry.srid"] = "3003"
    field = _geometry_field("geometry", meta)
    table = pa.table(
        {"geometry": pa.array([_wkb_point(9.19, 45.46)], type=pa.binary()),
         "id": pa.array([1], pa.int64())},
        schema=pa.schema([field, pa.field("id", pa.int64())],
                         metadata={"plenora.contract.version": CONTRACT_VERSION}),
    )
    return table, {"expect": "fail_closed", "conflict": "crs_id=EPSG:4326 vs srid=3003",
                   "rule": "R4.3", "gate_fixture": "conflicting_crs_representations"}


CASES = {
    "point_z": case_point_z,
    "point_zm": case_point_zm,
    "dimensions_unknown": case_dimensions_unknown,
    "crs_unresolved": case_crs_unresolved,
    "axis_lat_lon": case_axis_lat_lon,
    "types_mixed": case_types_mixed,
    "int64_beyond_2_53": case_int64_beyond_2_53,
    "uint64_ordering": case_uint64_ordering,
    "unknown_key": case_unknown_key,
    "multipolygon_xyzm_srid": case_multipolygon_xyzm_srid,
    "crs_missing": case_crs_missing,
    "geography_semantics": case_geography_semantics,
    "conflicting_crs": case_conflicting_crs,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--only", action="append", choices=sorted(CASES))
    arguments = parser.parse_args()

    arguments.out.mkdir(parents=True, exist_ok=True)
    selected = arguments.only or sorted(CASES)

    for name in selected:
        table, expected = CASES[name]()
        target = arguments.out / f"{name}.arrow"
        with ipc.new_file(target, table.schema) as writer:
            writer.write_table(table)
        expected["case"] = name
        expected["schema_metadata"] = {
            key.decode(): value.decode()
            for key, value in (table.schema.metadata or {}).items()
        }
        expected["field_metadata"] = {
            key.decode(): value.decode()
            for key, value in (table.schema.field("geometry").metadata or {}).items()
        }
        (arguments.out / f"{name}.json").write_text(
            json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"{name}: {target.name} ({target.stat().st_size} byte)")

    print(f"\n{len(selected)} casi in {arguments.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
