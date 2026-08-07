"""Giudice della campagna `error-axes-v1` (ICD R9.15-R9.18, R9.7).

Confronta l'osservazione di un componente con gli oracoli della campagna su tre
fronti:

1. **forma sul filo** — ogni valore di ogni asse si serializza esattamente come
   dichiarato, e l'elenco e' esaustivo per costruzione (i conteggi attesi sono
   nel manifesto, quindi un valore nuovo non dichiarato fa fallire la campagna);
2. **degradazione** — un valore non riconosciuto non fa cadere l'envelope, gli
   altri assi restano leggibili, e sugli assi che governano il comportamento si
   applica il valore conservativo;
3. **inoltro senza perdita** — un envelope che attraversa piu' componenti esce
   con i valori non compresi invariati.

Il terzo non e' verificabile da un componente solo: e' la ragione per cui
questa campagna esiste accanto ai gate interni dei tre repository.

Solo standard library.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

EXPECTED_CAMPAIGN = {
    "schema_version": 1,
    "campaign_id": "error-axes-v1",
    "contract": "plenora-error-axes-v1",
}


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


def _judge_wire_forms(campaign: Mapping[str, Any], observed: object) -> list[str]:
    """Ogni valore dichiarato deve serializzarsi esattamente come atteso."""
    failures: list[str] = []
    atteso = _mapping(campaign.get("wire_forms"), "campaign.wire_forms")
    osservato = _mapping(observed, "observation.wire_forms")

    for asse, spec in atteso.items():
        spec = _mapping(spec, f"campaign.wire_forms.{asse}")
        valori = _sequence(spec.get("values"), f"campaign.wire_forms.{asse}.values")

        # Esaustivita' per costruzione: il conteggio e' parte del contratto,
        # cosi' un valore aggiunto senza fissarne la forma non passa in
        # silenzio.
        conteggio = spec.get("expected_count")
        if len(valori) != conteggio:
            failures.append(
                f"wire_forms.{asse}: la campagna dichiara {conteggio} valori "
                f"ma ne elenca {len(valori)}"
            )

        if asse not in osservato:
            failures.append(f"wire_forms.{asse}: asse assente dall'osservazione")
            continue
        forme = _mapping(osservato[asse], f"observation.wire_forms.{asse}")

        dichiarati = {_mapping(v, "value")["value"] for v in valori}
        in_piu = set(forme) - dichiarati
        if in_piu:
            failures.append(
                f"wire_forms.{asse}: il componente emette valori non dichiarati "
                f"dalla campagna: {sorted(in_piu)}"
            )

        for voce in valori:
            voce = _mapping(voce, f"campaign.wire_forms.{asse}.values[]")
            nome, forma = voce["value"], voce["wire"]
            if nome not in forme:
                failures.append(f"wire_forms.{asse}.{nome}: non osservato")
            elif forme[nome] != forma:
                failures.append(
                    f"wire_forms.{asse}.{nome}: atteso {forma!r}, "
                    f"osservato {forme[nome]!r}"
                )
    return failures


def _judge_degradation(campaign: Mapping[str, Any], observed: object) -> list[str]:
    """Un valore ignoto non deve far cadere l'envelope (R9.16-R9.17)."""
    failures: list[str] = []
    casi = {
        _mapping(c, "case")["id"]: _mapping(c, "case")
        for c in _sequence(campaign.get("degradation_cases"), "campaign.degradation_cases")
    }
    vietati = _mapping(
        campaign.get("forbidden_degradations", {}), "campaign.forbidden_degradations"
    )
    osservati = {
        _mapping(o, "observation")["id"]: _mapping(o, "observation")
        for o in _sequence(observed, "observation.degradation_cases")
    }

    mancanti = set(casi) - set(osservati)
    if mancanti:
        failures.append(f"degradation: casi non osservati: {sorted(mancanti)}")

    for identificativo, caso in casi.items():
        osservazione = osservati.get(identificativo)
        if osservazione is None:
            continue
        atteso = _mapping(caso.get("expected"), f"{identificativo}.expected")

        for campo, valore in atteso.items():
            if campo not in osservazione:
                failures.append(f"{identificativo}: campo {campo} non riportato")
            elif osservazione[campo] != valore:
                failures.append(
                    f"{identificativo}.{campo}: atteso {valore!r}, "
                    f"osservato {osservazione[campo]!r}"
                )

        # Il divieto e' esplicito perche' sono le letture che autorizzano
        # l'azione piu' rischiosa proprio quando l'informazione manca.
        for asse, proibiti in vietati.items():
            effettivo = osservazione.get(f"{asse}_effective")
            if effettivo in proibiti:
                failures.append(
                    f"{identificativo}: {asse} degradato a {effettivo!r}, "
                    f"vietato da R9.17"
                )
    return failures


def _judge_relay(campaign: Mapping[str, Any], observed: object) -> list[str]:
    """Chi inoltra ritrasmette invariato cio' che non ha compreso (R9.16)."""
    failures: list[str] = []
    casi = {
        _mapping(c, "case")["id"]: _mapping(c, "case")
        for c in _sequence(campaign.get("relay_cases"), "campaign.relay_cases")
    }
    osservati = {
        _mapping(o, "observation")["id"]: _mapping(o, "observation")
        for o in _sequence(observed, "observation.relay_cases")
    }

    mancanti = set(casi) - set(osservati)
    if mancanti:
        failures.append(f"relay: casi non osservati: {sorted(mancanti)}")

    for identificativo, caso in casi.items():
        osservazione = osservati.get(identificativo)
        if osservazione is None:
            continue
        catena = _sequence(caso.get("chain"), f"{identificativo}.chain")
        atteso = _mapping(
            caso.get("expected_at_each_hop"), f"{identificativo}.expected_at_each_hop"
        )
        salti = _sequence(osservazione.get("hops"), f"{identificativo}.hops")

        if len(salti) != len(catena):
            failures.append(
                f"{identificativo}: la catena dichiara {len(catena)} salti, "
                f"osservati {len(salti)}"
            )

        for indice, salto in enumerate(salti):
            salto = _mapping(salto, f"{identificativo}.hops[{indice}]")
            componente = salto.get("component", f"salto {indice}")
            envelope = _mapping(salto.get("envelope"), f"{identificativo}.hops[{indice}].envelope")
            for campo, valore in atteso.items():
                if envelope.get(campo) != valore:
                    failures.append(
                        f"{identificativo}: dopo {componente} il campo {campo} "
                        f"vale {envelope.get(campo)!r}, atteso {valore!r}"
                    )
    return failures


def judge_campaign(campaign: object, observation: object) -> dict[str, object]:
    """Giudica un'osservazione contro il manifesto della campagna.

    Restituisce `{"status": "pass"|"fail", "failures": [...]}`. Il giudizio e'
    deterministico e non tocca il filesystem.
    """
    manifesto = _mapping(campaign, "campaign")
    divergenze = {
        campo: manifesto.get(campo)
        for campo, atteso in EXPECTED_CAMPAIGN.items()
        if manifesto.get(campo) != atteso
    }
    if divergenze:
        return {
            "status": "fail",
            "failures": [f"campagna non riconosciuta: {divergenze}"],
        }

    osservazione = _mapping(observation, "observation")
    guasti: list[str] = []
    guasti += _judge_wire_forms(manifesto, osservazione.get("wire_forms", {}))
    guasti += _judge_degradation(manifesto, osservazione.get("degradation_cases", []))
    guasti += _judge_relay(manifesto, osservazione.get("relay_cases", []))

    return {
        "status": "pass" if not guasti else "fail",
        "component": osservazione.get("component"),
        "failures": guasti,
    }
