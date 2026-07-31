"""La busta d'errore a quattro assi, letta come dati e non come prosa.

R9.2 dell'ICD: «la ritentabilità **DEVE** essere esplicita e non dedotta dal
messaggio. Un chiamante non deve interpretare del testo per decidere se
riprovare.» Fino al 31 luglio 2026 al confine CLI non era così — i tre
componenti esponevano gli assi in tre modi diversi, due dentro la prosa e uno
per niente — e questo modulo non si sarebbe potuto scrivere senza espressioni
regolari. Ora tutti e tre emettono la stessa busta.

I valori sono quelli serializzati dai tipi Rust, non una convenzione di questo
modulo: snake_case per categoria, fase ed effetto, e `retry` come oggetto
taggato perché la variante `after` porta una durata.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum


class Category(str, Enum):
    """Che cosa è andato storto. Enumerazione condivisa (R9.5): un componente
    può usarne un sottoinsieme, non può inventarne di proprie."""

    INVALID_PLAN = "invalid_plan"
    INVALID_CONFIGURATION = "invalid_configuration"
    SCHEMA = "schema"
    DATA_MAPPING = "data_mapping"
    CRS = "crs"
    UNSUPPORTED = "unsupported"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    RESOURCE_LIMIT = "resource_limit"
    IO = "io"
    PROTOCOL = "protocol"
    TRANSIENT = "transient"
    EXECUTION = "execution"
    INTERNAL = "internal"


class Phase(str, Enum):
    """A che punto della lavorazione ci si è fermati."""

    VALIDATE = "validate"
    CONNECT = "connect"
    PROBE = "probe"
    PREPARE = "prepare"
    READ = "read"
    WRITE = "write"
    FINALIZE = "finalize"
    COMMIT = "commit"
    ROLLBACK = "rollback"
    CLEANUP = "cleanup"


class RemoteEffect(str, Enum):
    """Che effetto ha avuto sul sistema remoto.

    `UNKNOWN` non è un fallimento del modello: è l'informazione che decide se si
    può ripartire da capo o serve prima accertare lo stato (R9.3).
    """

    NONE = "none"
    ROLLED_BACK = "rolled_back"
    PARTIAL = "partial"
    COMMITTED = "committed"
    UNKNOWN = "unknown"


class RetryKind(str, Enum):
    NEVER = "never"
    SAFE = "safe"
    REQUIRES_IDEMPOTENCY_KEY = "requires_idempotency_key"
    REQUIRES_RECOVERY = "requires_recovery"
    AFTER = "after"


@dataclass(frozen=True)
class Retry:
    """Disposizione di ritentabilità. `after` porta una durata: la variante
    esiste proprio perché «riprova più tardi» senza dire quando è metà
    informazione."""

    kind: RetryKind
    delay_ms: int | None = None

    @classmethod
    def parse(cls, value: object) -> "Retry":
        if isinstance(value, str):
            # Forma non taggata: nessun componente la emette più, ma una
            # versione più vecchia potrebbe. Accettarla senza la durata è
            # meglio che fallire, purché `after` resti riconoscibile.
            return cls(RetryKind(value))
        if not isinstance(value, dict) or "kind" not in value:
            raise MalformedEnvelope(f"campo `retry` non interpretabile: {value!r}")
        kind = RetryKind(value["kind"])
        delay = value.get("delay_ms")
        if kind is RetryKind.AFTER and delay is None:
            raise MalformedEnvelope(
                "`retry.kind` è `after` ma manca `delay_ms`: la disposizione "
                "dice di riprovare più tardi senza dire quando"
            )
        return cls(kind, int(delay) if delay is not None else None)

    @property
    def retryable(self) -> bool:
        """Vero solo dove riprovare è lecito senza altre condizioni."""
        return self.kind in (RetryKind.SAFE, RetryKind.AFTER)


class PlenoraError(Exception):
    """Errore di un componente, con i quattro assi come attributi.

    Il nome non collide con nulla di normativo: R9.8 vieta `PlenoraError` per il
    **tipo condiviso Rust** dei tre componenti, non per un'eccezione Python del
    chiamante.
    """

    def __init__(self, component: str, category: Category, phase: Phase,
                 remote_effect: RemoteEffect, retry: Retry, message: str,
                 context: dict | None = None) -> None:
        super().__init__(f"{component}: {category.value} in {phase.value} "
                         f"(effetto={remote_effect.value}, "
                         f"retry={retry.kind.value}): {message}")
        self.component = component
        self.category = category
        self.phase = phase
        self.remote_effect = remote_effect
        self.retry = retry
        self.detail = message
        self.context = context or {}

    @property
    def committed_remotely(self) -> bool:
        """Se l'effetto è ignoto, chi decide deve accertare lo stato prima di
        ripartire: `unknown` non è `none`."""
        return self.remote_effect in (RemoteEffect.COMMITTED,
                                      RemoteEffect.PARTIAL,
                                      RemoteEffect.UNKNOWN)


class MalformedEnvelope(PlenoraError):
    """La busta non è interpretabile. Non è un errore del componente: è un
    errore del confine, e va distinto perché non dice nulla sul dato."""

    def __init__(self, message: str) -> None:
        Exception.__init__(self, message)
        self.component = "?"
        self.category = Category.PROTOCOL
        self.phase = Phase.VALIDATE
        self.remote_effect = RemoteEffect.UNKNOWN
        self.retry = Retry(RetryKind.NEVER)
        self.detail = message
        self.context = {}


CORE_FIELDS = ("category", "phase", "remote_effect", "retry", "message")


def parse_error(component: str, payload: str) -> PlenoraError:
    """Costruisce l'eccezione dalla busta JSON di un componente.

    I campi oltre i cinque canonici — `code` in IO-tools, `execution_id` e
    `provider` in database-tools — sono contesto del componente e finiscono in
    `context` senza essere interpretati: R2.4 vale anche qui.
    """
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as error:
        raise MalformedEnvelope(f"uscita non JSON: {error}") from None
    if not isinstance(document, dict) or document.get("status") != "error":
        raise MalformedEnvelope(
            f"busta senza `status: error`: {str(document)[:120]}")
    body = document.get("error")
    if not isinstance(body, dict):
        raise MalformedEnvelope("busta senza oggetto `error`")

    missing = [k for k in CORE_FIELDS if k not in body]
    if missing:
        raise MalformedEnvelope(
            f"busta priva dei campi canonici {missing}: gli assi di R9.1 non "
            "sono ricostruibili, e R9.2 vieta di dedurli dal messaggio")
    try:
        return PlenoraError(
            component=component,
            category=Category(body["category"]),
            phase=Phase(body["phase"]),
            remote_effect=RemoteEffect(body["remote_effect"]),
            retry=Retry.parse(body["retry"]),
            message=str(body["message"]),
            context={k: v for k, v in body.items()
                     if k not in CORE_FIELDS and v is not None},
        )
    except ValueError as error:
        raise MalformedEnvelope(f"valore fuori dall'enumerazione condivisa: "
                                f"{error}") from None
