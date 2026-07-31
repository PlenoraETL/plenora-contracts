#!/usr/bin/env python3
"""Verifica il confine Python contro le buste reali dei tre componenti.

Le buste non sono inventate: sono catturate eseguendo i tre CLI su errori veri,
il 31 luglio 2026, alle revisioni in cui la busta a quattro assi è stata
consegnata. Se un componente cambia forma questi test lo dicono.

    python python/test_plenora.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from plenora import (  # noqa: E402
    Category, ConversionReport, Level, MalformedEnvelope, Phase, RemoteEffect,
    RetryKind, parse_error,
)

# Catturate eseguendo, non scritte a mano.
REALI = {
    "IO-tools": json.dumps({
        "contract": "plenora-io-error-v1", "protocol_version": 1, "status": "error",
        "error": {"category": "data_mapping", "code": "FORMAT_ERROR",
                  "message": "anello interno Shapefile senza anello esterno",
                  "phase": "read", "remote_effect": "none",
                  "retry": {"kind": "never"}}}),
    "data-tools": json.dumps({
        "protocol_version": 1, "status": "error",
        "error": {"category": "unsupported", "phase": "validate",
                  "message": "geo.centroid: dimensionalita' xyzm non supportata",
                  "remote_effect": "none", "retry": {"kind": "never"}}}),
    "database-tools": json.dumps({
        "protocol_version": 1, "status": "error",
        "error": {"category": "crs", "execution_id": None, "provider": None,
                  "message": "identificatore CRS e SRID numerico divergenti",
                  "phase": "validate", "remote_effect": "none",
                  "retry": {"kind": "never"}}}),
}


def prove() -> list[tuple[str, bool, str]]:
    esiti: list[tuple[str, bool, str]] = []

    def verifica(nome: str, condizione: bool, dettaglio: str = "") -> None:
        esiti.append((nome, condizione, dettaglio))

    # --- le tre buste reali si leggono tutte
    for componente, busta in REALI.items():
        errore = parse_error(componente, busta)
        verifica(f"busta reale di {componente}",
                 isinstance(errore.category, Category)
                 and isinstance(errore.phase, Phase)
                 and isinstance(errore.remote_effect, RemoteEffect)
                 and errore.retry.kind is RetryKind.NEVER,
                 f"{errore.category.value}/{errore.phase.value}")

    # --- i campi oltre i cinque canonici finiscono in context, non interpretati
    errore = parse_error("IO-tools", REALI["IO-tools"])
    verifica("campi extra in context, non interpretati",
             errore.context == {"code": "FORMAT_ERROR"}, str(errore.context))

    # --- `after` senza durata e' una busta rotta: dice di riprovare piu' tardi
    #     senza dire quando, ed e' meta' informazione
    rotta = json.dumps({"status": "error", "protocol_version": 1,
                        "error": {"category": "transient", "phase": "connect",
                                  "remote_effect": "unknown",
                                  "retry": {"kind": "after"}, "message": "x"}})
    try:
        parse_error("x", rotta)
        verifica("`after` senza delay_ms rifiutata", False, "accettata")
    except MalformedEnvelope as errore:
        verifica("`after` senza delay_ms rifiutata", True, str(errore)[:60])

    # --- `after` con durata si legge, ed e' ritentabile
    valida = json.dumps({"status": "error", "protocol_version": 1,
                         "error": {"category": "transient", "phase": "connect",
                                   "remote_effect": "unknown",
                                   "retry": {"kind": "after", "delay_ms": 5000},
                                   "message": "x"}})
    errore = parse_error("x", valida)
    verifica("`after` con delay_ms, ritentabile",
             errore.retry.delay_ms == 5000 and errore.retry.retryable,
             f"delay={errore.retry.delay_ms}")

    # --- effetto ignoto: chi decide deve accertare lo stato prima di ripartire
    verifica("effetto `unknown` conta come possibile commit",
             errore.committed_remotely, str(errore.remote_effect.value))

    # --- una busta senza gli assi non e' interpretabile: R9.2 vieta di
    #     dedurli dal messaggio, quindi non li si deduce
    priva = json.dumps({"status": "error", "protocol_version": 1,
                        "error": {"message": "qualcosa è andato storto"}})
    try:
        parse_error("x", priva)
        verifica("busta priva degli assi rifiutata", False, "accettata")
    except MalformedEnvelope as errore:
        verifica("busta priva degli assi rifiutata", True, str(errore)[:70])

    # --- un valore fuori dall'enumerazione condivisa e' un errore (R9.5)
    inventata = json.dumps({"status": "error", "protocol_version": 1,
                            "error": {"category": "fantasia", "phase": "read",
                                      "remote_effect": "none",
                                      "retry": {"kind": "never"}, "message": "x"}})
    try:
        parse_error("x", inventata)
        verifica("categoria inventata rifiutata", False, "accettata")
    except MalformedEnvelope:
        verifica("categoria inventata rifiutata", True)

    # --- la fedelta' complessiva non e' quella del writer
    documento = {"from": "shp", "to": "ipc", "total_rows": 3000,
                 "read_loss": {"counts": {"dbf_numeric_integer_precision_unverifiable": 3000},
                               "lossless": False},
                 "write_loss": {"counts": {}, "lossless": True},
                 "read_fidelity": {"level": "approximating", "reasons": []},
                 "write_fidelity": {"level": "lossless", "reasons": []},
                 "conversion_fidelity": {"level": "approximating", "reasons": []}}
    report = ConversionReport.parse(documento)
    verifica("writer fedele ma conversione no",
             report.write_loss.lossless and not report.faithful,
             f"write={report.write_loss.lossless} conversione={report.faithful}")
    verifica("le perdite sono attribuite all'ambito",
             report.losses() == {"read": {"dbf_numeric_integer_precision_unverifiable": 3000}},
             str(report.losses()))

    # --- l'assenza di una dichiarazione non e' una dichiarazione di fedelta'
    muto = ConversionReport.parse({"from": "a", "to": "b", "total_rows": 1})
    verifica("senza `conversion_fidelity` non e' fedele",
             not muto.faithful, "faithful=False")

    return esiti


def main() -> int:
    esiti = prove()
    for nome, ok, dettaglio in esiti:
        marcatore = "  ok  " if ok else "  NO  "
        print(f"{marcatore}{nome:<44}{dettaglio}")
    falliti = [n for n, ok, _ in esiti if not ok]
    print(f"\n{len(esiti) - len(falliti)}/{len(esiti)} verifiche superate")
    return 1 if falliti else 0


if __name__ == "__main__":
    raise SystemExit(main())
