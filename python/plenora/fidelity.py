"""Perdita e fedeltà, con l'ambito esplicito.

Fino al 31 luglio 2026 `convert` esponeva un solo campo `loss` con un booleano
`lossless` che descriveva **il solo writer**: su una conversione da shapefile che
perdeva precisione su 3.000 identificativi diceva `true`, mentre due righe sotto
`read_fidelity` diceva `approximating`. Chi leggeva il campo dal nome più ovvio
concludeva che la conversione era fedele.

Ora gli ambiti sono tre e distinti — lettura, scrittura, conversione — e questo
modulo li tiene distinti anche in Python invece di riassumerli in un booleano.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Level(str, Enum):
    LOSSLESS = "lossless"
    CONDITIONAL = "conditional"
    APPROXIMATING = "approximating"


@dataclass(frozen=True)
class Reason:
    code: str
    detail: str


@dataclass(frozen=True)
class Fidelity:
    """Valutazione di fedeltà su un ambito. `reasons` non è decorativo: è dove
    si legge *cosa* si è degradato, non solo che qualcosa lo ha fatto."""

    level: Level
    reasons: tuple[Reason, ...] = ()

    @classmethod
    def parse(cls, payload: dict | None) -> "Fidelity | None":
        if not payload:
            return None
        return cls(
            level=Level(payload["level"]),
            reasons=tuple(Reason(r.get("code", ""), r.get("detail", ""))
                          for r in payload.get("reasons", [])),
        )

    @property
    def faithful(self) -> bool:
        return self.level is Level.LOSSLESS


@dataclass(frozen=True)
class Loss:
    """Rapporto di perdita su un ambito preciso.

    `counts` è una mappa da categoria a occorrenze: `lossless` da solo dice che
    non si è perso nulla **in quell'ambito**, e il nome dell'attributo non lo
    lascia dimenticare.
    """

    scope: str
    counts: dict[str, int]
    lossless: bool

    @classmethod
    def parse(cls, scope: str, payload: dict | None) -> "Loss | None":
        if payload is None:
            return None
        return cls(scope=scope,
                   counts=dict(payload.get("counts") or {}),
                   lossless=bool(payload.get("lossless", False)))

    def __bool__(self) -> bool:
        return not self.lossless


@dataclass(frozen=True)
class ConversionReport:
    """Esito di una conversione, con i tre ambiti separati.

    `faithful` guarda **la fedeltà complessiva**, non quella del writer: è la
    domanda che chi chiama voleva fare, ed è l'unica risposta che tiene conto di
    ciò che si è perso in lettura.
    """

    source_format: str
    target_format: str
    rows: int
    read_loss: Loss | None
    write_loss: Loss | None
    read_fidelity: Fidelity | None
    write_fidelity: Fidelity | None
    conversion_fidelity: Fidelity | None
    raw: dict

    @classmethod
    def parse(cls, document: dict) -> "ConversionReport":
        return cls(
            source_format=document.get("from", ""),
            target_format=document.get("to", ""),
            rows=int(document.get("total_rows", 0)),
            read_loss=Loss.parse("read", document.get("read_loss")),
            write_loss=Loss.parse("write", document.get("write_loss")),
            read_fidelity=Fidelity.parse(document.get("read_fidelity")),
            write_fidelity=Fidelity.parse(document.get("write_fidelity")),
            conversion_fidelity=Fidelity.parse(document.get("conversion_fidelity")),
            raw=document,
        )

    @property
    def faithful(self) -> bool:
        """Fedele end-to-end. Se il componente non dichiara la fedeltà
        complessiva la risposta è `False`: l'assenza di una dichiarazione non è
        una dichiarazione di fedeltà."""
        return bool(self.conversion_fidelity and self.conversion_fidelity.faithful)

    def losses(self) -> dict[str, dict[str, int]]:
        """Tutte le perdite, per ambito. Vuoto significa nessuna perdita
        dichiarata — che non è lo stesso di nessuna perdita, se il componente
        non ha letto ciò che trasporta."""
        return {loss.scope: loss.counts
                for loss in (self.read_loss, self.write_loss)
                if loss is not None and loss.counts}
