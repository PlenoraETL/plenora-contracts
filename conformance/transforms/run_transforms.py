#!/usr/bin/env python3
"""Cosa succede al contratto quando il dato viene davvero trasformato.

`run_roundtrip.py` e `run_chain.py` verificano il **transito**: il piano che
usano è un filtro identità, quindi su 147 operazioni ne esercitano una, scelta
apposta per non trasformare niente. Provano che il contratto sopravvive quando
il dato non cambia.

Questo strumento fa l'altra metà, che è quella difficile: applica una vera
trasformazione e registra il contratto che ne esce. Dopo una riproiezione
`crs_id` deve cambiare — e `axis_order`? e `srid`? Dopo un buffer, che è
bidimensionale, una geometria XYZ resta `xyz`? Dopo un dissolve i tipi restano
`exact`? R2.4 distingue lineage `identity`, `derived` e `multi_source`, e finora
la catena non ha mai prodotto un dato derivato: quelle regole non sono mai state
esercitate da nessuno.

**Non giudica.** Per diversi casi il contratto atteso non è deciso, e inventarlo
qui significherebbe imporre come regola una mia opinione. Lo strumento esegue,
osserva e riporta; dove esiste un'attesa dichiarata la verifica, dove non esiste
scrive `da_decidere` e mostra cosa è successo. Le domande che ne escono sono per
l'owner, non per i team.

Solo la standard library e pyarrow.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pyarrow.ipc as ipc

CANONICAL = (
    "plenora.geometry.crs_id",
    "plenora.geometry.srid",
    "plenora.geometry.crs_resolution",
    "plenora.geometry.axis_order",
    "plenora.geometry.dimensions",
    "plenora.geometry.types",
    "plenora.geometry.types_declaration",
    "plenora.geometry.spatial_semantics",
    "plenora.geometry.encoding",
    "plenora.geometry.precision",
    "plenora.field_id",
)


def plan(node_id: str, op: str, config: dict) -> dict:
    return {
        "schema_version": 4,
        "inputs": ["main"],
        "nodes": [{"id": node_id, "op": op, "in": ["main"], "config": config}],
        "output": node_id,
    }


# Ogni trasformazione dichiara: il caso del corpus su cui si applica, il piano,
# la domanda che pone al contratto, e cio' che ci si aspetta *se* e' deciso.
TRANSFORMS = [
    {
        "id": "reproject",
        "case": "polygon_xy_projected",
        "plan": plan("t", "geo.reproject", {"target_crs": "EPSG:4326"}),
        "question": "Dopo una riproiezione cambiano crs_id, srid e axis_order. "
                    "Chi li riscrive e con quale autorita'? EPSG:4326 e' lat/lon "
                    "per R4.2: l'axis_order deve diventare lat_lon, non restare "
                    "easting_northing.",
        "expected": {"plenora.geometry.crs_id": "EPSG:4326"},
        "open": ["plenora.geometry.srid", "plenora.geometry.axis_order"],
    },
    {
        "id": "centroid",
        "case": "polygon_xy_projected",
        "plan": plan("t", "geo.centroid", {}),
        "question": "Un centroide trasforma poligoni in punti. `types` deve "
                    "passare da polygon a point, altrimenti il contratto "
                    "dichiara un tipo che i byte smentiscono (H-01).",
        "expected": {},
        "open": ["plenora.geometry.types", "plenora.geometry.types_declaration"],
    },
    {
        "id": "buffer",
        "case": "polygon_xy_projected",
        "plan": plan("t", "geo.buffer", {"distance": 5.0}),
        "question": "Il buffer sostituisce ogni geometria con la propria "
                    "dilatazione. Il tipo resta polygon, ma i byte sono altri: "
                    "il contratto in uscita e' derivato, non identita' (R2.4).",
        "expected": {},
        "open": ["plenora.geometry.types"],
    },
    {
        "id": "dissolve",
        "case": "polygon_xy_projected",
        "plan": plan("t", "geo.dissolve", {}),
        "question": "Il dissolve aggrega molte geometrie in una e non propaga "
                    "gli attributi. Il tipo puo' diventare multipolygon, e la "
                    "dichiarazione `exact` va rivista di conseguenza.",
        "expected": {},
        "open": ["plenora.geometry.types", "plenora.geometry.types_declaration"],
    },
    {
        "id": "simplify",
        "case": "polygon_xy_projected",
        "plan": plan("t", "geo.simplify", {"tolerance": 0.5}),
        "question": "La semplificazione toglie vertici senza cambiare tipo ne' "
                    "sistema di riferimento: il contratto non dovrebbe cambiare.",
        "expected": {},
        "open": [],
    },
    {
        "id": "make_valid",
        "case": "polygon_xy_projected",
        "plan": plan("t", "geo.make_valid", {}),
        "question": "make_valid ripara una geometria: e' una correzione, non "
                    "una trasformazione di tipo. Il contratto non dovrebbe "
                    "cambiare. Richiede la capability `geos`.",
        "expected": {},
        "open": [],
    },
    {
        "id": "dimensione_non_xy",
        "case": "point_zm",
        "plan": plan("t", "geo.centroid", {}),
        "question": "ADR-0008 decide che i kernel geo rifiutano "
                    "`dimensions != xy` in analisi del piano, invece di "
                    "appiattire in silenzio. Questo caso verifica che il "
                    "rifiuto avvenga: e' l'alternativa a un metadato che "
                    "contraddice i byte.",
        "expected": {},
        "open": [],
        "expect_rejection": True,
    },
]


def contract_of(path: Path) -> dict[str, str]:
    table = ipc.open_file(str(path)).read_all()
    if "geometry" not in table.schema.names:
        return {}
    metadata = table.schema.field("geometry").metadata or {}
    observed = {k.decode(): v.decode() for k, v in metadata.items()}
    schema_metadata = table.schema.metadata or {}
    observed.update({k.decode(): v.decode() for k, v in schema_metadata.items()})
    return observed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent.parent
    parser.add_argument("--cases", type=Path, default=root / "cases")
    parser.add_argument("--components", type=Path, default=root / "components.json")
    parser.add_argument("--checkouts", type=Path, default=root.parent.parent)
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()

    manifest = json.loads(arguments.components.read_text(encoding="utf-8"))
    entry = next((r for r in manifest["roundtrips"] if r["id"] == "data"), None)
    if entry is None or entry["status"] != "available":
        print("roundtrip 'data' non disponibile", file=sys.stderr)
        return 2
    repo = arguments.checkouts / entry["component"]
    if not (repo / "Cargo.toml").is_file():
        print(f"checkout assente: {repo}", file=sys.stderr)
        return 2
    if shutil.which("cargo") is None:
        print("cargo non disponibile nel PATH", file=sys.stderr)
        return 2

    results = []
    with tempfile.TemporaryDirectory(prefix="plenora-transform-") as directory:
        workspace = Path(directory)
        for transform in TRANSFORMS:
            source = arguments.cases / f"{transform['case']}.arrow"
            if not source.is_file():
                print(f"caso assente: {source}", file=sys.stderr)
                continue
            plan_path = workspace / f"{transform['id']}.plan.json"
            plan_path.write_text(json.dumps(transform["plan"], separators=(",", ":")),
                                 encoding="utf-8")
            target = workspace / f"{transform['id']}.arrow"

            command = [part.format(plan=str(plan_path), input=str(source),
                                   output=str(target))
                       for part in entry["invocation"]]
            completed = subprocess.run(command, cwd=repo, capture_output=True,
                                       text=True, check=False)

            record = {"transform": transform["id"], "case": transform["case"],
                      "op": transform["plan"]["nodes"][0]["op"],
                      "question": transform["question"]}

            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout or "").strip()
                record["outcome"] = "rifiutato"
                record["detail"] = detail[-400:]
                if transform.get("expect_rejection"):
                    record["verdict"] = "pass"
                    record["problems"] = []
                else:
                    record["verdict"] = "fail"
                    record["problems"] = ["rifiutato ma la trasformazione "
                                          "doveva essere eseguibile"]
                results.append(record)
                continue

            before = contract_of(source)
            after = contract_of(target)
            changes = {key: {"prima": before.get(key), "dopo": after.get(key)}
                       for key in CANONICAL
                       if before.get(key) != after.get(key)}
            record["outcome"] = "eseguito"
            record["changes"] = changes
            record["unchanged"] = [k for k in CANONICAL
                                   if k in before and k not in changes]

            problems = [f"{key}: atteso {value!r}, osservato {after.get(key)!r}"
                        for key, value in transform["expected"].items()
                        if after.get(key) != value]
            if transform.get("expect_rejection"):
                problems.append("eseguito, ma ADR-0008 richiede il rifiuto in "
                                "analisi del piano per dimensions != xy")
            record["verdict"] = ("fail" if problems else
                                 "da_decidere" if transform["open"] else "pass")
            record["problems"] = problems
            record["open_keys"] = {k: changes.get(k, {"prima": before.get(k),
                                                      "dopo": after.get(k)})
                                   for k in transform["open"]}
            results.append(record)

    for record in results:
        marker = {"rifiutato": "RIF ", "eseguito": "    "}[record["outcome"]]
        verdict = record.get("verdict", "")
        print(f"\n{marker}{record['transform']:<16} {record['op']:<16} {verdict}")
        if record["outcome"] == "rifiutato":
            print(f"      {record['detail'][:200]}")
            continue
        for key, change in record["changes"].items():
            print(f"      {key.split('.')[-1]:<20} {change['prima']!r} -> {change['dopo']!r}")
        if not record["changes"]:
            print("      contratto invariato")
        for problem in record["problems"]:
            print(f"      ATTESA NON RISPETTATA: {problem}")

    decided = [r for r in results if r.get("verdict") in ("pass", "fail")]
    undecided = [r for r in results if r.get("verdict") == "da_decidere"]
    rejected = [r for r in results if r["outcome"] == "rifiutato"]
    print(f"\n{len(results)} trasformazioni: {len(decided)} con attesa dichiarata, "
          f"{len(undecided)} da decidere, {len(rejected)} rifiutate")
    print("Le voci `da_decidere` non sono difetti: sono domande che l'ICD non "
          "risponde ancora.")

    if arguments.report:
        arguments.report.write_text(
            json.dumps({"manifest_version": 1, "kind": "transform_discovery",
                        "note": "Esecuzione esplorativa: registra cosa accade al "
                                "contratto sotto trasformazione. Non e' evidenza "
                                "di conformita'.",
                        "transforms": results}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
    return 1 if any(r.get("problems") for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
