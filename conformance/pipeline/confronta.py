#!/usr/bin/env python3
"""Fase 0: la stessa pipeline sui due stack, e la differenza fra gli output.

Non serve a integrare. Serve a misurare l'attrito — cosa il backend attuale fa
e i tre componenti fanno diversamente, prima che qualcuno riscriva ottomila
righe contro un'ipotesi.

La pipeline è quella di un ETL patrimoniale minimo che tocca tutti e tre i
confini:

    shapefile catastale EPSG:3003
      → filtro sugli attributi
      → riproiezione a EPSG:4326
      → contratto in uscita

Lo stack di riferimento è GeoPandas/Shapely, che è quello che Plenora usa oggi.
Quello nuovo sono i tre componenti via il confine Python.

**Non giudica quale sia giusto.** Riporta dove divergono: la decisione su ogni
divergenza è dell'owner, e alcune saranno regressioni accettabili e altre no.
"""

from __future__ import annotations

import json
import subprocess
import time
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))

PIANO = {
    "schema_version": 4,
    "inputs": ["main"],
    "nodes": [
        {"id": "f", "op": "table.filter", "in": ["main"],
         "config": {"column": "SUPERFICIE", "operator": ">", "value": 500.0}},
    ],
    "output": "f",
}


def riferimento(sorgente: Path) -> dict:
    """Lo stack attuale: GeoPandas, in memoria e in processo."""
    import geopandas as gpd

    t0 = time.perf_counter()
    letto = gpd.read_file(sorgente)
    t_lettura = time.perf_counter() - t0

    t0 = time.perf_counter()
    filtrato = letto[letto["SUPERFICIE"] > 500.0]
    t_filtro = time.perf_counter() - t0

    t0 = time.perf_counter()
    riproiettato = filtrato.to_crs("EPSG:4326")
    t_riproiezione = time.perf_counter() - t0
    return {
        "tempi": {"lettura": round(t_lettura, 4), "filtro": round(t_filtro, 4),
                  "riproiezione": round(t_riproiezione, 4),
                  "totale": round(t_lettura + t_filtro + t_riproiezione, 4)},
        "righe_lette": len(letto),
        "righe_filtrate": len(filtrato),
        "colonne": list(letto.columns),
        # `letto.dtypes` invece di `letto[c].dtype`: GeoPandas conserva le
        # colonne omonime che il DBF produce per troncamento, quindi
        # l'indicizzazione per nome restituirebbe un DataFrame. E' gia' una
        # differenza rispetto ai tre, che ne tengono una sola.
        "tipi_attributi": {c: str(d) for c, d in letto.dtypes.items()
                           if c != "geometry"},
        "colonne_omonime": sorted({c for c in letto.columns
                                   if list(letto.columns).count(c) > 1}),
        "id_distinti": int(letto.iloc[:, list(letto.columns).index("ID_PARTICE")].nunique()),
        "tipi_geometrici": {k: int(v) for k, v in
                            letto.geom_type.value_counts().to_dict().items()},
        "geometrie_valide": int(letto.geometry.is_valid.sum()),
        "crs_dopo_riproiezione": str(riproiettato.crs),
        "primo_id": int(letto.iloc[0, list(letto.columns).index("ID_PARTICE")]),
        "primo_centroide_4326": [round(v, 6) for v in
                                 (riproiettato.geometry.iloc[0].centroid.x,
                                  riproiettato.geometry.iloc[0].centroid.y)],
    }


