"""Invocazione dei tre componenti dal backend Python.

I tre non si chiamano fra loro: l'orchestratore Python li invoca come processi e
si passa tabelle Arrow IPC. Questo modulo è quel confine, scritto una volta sola
invece che tre.

**Non è usato dai runner della conformità**, ed è deliberato: se il giudice
passasse da qui, un difetto di questo modulo maschererebbe un difetto di un
componente e la qualifica smetterebbe di essere indipendente. I runner invocano
direttamente; qui si condivide la conoscenza del contratto, non il codice del
giudizio.

Un vincolo scoperto eseguendo, non documentato altrove: `plenora-data-tools`
rifiuta di pubblicare su un filesystem che non riconosce — `f_type=0x1021997`,
cioè 9p, il modo in cui Docker Desktop monta i percorsi Windows. È R14 applicata
sul serio, e va saputo prima di scegliere dove finiscono gli intermedi.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .errors import MalformedEnvelope, parse_error
from .fidelity import ConversionReport


@dataclass(frozen=True)
class Component:
    """Un componente invocabile: dove sta e come si chiama.

    `features` esiste perché `plenora-data-tools` richiede `proj-backend` per
    risolvere i CRS e `geos-backend` per le operazioni topologiche: senza,
    rifiuta ogni dataset con `CRS_BACKEND_UNAVAILABLE`. È un dettaglio che è
    costato due esecuzioni della matrice di qualifica prima di essere notato.
    """

    name: str
    workspace: Path
    package: str
    features: tuple[str, ...] = ()

    def command(self, *arguments: str) -> list[str]:
        base = ["cargo", "run", "--locked", "--quiet", "-p", self.package]
        if self.features:
            base += ["--features", ",".join(self.features)]
        return base + ["--", *arguments]


def _run(component: Component, arguments: list[str]) -> dict:
    """Esegue e restituisce il documento JSON, o solleva l'errore tipizzato.

    Alcuni componenti scrivono la busta su stderr e altri su stdout: si guarda
    dove c'è, invece di assumere. È l'unica concessione all'eterogeneità che
    resta, e sparirà quando le sei buste della CLI saranno congelate.
    """
    completed = subprocess.run(component.command(*arguments),
                               cwd=component.workspace,
                               capture_output=True, text=True, check=False)
    for stream in (completed.stdout, completed.stderr):
        start = stream.find("{")
        if start < 0:
            continue
        payload = stream[start:].strip()
        try:
            document = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if document.get("status") == "error":
            raise parse_error(component.name, payload)
        if completed.returncode == 0:
            return document
    if completed.returncode != 0:
        raise MalformedEnvelope(
            f"{component.name} è uscito con {completed.returncode} senza una "
            f"busta interpretabile: "
            f"{(completed.stderr or completed.stdout).strip()[-300:]}")
    raise MalformedEnvelope(f"{component.name}: nessun JSON nell'uscita")


def convert(component: Component, source: Path, target: Path) -> ConversionReport:
    """Converte fra due formati. Il formato è dedotto dall'estensione.

    L'esito porta i tre ambiti di fedeltà separati: chiedere `report.faithful`
    risponde sulla conversione intera, non sul solo writer.
    """
    document = _run(component, ["convert", str(source), str(target)])
    return ConversionReport.parse(document)


def inspect(component: Component, source: Path) -> dict:
    """Apre una sorgente e riferisce cosa contiene, senza leggerla tutta."""
    return _run(component, ["inspect", str(source)])


def catalog(component: Component) -> dict:
    """Formati riconosciuti e capacità di ciascuno, interrogabili prima di
    scrivere: §10 esiste perché una capacità assente si scopra prima e non a
    metà lavorazione."""
    return _run(component, ["catalog"])


def run_plan(component: Component, plan: Path, inputs: Path, output: Path) -> dict:
    """Esegue un piano di trasformazione.

    Il piano è un dato, non codice: si versiona, si riesegue identico e si
    confronta con quello di ieri.
    """
    return _run(component, ["run", "--plan", str(plan),
                            "--inputs", str(inputs), "--output", str(output)])


def inspect_dataset(component: Component, source: Path) -> dict:
    """Contratto geometrico che un dataset Arrow produrrebbe al confine
    database, con l'ispezione EWKB di ogni cella. Offline: nessuna
    connessione."""
    return _run(component, ["inspect-dataset", str(source)])
