"""Confine Python verso i tre componenti Plenora.

Uno solo, non tre: ciò che il chiamante deve gestire — costruire l'invocazione,
leggere la busta a quattro assi, distinguere gli ambiti di perdita — è comune, e
tre copie sarebbero tre posti dove sbagliare le stesse cose.

Non è usato dai runner della conformità: il giudice resta indipendente da questo
codice.
"""

from .errors import (
    Category, MalformedEnvelope, Phase, PlenoraError, RemoteEffect, Retry,
    RetryKind, parse_error,
)
from .fidelity import ConversionReport, Fidelity, Level, Loss, Reason
from .components import (
    Component, catalog, convert, inspect, inspect_dataset, run_plan,
)

__all__ = [
    "Category", "Phase", "RemoteEffect", "Retry", "RetryKind",
    "PlenoraError", "MalformedEnvelope", "parse_error",
    "Fidelity", "Level", "Loss", "Reason", "ConversionReport",
    "Component", "convert", "inspect", "catalog", "run_plan", "inspect_dataset",
]
