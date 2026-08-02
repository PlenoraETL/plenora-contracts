#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import struct
from pathlib import Path


SHAPE_POLYGON = 5
EPSG_3003_WKT = (
    'PROJCS["Monte Mario / Italy zone 1",'
    'GEOGCS["Monte Mario",DATUM["Monte_Mario",'
    'SPHEROID["International 1924",6378388,297]],'
    'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],'
    'PROJECTION["Transverse_Mercator"],'
    'PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",9],'
    'PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",1500000],'
    'PARAMETER["false_northing",0],UNIT["metre",1],'
    'AUTHORITY["EPSG","3003"]]'
)


def _signed_area(ring: list[tuple[float, float]]) -> float:
    return sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(ring, ring[1:])
    ) / 2.0


def _ring(
    cx: float,
    cy: float,
    radius: float = 18.0,
    vertices: int = 8,
    *,
    clockwise: bool,
    closed: bool = True,
) -> list[tuple[float, float]]:
    step = 2 * math.pi / vertices
    ring = [
        (cx + radius * math.cos(index * step), cy + radius * math.sin(index * step))
        for index in range(vertices)
    ]
    ring.append(ring[0])
    if (_signed_area(ring) < 0) != clockwise:
        ring.reverse()
    if not closed:
        ring.pop()
    return ring


def _geometry(index: int) -> list[list[tuple[float, float]]]:
    cx = 1_500_000.0 + index * 37.0
    cy = 5_030_000.0 + index * 13.0
    if index in (17, 113):
        return [_ring(cx, cy, clockwise=False)]
    if index == 89:
        return [_ring(cx, cy, clockwise=True, closed=False)]
    return [_ring(cx, cy, clockwise=True)]


def _polygon_record(rings: list[list[tuple[float, float]]]) -> bytes:
    points = [point for ring in rings for point in ring]
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    body = struct.pack("<i4dii", SHAPE_POLYGON, min(xs), min(ys), max(xs), max(ys), len(rings), len(points))
    offset = 0
    for ring in rings:
        body += struct.pack("<i", offset)
        offset += len(ring)
    for x, y in points:
        body += struct.pack("<2d", x, y)
    return body


def _shapefile_header(file_length_words: int, geometries: list[list[list[tuple[float, float]]]]) -> bytes:
    points = [point for geometry in geometries for ring in geometry for point in ring]
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    header = struct.pack(">i", 9994) + b"\x00" * 20 + struct.pack(">i", file_length_words)
    header += struct.pack("<ii4d4d", 1000, SHAPE_POLYGON, min(xs), min(ys), max(xs), max(ys), 0.0, 0.0, 0.0, 0.0)
    return header


def _write_dbf(path: Path, rows: int) -> None:
    fields = [("ID_PART", "N", 18, 0), ("NOTE", "C", 48, 0)]
    header_length = 32 + 32 * len(fields) + 1
    record_length = 1 + sum(width for _, _, width, _ in fields)
    header = struct.pack("<BBBBIHH", 0x03, 26, 8, 2, rows, header_length, record_length) + b"\x00" * 20
    for name, kind, width, decimals in fields:
        header += name.encode("ascii").ljust(11, b"\x00")
        header += kind.encode("ascii") + b"\x00" * 4
        header += struct.pack("<BB", width, decimals) + b"\x00" * 14
    header += b"\x0d"
    body = bytearray()
    for index in range(rows):
        identifier = str((1 << 53) + index).rjust(18)
        note = (
            "inner_ring_without_outer"
            if index in (17, 113)
            else "unclosed_ring" if index == 89 else "regular"
        )
        body.extend(b" " + identifier.encode("ascii") + note.encode("ascii").ljust(48))
    path.write_bytes(header + body + b"\x1a")


def _write_shapefile(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    geometries = [_geometry(index) for index in range(128)]
    records = [_polygon_record(geometry) for geometry in geometries]
    shp_body = bytearray()
    shx_body = bytearray()
    offset_words = 50
    for number, record in enumerate(records, start=1):
        words = len(record) // 2
        shp_body.extend(struct.pack(">ii", number, words) + record)
        shx_body.extend(struct.pack(">ii", offset_words, words))
        offset_words += 4 + words
    (root / "particelle.shp").write_bytes(
        _shapefile_header(50 + len(shp_body) // 2, geometries) + shp_body
    )
    (root / "particelle.shx").write_bytes(
        _shapefile_header(50 + len(shx_body) // 2, geometries) + shx_body
    )
    _write_dbf(root / "particelle.dbf", len(geometries))
    (root / "particelle.prj").write_text(EPSG_3003_WKT, encoding="ascii")
    (root / "particelle.cpg").write_text("CP1252", encoding="ascii")


def _write_invalid_dates(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["row_label", "effective_date"])
        for index in range(1025):
            value = "2026-02-30" if index == 4 else "not-a-date" if index == 1004 else "2026-08-02"
            writer.writerow([f"row-{index}", value])


def _write_constraint_rows(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["parcel_id", "area_m2"])
        for index in range(5200):
            area = "-1.0" if index == 4999 else f"{100.0 + index / 10:.1f}"
            writer.writerow([f"P-{index:05d}", area])


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    _write_shapefile(output / "read-shapefile-invalid-geometry")
    _write_invalid_dates(output / "read-invalid-date.csv")
    _write_constraint_rows(output / "write-constraint.csv")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    generate(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
