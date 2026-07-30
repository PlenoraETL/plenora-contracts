#!/usr/bin/env python3
"""Genera dataset patrimoniali sporchi in formati reali.

Non e' il corpus di conformita'. Quello verifica proprieta' note su casi da due
righe e produce un esito. Questo produce **sorprese**: file grandi, sporchi e
plausibili, nei formati che gli uffici tecnici usano davvero, per vedere cosa
succede quando la catena incontra dati che nessuno ha disegnato per lei.

Le patologie non sono inventate: sono quelle che si trovano nei dati catastali
e patrimoniali italiani veri.

  - nomi di campo oltre i dieci caratteri, che il DBF tronca;
  - accenti nei valori (`Localita' Sant'Angelo`) con codepage CP1252, non UTF-8;
  - codici con zeri iniziali, che qualunque passaggio da foglio di calcolo
    distrugge silenziosamente;
  - identificativi oltre 2^53, che collassano se qualcuno li tratta come f64;
  - poligoni con buchi, con anelli avvolti nel verso sbagliato;
  - poligoni auto-intersecanti e ad area nulla;
  - vertici consecutivi duplicati e anelli non chiusi;
  - quote presenti ma tutte a zero, indistinguibili da quote assenti;
  - EPSG:3003 Monte Mario, con coordinate a sette cifre dove la precisione
    float32 non basta piu'.

Scrive shapefile (.shp/.shx/.dbf/.prj), che e' il formato dove queste patologie
sono nate, e Arrow IPC per il confronto. Solo la standard library e pyarrow.
"""

from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path

import pyarrow as pa
import pyarrow.ipc as ipc

# Monte Mario / Italy zone 1: il sistema del catasto italiano storico. Le
# coordinate hanno sette cifre intere, quindi un f32 perde gia' i decimetri.
EPSG_3003_WKT = (
    'PROJCS["Monte Mario / Italy zone 1",'
    'GEOGCS["Monte Mario",DATUM["Monte_Mario",'
    'SPHEROID["International 1924",6378388,297],'
    'TOWGS84[-104.1,-49.1,-9.9,0.971,-2.917,0.714,-11.68]],'
    'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],'
    'PROJECTION["Transverse_Mercator"],'
    'PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",9],'
    'PARAMETER["scale_factor",0.9996],'
    'PARAMETER["false_easting",1500000],PARAMETER["false_northing",0],'
    'UNIT["metre",1],AXIS["Easting",EAST],AXIS["Northing",NORTH],'
    'AUTHORITY["EPSG","3003"]]'
)

SHAPE_POLYGON = 5
SHAPE_POLYGON_Z = 15

# --------------------------------------------------------------- geometrie


def signed_area(ring: list[tuple[float, float]]) -> float:
    """Area con segno (shoelace): positiva se antiorario, negativa se orario."""
    total = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _ring(cx: float, cy: float, radius: float, vertices: int,
          clockwise: bool) -> list[tuple[float, float]]:
    """Anello chiuso, con il verso verificato invece che dedotto.

    In shapefile il guscio esterno e' **orario** e i buchi antiorari. Il verso
    non si deduce dalla direzione dell'indice — la prima versione di questa
    funzione lo sbagliava e produceva file che il lettore respingeva
    correttamente con `anello interno senza anello esterno`. Qui si genera e poi
    si verifica il segno dell'area, che e' la definizione e non un'inferenza.
    """
    step = 2 * math.pi / vertices
    ring = [(cx + radius * math.cos(index * step),
             cy + radius * math.sin(index * step)) for index in range(vertices)]
    ring.append(ring[0])
    is_clockwise = signed_area(ring) < 0
    if is_clockwise != clockwise:
        ring = list(reversed(ring))
    assert (signed_area(ring) < 0) == clockwise, "verso dell'anello non conforme"
    return ring


