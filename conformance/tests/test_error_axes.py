"""Il giudice della campagna `error-axes-v1`, e la prova che sappia bocciare.

La seconda meta' di questo file e' un gate di mutazione: costruisce
un'osservazione conforme, la rompe in un punto per volta, e verifica che il
giudice se ne accorga. Un giudice che non boccia non e' un gate, e la campagna
`error-axes-v1` nasce proprio perche' un oracolo mai confrontato con
un'osservazione reale aveva lasciato passare tre contraddizioni.
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "conformance" / "campaigns" / "error-axes-v1" / "cases.json"
JUDGE = ROOT / "conformance" / "judge_error_axes.py"


def _judge():
    spec = importlib.util.spec_from_file_location("judge_error_axes", JUDGE)
    if spec is None or spec.loader is None:
        raise RuntimeError("judge_error_axes is not loadable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.judge_campaign


def _campaign() -> dict:
    return json.loads(CASES.read_text(encoding="utf-8"))


def _conformant_observation(campaign: dict) -> dict:
    """Osservazione che rispetta il contratto in ogni punto.

    E' costruita dagli oracoli, quindi non dimostra che un componente sia
    conforme: dimostra che il giudice accetta cio' che deve accettare. La
    conformita' dei componenti si misura con le loro osservazioni reali.
    """
    forme = {
        asse: {v["value"]: v["wire"] for v in spec["values"]}
        for asse, spec in campaign["wire_forms"].items()
    }
    degradazioni = [
        {"id": caso["id"], **caso["expected"]} for caso in campaign["degradation_cases"]
    ]
    inoltri = [
        {
            "id": caso["id"],
            "hops": [
                {"component": componente, "envelope": deepcopy(caso["envelope"])}
                for componente in caso["chain"]
            ],
        }
        for caso in campaign["relay_cases"]
    ]
    return {
        "component": "oracolo",
        "wire_forms": forme,
        "degradation_cases": degradazioni,
        "relay_cases": inoltri,
    }


class ErrorAxesJudgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.judge = _judge()
        self.campaign = _campaign()
        self.observation = _conformant_observation(self.campaign)

    def test_un_osservazione_conforme_passa(self) -> None:
        esito = self.judge(self.campaign, self.observation)
        self.assertEqual(esito["failures"], [])
        self.assertEqual(esito["status"], "pass")

    def test_la_campagna_dichiara_i_conteggi_degli_assi(self) -> None:
        """L'esaustivita' e' per costruzione: se i conteggi non corrispondono
        all'elenco, un valore aggiunto senza forma dichiarata passerebbe."""
        for asse, spec in self.campaign["wire_forms"].items():
            self.assertEqual(
                len(spec["values"]),
                spec["expected_count"],
                f"{asse}: conteggio e elenco divergono nel manifesto",
            )

    def test_il_vocabolario_sul_filo_e_snake_case(self) -> None:
        """R9.15: i valori viaggiano in `snake_case` su tutti e quattro gli assi.

        E' la contraddizione che aveva diviso oracoli e implementazioni: le
        tabelle dell'ICD scrivono la categoria in PascalCase, i componenti
        emettono `snake_case`.
        """
        for asse, spec in self.campaign["wire_forms"].items():
            for voce in spec["values"]:
                forma = voce["wire"]
                testo = forma["kind"] if isinstance(forma, dict) else forma
                self.assertEqual(
                    testo,
                    testo.lower(),
                    f"{asse}.{voce['value']}: la forma sul filo non e' snake_case",
                )
                self.assertNotIn(
                    " ", testo, f"{asse}.{voce['value']}: spazio nella forma sul filo"
                )


class MutationGateTest(unittest.TestCase):
    """Ogni prova rompe l'osservazione in un punto e pretende una bocciatura."""

    def setUp(self) -> None:
        self.judge = _judge()
        self.campaign = _campaign()
        self.observation = _conformant_observation(self.campaign)

    def _boccia(self, osservazione: dict, atteso: str) -> None:
        esito = self.judge(self.campaign, osservazione)
        self.assertEqual(esito["status"], "fail", "il giudice non ha bocciato")
        self.assertTrue(
            any(atteso in guasto for guasto in esito["failures"]),
            f"nessun guasto contiene {atteso!r}: {esito['failures']}",
        )

    def test_boccia_una_forma_sul_filo_sbagliata(self) -> None:
        rotta = deepcopy(self.observation)
        rotta["wire_forms"]["category"]["data_mapping"] = "DataMapping"
        self._boccia(rotta, "wire_forms.category.data_mapping")

    def test_boccia_un_valore_d_asse_non_dichiarato(self) -> None:
        rotta = deepcopy(self.observation)
        rotta["wire_forms"]["retry"]["quarantine"] = {"kind": "quarantine"}
        self._boccia(rotta, "non dichiarati")

    def test_boccia_una_forma_mancante(self) -> None:
        rotta = deepcopy(self.observation)
        del rotta["wire_forms"]["remote_effect"]["unknown"]
        self._boccia(rotta, "wire_forms.remote_effect.unknown")

    def test_boccia_un_envelope_che_cade_su_un_valore_ignoto(self) -> None:
        """R9.16: e' il difetto reale del 2026-08-07."""
        rotta = deepcopy(self.observation)
        caso = next(
            c for c in rotta["degradation_cases"] if c["id"] == "retry-quarantine-da-database-tools"
        )
        caso["readable"] = False
        self._boccia(rotta, "readable")

    def test_boccia_una_degradazione_verso_un_valore_vietato(self) -> None:
        """R9.17: leggere l'ignoto come `safe` autorizza l'azione piu'
        rischiosa proprio quando l'informazione manca."""
        rotta = deepcopy(self.observation)
        caso = next(
            c for c in rotta["degradation_cases"] if c["id"] == "retry-valore-inventato"
        )
        caso["retry_effective"] = "safe"
        self._boccia(rotta, "vietato da R9.17")

    def test_boccia_la_perdita_del_valore_ricevuto(self) -> None:
        rotta = deepcopy(self.observation)
        caso = next(
            c for c in rotta["degradation_cases"] if c["id"] == "remote-effect-inventato"
        )
        caso["remote_effect_received"] = "unknown"
        self._boccia(rotta, "remote_effect_received")

    def test_boccia_un_caso_di_degradazione_non_osservato(self) -> None:
        rotta = deepcopy(self.observation)
        rotta["degradation_cases"] = rotta["degradation_cases"][:-1]
        self._boccia(rotta, "casi non osservati")

    def test_boccia_l_inoltro_che_normalizza_cio_che_non_ha_capito(self) -> None:
        """R9.16: il destinatario successivo potrebbe comprenderlo."""
        rotta = deepcopy(self.observation)
        caso = next(c for c in rotta["relay_cases"] if c["id"] == "inoltro-di-quarantine")
        caso["hops"][1]["envelope"]["retry"] = {"kind": "requires_recovery"}
        self._boccia(rotta, "dopo data-tools")

    def test_boccia_una_catena_troncata(self) -> None:
        rotta = deepcopy(self.observation)
        caso = next(c for c in rotta["relay_cases"] if c["id"] == "inoltro-di-quarantine")
        caso["hops"] = caso["hops"][:2]
        self._boccia(rotta, "salti")

    def test_boccia_una_campagna_diversa(self) -> None:
        manifesto = deepcopy(self.campaign)
        manifesto["campaign_id"] = "qualcos-altro"
        esito = self.judge(manifesto, self.observation)
        self.assertEqual(esito["status"], "fail")


if __name__ == "__main__":
    unittest.main()