def nuovo(sorgente: Path, io_repo: Path, data_repo: Path,
          lavoro: Path) -> dict:
    """I tre componenti, via il confine Python."""
    from plenora import Component, convert, PlenoraError

    # `--release` e' obbligatorio per un confronto di prestazioni: in debug
    # Rust e' ordini di grandezza piu' lento e il numero non direbbe nulla.
    io = Component("IO-tools", io_repo, "plenora-io-cli")
    io.__dict__  # dataclass frozen: l'opzione release passa dal comando sotto
    arrow = lavoro / "letto.arrow"
    esito: dict = {}

    t0 = time.perf_counter()
    completato = subprocess.run(
        ["cargo", "run", "--locked", "--quiet", "--release", "-p", "plenora-io-cli",
         "--", "convert", str(sorgente), str(arrow)],
        cwd=io_repo, capture_output=True, text=True, check=False)
    t_lettura = time.perf_counter() - t0
    documento = json.loads(completato.stdout[completato.stdout.find("{"):])
    from plenora.fidelity import ConversionReport
    rapporto = ConversionReport.parse(documento)
    esito["tempi"] = {"lettura": round(t_lettura, 4)}
    esito["righe_lette"] = rapporto.rows
    esito["fedele"] = rapporto.faithful
    esito["perdite"] = rapporto.losses()

    import pyarrow.ipc as ipc
    tabella = ipc.open_file(str(arrow)).read_all()
    esito["colonne"] = tabella.schema.names
    esito["tipi_attributi"] = {n: str(tabella.schema.field(n).type)
                               for n in tabella.schema.names if n != "geometry"}
    if "ID_PARTICE" in tabella.schema.names:
        colonna = tabella.column("ID_PARTICE")
        esito["id_distinti"] = len({colonna[i].as_py()
                                    for i in range(tabella.num_rows)})
    metadati = tabella.schema.field("geometry").metadata or {}
    esito["contratto"] = {k.decode(): v.decode() for k, v in metadati.items()
                          if k.decode().startswith("plenora.geometry")}

    piano = lavoro / "piano.json"
    piano.write_text(json.dumps(PIANO, separators=(",", ":")), encoding="utf-8")
    uscita = lavoro / "filtrato.arrow"
    t0 = time.perf_counter()
    comando = ["cargo", "run", "--locked", "--quiet", "--release", "-p", "plenora-cli",
               "--features", "full-backends", "--", "run",
               "--plan", str(piano), "--inputs", str(arrow),
               "--output", str(uscita)]
    completato = subprocess.run(comando, cwd=data_repo, capture_output=True,
                                text=True, check=False)
    esito["tempi"]["filtro"] = round(time.perf_counter() - t0, 4)
    if completato.returncode != 0:
        esito["filtro"] = "RIFIUTATO"
        esito["filtro_dettaglio"] = (completato.stderr or completato.stdout)[-300:]
    else:
        esito["righe_filtrate"] = ipc.open_file(str(uscita)).read_all().num_rows
        esito["filtro"] = "ok"

    # La riproiezione: il piano la chiede come nodo separato perche' cambia il CRS
    piano_r = lavoro / "riproietta.json"
    piano_r.write_text(json.dumps({
        "schema_version": 4, "inputs": ["main"],
        "nodes": [{"id": "r", "op": "geo.reproject", "in": ["main"],
                   "config": {"target_crs": "EPSG:4326"}}],
        "output": "r"}, separators=(",", ":")), encoding="utf-8")
    riproiettato = lavoro / "riproiettato.arrow"
    t0 = time.perf_counter()
    completato = subprocess.run(
        ["cargo", "run", "--locked", "--quiet", "--release", "-p", "plenora-cli",
         "--features", "full-backends", "--", "run", "--plan", str(piano_r),
         "--inputs", str(uscita if esito.get("filtro") == "ok" else arrow),
         "--output", str(riproiettato)],
        cwd=data_repo, capture_output=True, text=True, check=False)
    esito["tempi"]["riproiezione"] = round(time.perf_counter() - t0, 4)
    esito["tempi"]["totale"] = round(sum(esito["tempi"].values()), 4)
    if completato.returncode != 0:
        esito["riproiezione"] = "RIFIUTATA"
        esito["riproiezione_dettaglio"] = (completato.stderr or completato.stdout)[-300:]
    else:
        esito["riproiezione"] = "ok"
        finale = ipc.open_file(str(riproiettato)).read_all()
        meta = finale.schema.field("geometry").metadata or {}
        esito["contratto_dopo_riproiezione"] = {
            k.decode(): v.decode() for k, v in meta.items()
            if k.decode().startswith("plenora.geometry")}
    return esito