def parcel(index: int, pathology: str) -> tuple[list[list[tuple[float, float]]], str]:
    """Una particella, con la patologia richiesta. Restituisce anelli e nota."""
    # Coordinate plausibili per Monte Mario zona 1: Lombardia occidentale.
    cx = 1_500_000.0 + (index % 500) * 37.0
    cy = 5_030_000.0 + (index // 500) * 41.0

    if pathology == "hole":
        # Guscio orario, buco antiorario: il verso corretto per shapefile.
        return [_ring(cx, cy, 20.0, 8, True), _ring(cx, cy, 7.0, 6, False)], "buco"
    if pathology == "hole_wrong_winding":
        # Entrambi orari: il buco diventa un secondo guscio per un lettore che
        # si fida del verso, e resta un buco per uno che calcola l'inclusione.
        return [_ring(cx, cy, 20.0, 8, True), _ring(cx, cy, 7.0, 6, True)], "buco avvolto male"
    if pathology == "self_intersecting":
        # Farfalla: gli spigoli si incrociano, l'area non e' definita.
        return [[(cx, cy), (cx + 20, cy + 20), (cx + 20, cy),
                 (cx, cy + 20), (cx, cy)]], "auto-intersecante"
    if pathology == "zero_area":
        # Tre vertici collineari: area nulla, geometria formalmente valida.
        return [[(cx, cy), (cx + 10, cy), (cx + 20, cy), (cx, cy)]], "area nulla"
    if pathology == "duplicate_vertices":
        ring = _ring(cx, cy, 15.0, 6, True)
        return [[ring[0], ring[0], *ring[1:]]], "vertici duplicati"
    if pathology == "unclosed":
        # Anello non chiuso: lo shapefile lo pretende chiuso.
        return [_ring(cx, cy, 15.0, 6, True)[:-1]], "anello non chiuso"
    if pathology == "single_vertex_ring":
        return [[(cx, cy), (cx, cy), (cx, cy), (cx, cy)]], "anello degenere"
    return [_ring(cx, cy, 18.0, 10, True)], "regolare"


PATHOLOGIES = [
    ("regolare", 0.82),
    ("hole", 0.06),
    ("hole_wrong_winding", 0.03),
    ("self_intersecting", 0.03),
    ("zero_area", 0.02),
    ("duplicate_vertices", 0.02),
    ("unclosed", 0.01),
    ("single_vertex_ring", 0.01),
]


def pathology_for(index: int) -> str:
    """Distribuzione deterministica: nessun random, il corpus e' riproducibile."""
    position = (index * 7919) % 100  # 7919 primo: sparpaglia senza casualita'
    threshold = 0.0
    for name, share in PATHOLOGIES:
        threshold += share * 100
        if position < threshold:
            return name
    return "regolare"


# --------------------------------------------------------------- attributi

# I nomi oltre dieci caratteri sono quelli che il DBF tronca. Sono scritti per
# collidere una volta troncati: `denominazione_catastale` e
# `denominazione_storica` diventano entrambi `DENOMINAZ`.
FIELDS = [
    ("id_particella", "N", 18, 0),
    ("codice_belfiore", "C", 4, 0),
    ("foglio", "C", 6, 0),
    ("denominazione_catastale", "C", 60, 0),
    ("denominazione_storica", "C", 60, 0),
    ("superficie_catastale_mq", "N", 12, 2),
    ("quota_slm", "N", 10, 2),
    ("note_tecniche", "C", 120, 0),
]

COMUNI = ["Sant'Angelo Lodigiano", "Località Caselle", "Borgo San Siro",
          "Cascina Nuova d'Adda", "Frazione Bàrbara", "Corte Sant'Antonio"]


def attributes(index: int, pathology: str, note: str) -> dict:
    # Identificativi oltre 2^53: collassano se trattati come f64.
    identifier = (1 << 53) + index
    return {
        # Zeri iniziali: significativi, e distrutti da qualunque passaggio
        # numerico. Il codice Belfiore e' testo, non un numero.
        "codice_belfiore": f"{(index % 900) + 100:04d}"[:4],
        "foglio": f"{(index % 300):06d}",
        "id_particella": identifier,
        "denominazione_catastale": COMUNI[index % len(COMUNI)],
        "denominazione_storica": COMUNI[(index + 3) % len(COMUNI)],
        "superficie_catastale_mq": round(120.0 + (index % 900) * 3.25, 2),
        # Quota presente ma tutta a zero su una fetta dei record: indistinguibile
        # da quota assente se qualcuno guarda solo i valori.
        "quota_slm": 0.0 if index % 5 == 0 else round(80.0 + (index % 400) * 0.5, 2),
        "note_tecniche": f"patologia={pathology}; {note}; rilievo 2009",
    }


# --------------------------------------------------------------- shapefile


def _polygon_record(rings: list[list[tuple[float, float]]]) -> bytes:
    points = [point for ring in rings for point in ring]
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    body = struct.pack("<i", SHAPE_POLYGON)
    body += struct.pack("<4d", min(xs), min(ys), max(xs), max(ys))
    body += struct.pack("<ii", len(rings), len(points))
    offset = 0
    for ring in rings:
        body += struct.pack("<i", offset)
        offset += len(ring)
    for x, y in points:
        body += struct.pack("<2d", x, y)
    return body


def write_shapefile(directory: Path, name: str, geometries: list, rows: list[dict]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    shp = directory / f"{name}.shp"
    shx = directory / f"{name}.shx"

    records: list[bytes] = [_polygon_record(rings) for rings in geometries]

    all_points = [p for rings in geometries for ring in rings for p in ring]
    xs = [x for x, _ in all_points]
    ys = [y for _, y in all_points]

    def header(file_length_words: int) -> bytes:
        head = struct.pack(">i", 9994) + b"\x00" * 20
        head += struct.pack(">i", file_length_words)
        head += struct.pack("<ii", 1000, SHAPE_POLYGON)
        head += struct.pack("<4d", min(xs), min(ys), max(xs), max(ys))
        head += struct.pack("<4d", 0.0, 0.0, 0.0, 0.0)  # z e m non usati
        return head

    shp_body = b""
    shx_body = b""
    offset_words = 50  # l'header occupa 100 byte = 50 parole da 16 bit
    for number, content in enumerate(records, start=1):
        length_words = len(content) // 2
        shp_body += struct.pack(">ii", number, length_words) + content
        shx_body += struct.pack(">ii", offset_words, length_words)
        offset_words += 4 + length_words  # 8 byte di intestazione record

    shp.write_bytes(header(50 + len(shp_body) // 2) + shp_body)
    shx.write_bytes(header(50 + len(shx_body) // 2) + shx_body)
    (directory / f"{name}.prj").write_text(EPSG_3003_WKT, encoding="ascii")
    _write_dbf(directory / f"{name}.dbf", rows)
    # `cpg` dichiara la codepage: senza, un lettore deve indovinare.
    (directory / f"{name}.cpg").write_text("CP1252", encoding="ascii")


def _write_dbf(path: Path, rows: list[dict]) -> None:
    """dBase III. I nomi oltre 10 caratteri vengono troncati: e' il punto."""
    header_length = 32 + 32 * len(FIELDS) + 1
    record_length = 1 + sum(size for _, _, size, _ in FIELDS)

    head = struct.pack("<BBBB", 0x03, 26, 7, 30)  # 2026-07-30
    head += struct.pack("<IHH", len(rows), header_length, record_length)
    head += b"\x00" * 20

    for name, kind, size, decimals in FIELDS:
        truncated = name[:10].upper().encode("ascii")
        head += truncated.ljust(11, b"\x00")
        head += kind.encode("ascii")
        head += b"\x00" * 4
        head += struct.pack("<BB", size, decimals)
        head += b"\x00" * 14
    head += b"\x0d"

    body = b""
    for row in rows:
        body += b" "  # marcatore di cancellazione
        for name, kind, size, decimals in FIELDS:
            value = row[name]
            if kind == "N":
                text = f"{value:.{decimals}f}" if decimals else str(value)
                body += text.rjust(size)[-size:].encode("ascii")
            else:
                # CP1252, non UTF-8: e' cio' che i file veri contengono, e gli
                # accenti sono il modo piu' comune di scoprirlo.
                encoded = str(value).encode("cp1252", errors="replace")
                body += encoded.ljust(size, b" ")[:size]
    path.write_bytes(head + body + b"\x1a")


# --------------------------------------------------------------- arrow


def _wkb_polygon(rings: list[list[tuple[float, float]]]) -> bytes:
    out = struct.pack("<BII", 1, 3, len(rings))
    for ring in rings:
        out += struct.pack("<I", len(ring))
        for x, y in ring:
            out += struct.pack("<2d", x, y)
    return out


def write_arrow(path: Path, geometries: list, rows: list[dict]) -> None:
    metadata = {
        "plenora.field_id": "0",
        "plenora.geometry.encoding": "wkb",
        "plenora.geometry.dimensions": "xy",
        "plenora.geometry.crs_resolution": "resolved",
        "plenora.geometry.crs_id": "EPSG:3003",
        "plenora.geometry.srid": "3003",
        "plenora.geometry.axis_order": "easting_northing",
        "plenora.geometry.types_declaration": "exact",
        "plenora.geometry.types": "polygon",
        "plenora.geometry.spatial_semantics": "geometry",
        "plenora.geometry.precision": "float64",
    }
    columns = {"geometry": pa.array([_wkb_polygon(g) for g in geometries], pa.binary()),
               "id": pa.array(list(range(1, len(rows) + 1)), pa.int64())}
    fields = [pa.field("geometry", pa.binary(), metadata=metadata),
              pa.field("id", pa.int64())]
    for name, kind, _size, _decimals in FIELDS:
        if kind == "N" and name == "id_particella":
            columns[name] = pa.array([r[name] for r in rows], pa.int64())
            fields.append(pa.field(name, pa.int64()))
        elif kind == "N":
            columns[name] = pa.array([float(r[name]) for r in rows], pa.float64())
            fields.append(pa.field(name, pa.float64()))
        else:
            columns[name] = pa.array([str(r[name]) for r in rows], pa.string())
            fields.append(pa.field(name, pa.string()))
    schema = pa.schema(fields, metadata={"plenora.contract.version": "1"})
    table = pa.table(columns, schema=schema)
    path.parent.mkdir(parents=True, exist_ok=True)
    with ipc.new_file(path, table.schema) as writer:
        writer.write_table(table)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--rows", type=int, default=50_000)
    parser.add_argument("--name", default="particelle")
    arguments = parser.parse_args()

    geometries: list = []
    rows: list[dict] = []
    counts: dict[str, int] = {}
    for index in range(arguments.rows):
        pathology = pathology_for(index)
        rings, note = parcel(index, pathology)
        geometries.append(rings)
        rows.append(attributes(index, pathology, note))
        counts[pathology] = counts.get(pathology, 0) + 1

    write_shapefile(arguments.out, arguments.name, geometries, rows)
    write_arrow(arguments.out / f"{arguments.name}.arrow", geometries, rows)

    print(f"{arguments.rows} particelle in {arguments.out}")
    for name, count in sorted(counts.items(), key=lambda item: -item[1]):
        print(f"  {name:<22} {count:>7}  ({100 * count / arguments.rows:.1f}%)")
    print("\nfile:")
    for file in sorted(arguments.out.glob(f"{arguments.name}.*")):
        print(f"  {file.name:<22} {file.stat().st_size:>12,} byte")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
