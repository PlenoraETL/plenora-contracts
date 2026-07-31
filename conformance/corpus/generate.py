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
    # R4.3.3 richiede axis_order in presenza di crs_id. Il CRS non si risolve,
    # quindi l'ordine degli assi non e' noto: `unknown` e' il valore onesto, ed
    # e' nell'insieme ammesso. Ometterlo farebbe verificare al caso R4.3.3
    # invece della proprieta' che gli compete.
    meta["plenora.geometry.axis_order"] = "unknown"
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
         "id": pa.array([1, 2], pa.int64()),
         "asset_id": pa.array([b, a], pa.int64())},
        schema=pa.schema([_geometry_field("geometry", _canonical("xy")),
                          pa.field("id", pa.int64()),
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
         "id": pa.array(list(range(1, len(values) + 1)), pa.int64()),
         "code": pa.array(values, pa.uint64())},
        schema=pa.schema([_geometry_field("geometry", _canonical("xy")),
                          pa.field("id", pa.int64()),
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
    return table, {
        # R4.6 colloca il fail-closed: il bordo di lettura dichiara, il bordo di
        # scrittura rifiuta, il centro decide. Un'attesa unica per tutti e tre
        # chiedeva a IO-tools il contrario di R4.6.1.
        "expect": "by_role",
        "expect_by_role": {
            "file_boundary": "preserve",
            "transformation_core": "preserve_with_transition",
            "database_boundary": "fail_closed",
        },
        # L'etichetta `resolved` in ingresso afferma una risoluzione che il
        # contenuto smentisce: crs_id e srid si contraddicono. Il centro che la
        # lascia intatta rivendica una risoluzione inesistente; quello che passa
        # a `declared_unresolved` non cambia una verita', scopre una menzogna —
        # ed e' esattamente cio' che quello stato significa. La transizione e'
        # quindi **richiesta**, non tollerata, e tutto il resto deve restare
        # invariato: le rappresentazioni non si toccano (R4.6.3), lo stato si
        # corregge. Rilievo del team data-tools, accolto dall'owner.
        "required_transitions": {
            "transformation_core": {
                "plenora.geometry.crs_resolution": {
                    "from": "resolved",
                    "to": "declared_unresolved",
                },
            },
        },
        "conflict": "crs_id=EPSG:4326 vs srid=3003",
        "rule": "R4.3.1, R4.6",
        "gate_fixture": "conflicting_crs_representations",
        # Un rifiuto non basta: deve essere il rifiuto giusto. Senza queste due
        # liste un componente che respinge tutto per una ragione estranea
        # supererebbe il caso, ed e' esattamente cio' che e' successo nella
        # prima esecuzione della matrice.
        "expected_error": {
            "cause_hints": ["srid", "crs_id", "identificatore crs",
                            "rappresentazioni", "divergent", "conflict"],
            "disqualifying": ["backend_unavailable", "crs_backend",
                              "proj", "feature", "not implemented",
                              "unsupported operation"],
        },
    }


def case_polygon_xy_projected() -> tuple[pa.Table, dict]:
    """Poligoni XY in CRS proiettato: l'unico ingresso che i kernel geo accettano.

    ADR-0008 di data-tools decide due vie a compile-plan: le op tabellari
    propagano i byte per qualunque dimensionalita', i kernel geo rifiutano
    `dimensions != xy` — incluso `unknown` — perche' decodificano in XY e
    accettarlo equivarrebbe a mapparlo a `xy`. Diverse operazioni richiedono in
    piu' un CRS proiettato, perche' calcolano aree e distanze.

    Nessun altro caso del corpus soddisfa entrambe le condizioni: serve per
    esercitare le trasformazioni, non per verificare una proprieta' del
    contratto.
    """
    ring = [(1_500_000.0, 5_030_000.0), (1_500_040.0, 5_030_000.0),
            (1_500_040.0, 5_030_030.0), (1_500_000.0, 5_030_030.0),
            (1_500_000.0, 5_030_000.0)]
    def polygon(offset: float) -> bytes:
        out = struct.pack("<BII", 1, 3, 1) + struct.pack("<I", len(ring))
        for x, y in ring:
            out += struct.pack("<2d", x + offset, y)
        return out

    meta = _canonical("xy")
    meta["plenora.geometry.types"] = "polygon"
    meta["plenora.geometry.crs_id"] = "EPSG:3003"
    meta["plenora.geometry.srid"] = "3003"
    meta["plenora.geometry.axis_order"] = "easting_northing"
    field = _geometry_field("geometry", meta)
    table = pa.table(
        {"geometry": pa.array([polygon(0.0), polygon(60.0)], type=pa.binary()),
         "id": pa.array([1, 2], pa.int64())},
        schema=pa.schema([field, pa.field("id", pa.int64())],
                         metadata={"plenora.contract.version": CONTRACT_VERSION}),
    )
    return table, {"dimensions": "xy", "crs_id": "EPSG:3003", "types": "polygon",
                   "rule": "R3.3", "purpose": "ingresso per le trasformazioni geo"}


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
    "polygon_xy_projected": case_polygon_xy_projected,
}


AXIS_ORDERS = ("lon_lat", "lat_lon", "easting_northing",
               "northing_easting", "other", "unknown")
CRS_RESOLUTIONS = ("resolved", "declared_unresolved", "missing")
DIMENSIONS = ("xy", "xyz", "xym", "xyzm", "unknown")
TYPES_DECLARATIONS = ("exact", "mixed", "unresolved")


def check_coherence(name: str, metadata: dict[str, str], expected: dict) -> None:
    """Rifiuta una fixture positiva incoerente con l'ICD.

    Una fixture che dovrebbe attraversare la catena intatta ma viola una regola
    fa dipendere il corpus dal fatto che quella regola *non* sia implementata:
    un componente conforme la respinge e il caso fallisce per la ragione
    sbagliata. Solo i casi dichiarati `fail_closed` possono essere incoerenti,
    ed e' esattamente cio' che verificano.
    """
    if expected.get("expect") == "fail_closed":
        return

    problems: list[str] = []
    get = metadata.get

    # R4.3.3: axis_order obbligatorio se c'e' crs_id oppure crs_definition.
    if (get("plenora.geometry.crs_id") or get("plenora.geometry.crs_definition")) \
            and "plenora.geometry.axis_order" not in metadata:
        problems.append("R4.3.3: crs_id o crs_definition presenti senza axis_order")

    # R4.3: una definizione senza discriminatore non e' interpretabile.
    if bool(get("plenora.geometry.crs_definition")) != \
            bool(get("plenora.geometry.crs_definition_format")):
        problems.append("R4.3: crs_definition e crs_definition_format non sono una coppia")

    # R4.1: `missing` significa assenza, non un identificativo taciuto.
    if get("plenora.geometry.crs_resolution") == "missing" and get("plenora.geometry.crs_id"):
        problems.append("R4.1: crs_resolution=missing con un crs_id presente")

    for key, allowed in (("plenora.geometry.axis_order", AXIS_ORDERS),
                         ("plenora.geometry.crs_resolution", CRS_RESOLUTIONS),
                         ("plenora.geometry.dimensions", DIMENSIONS),
                         ("plenora.geometry.types_declaration", TYPES_DECLARATIONS)):
        value = get(key)
        if value is not None and value not in allowed:
            problems.append(f"{key}: valore {value!r} fuori dall'insieme ammesso")

    if problems:
        raise SystemExit(f"fixture '{name}' incoerente con l'ICD:\n  "
                         + "\n  ".join(problems))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--only", action="append", choices=sorted(CASES))
    arguments = parser.parse_args()

    arguments.out.mkdir(parents=True, exist_ok=True)
    selected = arguments.only or sorted(CASES)

    # Ogni caso in due varianti. Con le sole chiavi canoniche un componente puo'
    # superare il caso senza leggerle: il driver IPC di plenora-IO-tools legge la
    # colonna come binario opaco e propaga tutto intatto — conservazione reale e
    # richiesta da R2.4, ma non comprensione del contratto. Con l'estensione
    # GeoArrow la colonna e' riconosciuta e il contratto viene interpretato.
    #
    # Le due varianti separano le due proprieta' invece di confonderle, e
    # verificano in piu' che i componenti che gia' riconoscono le canoniche —
    # data-tools e database-tools — si comportino identicamente sulle due. R2.8
    # propone che sia obbligatorio; fino alla ratifica questo lo misura.
    variants = [("", False), ("__geoarrow", True)]

    for name in selected:
        for suffix, extension in variants:
            emit(arguments.out, name, suffix, extension)

    totale = len(selected) * len(variants)
    print(f"{len(selected)} casi x {len(variants)} varianti = {totale} file")
    return 0


def emit(out: Path, name: str, suffix: str, extension: bool) -> None:
    table, expected = CASES[name]()
    if extension:
        field = table.schema.field("geometry")
        metadata = {k.decode(): v.decode() for k, v in (field.metadata or {}).items()}
        metadata["ARROW:extension:name"] = "geoarrow.wkb"
        schema = pa.schema(
            [pa.field("geometry", field.type, nullable=field.nullable, metadata=metadata)]
            + [table.schema.field(i) for i in range(1, len(table.schema))],
            metadata=table.schema.metadata,
        )
        table = pa.table(table.columns, schema=schema)
    expected["variant"] = "geoarrow" if extension else "canonical_only"
    expected["variant_note"] = (
        "Estensione GeoArrow presente: la colonna e' riconosciuta da tutti e tre e "
        "il contratto viene interpretato." if extension else
        "Solo chiavi canoniche di §2. Un componente che le legge interpreta il "
        "contratto; uno che richiede l'estensione tratta la colonna come binario "
        "opaco e propaga senza leggere. L'esito positivo su questa variante non e' "
        "evidenza di comprensione semantica finche' R2.8 non e' ratificata."
    )
    _write(out, f"{name}{suffix}", table, expected)


def _write(out: Path, stem: str, table: pa.Table, expected: dict) -> None:
    target = out / f"{stem}.arrow"
    with ipc.new_file(target, table.schema) as writer:
        writer.write_table(table)
    expected["case"] = stem
    expected["schema_metadata"] = {
        key.decode(): value.decode()
        for key, value in (table.schema.metadata or {}).items()
    }
    expected["field_metadata"] = {
        key.decode(): value.decode()
        for key, value in (table.schema.field("geometry").metadata or {}).items()
    }
    check_coherence(stem, expected["field_metadata"], expected)
    (out / f"{stem}.json").write_text(
        json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"  {stem}: {target.stat().st_size} byte")


if __name__ == "__main__":
    raise SystemExit(main())