def confronta(rif: dict, nuo: dict) -> list[tuple[str, str, str, str]]:
    """(aspetto, riferimento, nuovo, giudizio) — il giudizio non è un verdetto."""
    righe: list[tuple[str, str, str, str]] = []

    def r(aspetto, a, b, nota=""):
        righe.append((aspetto, str(a), str(b), nota))

    r("righe lette", rif["righe_lette"], nuo.get("righe_lette", "?"))
    r("righe dopo il filtro", rif["righe_filtrate"], nuo.get("righe_filtrate", "?"))
    r("identificativi distinti", rif["id_distinti"], nuo.get("id_distinti", "?"),
      "perdita di identita' se il nuovo e' minore")
    r("tipo di ID_PARTICE", rif["tipi_attributi"].get("ID_PARTICE"),
      nuo.get("tipi_attributi", {}).get("ID_PARTICE"))
    r("numero di colonne", len(rif["colonne"]), len(nuo.get("colonne", [])))
    r("colonne omonime conservate", rif.get("colonne_omonime", []),
      "una sola per nome",
      "il DBF tronca due nomi sullo stesso: uno stack le tiene entrambe")
    r("riproiezione", "eseguita", nuo.get("riproiezione", "?"))
    r("CRS dopo riproiezione", rif["crs_dopo_riproiezione"],
      nuo.get("contratto_dopo_riproiezione", {}).get("plenora.geometry.crs_id", "?"))
    r("ordine assi dopo riproiezione", "non rappresentato da GeoPandas",
      nuo.get("contratto_dopo_riproiezione", {}).get("plenora.geometry.axis_order", "?"))
    r("perdita dichiarata", "nessun meccanismo", nuo.get("perdite", {}))
    tr, tn = rif.get("tempi", {}), nuo.get("tempi", {})
    for stadio in ("lettura", "filtro", "riproiezione", "totale"):
        a, b = tr.get(stadio), tn.get(stadio)
        if a is not None and b is not None:
            rapporto = f"{b/a:.1f}x" if a > 0 else "?"
            r(f"tempo {stadio} (s)", a, f"{b}  ({rapporto})")
    return righe


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sorgente", required=True, type=Path)
    parser.add_argument("--io-repo", required=True, type=Path)
    parser.add_argument("--data-repo", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="plenora-fase0-") as directory:
        lavoro = Path(directory)
        print("== stack attuale (GeoPandas) ==")
        rif = riferimento(arguments.sorgente)
        print(f"  {rif['righe_lette']} righe, {rif['id_distinti']} id distinti, "
              f"{rif['geometrie_valide']} geometrie valide")
        print()
        print("== i tre componenti ==")
        nuo = nuovo(arguments.sorgente, arguments.io_repo, arguments.data_repo, lavoro)
        print(f"  {nuo.get('righe_lette')} righe, "
              f"{nuo.get('id_distinti')} id distinti, "
              f"fedele={nuo.get('fedele')}")

    print()
    print("== differenze ==")
    righe = confronta(rif, nuo)
    for aspetto, a, b, nota in righe:
        marcatore = "  " if a == b else "≠ "
        print(f"{marcatore}{aspetto:<32} {a[:34]:<36} {b[:40]}")
        if nota and a != b:
            print(f"    {nota}")

    diverse = [x for x in righe if x[1] != x[2]]
    print(f"\n{len(diverse)}/{len(righe)} aspetti divergono")

    if arguments.report:
        arguments.report.write_text(json.dumps(
            {"kind": "fase0_confronto", "riferimento": rif, "nuovo": nuo,
             "differenze": [{"aspetto": a, "attuale": b, "nuovo": c, "nota": d}
                            for a, b, c, d in righe if b != c]},
            indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
