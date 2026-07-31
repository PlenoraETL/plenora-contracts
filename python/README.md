# Confine Python verso i tre componenti

Uno solo, non tre. Ciò che il chiamante deve gestire — costruire l'invocazione,
leggere la busta a quattro assi, distinguere gli ambiti di perdita — è comune ai
tre, e tre copie sarebbero tre posti dove sbagliare le stesse cose. È lo stesso
argomento di §15.3 dell'ICD, dal lato Python.

## Perché prima non si poteva scrivere

Fino al 31 luglio 2026 i tre esponevano gli errori in tre modi: IO-tools una
busta JSON con gli assi dentro la prosa italiana, database-tools testo semplice
con gli assi in prosa inglese, data-tools testo senza assi. Un wrapper avrebbe
dovuto ricostruire con espressioni regolari ciò che `R9.2` vieta di ricostruire:
*«la ritentabilità DEVE essere esplicita e non dedotta dal messaggio»*.

Ora tutti e tre emettono la stessa busta, `retry` incluso come oggetto taggato.
Questo modulo non contiene una sola espressione regolare.

## Perché non è usato dai runner della conformità

Deliberato. Se il giudice passasse da qui, un difetto di questo codice
maschererebbe un difetto di un componente. I runner invocano direttamente; qui
si condivide la conoscenza del contratto, non il codice del giudizio.

## Cosa risolve

**Gli ambiti di perdita restano distinti.** `write_loss.lossless` può essere
`true` mentre la conversione ha perso metà degli identificativi in lettura:
`report.faithful` guarda la fedeltà complessiva, che è la domanda che il
chiamante voleva fare.

**L'assenza di una dichiarazione non è una dichiarazione.** Un componente che
non emette `conversion_fidelity` non è fedele: è muto.

**I campi che non conosciamo si conservano.** `code`, `execution_id`, `provider`
finiscono in `context` senza essere interpretati — R2.4 vale anche qui.

## Uso

```python
from pathlib import Path
from plenora import Component, convert, PlenoraError

io = Component("IO-tools", Path("../plenora-IO-tools"), "plenora-io-cli")
data = Component("data-tools", Path("../plenora-data-tools"), "plenora-cli",
                 features=("proj-backend",))

try:
    report = convert(io, Path("particelle.shp"), Path("out.arrow"))
    if not report.faithful:
        print("perdite:", report.losses())
except PlenoraError as error:
    if error.retry.retryable:
        ...
    if error.committed_remotely:
        ...  # accertare lo stato prima di ripartire: `unknown` non è `none`
```

`features` non è opzionale per data-tools: senza `proj-backend` rifiuta ogni
dataset con `CRS_BACKEND_UNAVAILABLE`, e senza `geos-backend` le operazioni
topologiche non sono disponibili. È costato due esecuzioni della matrice di
qualifica prima di essere notato.

## Un vincolo scoperto eseguendo

`plenora-data-tools` rifiuta di pubblicare su un filesystem che non riconosce —
`f_type=0x1021997`, cioè 9p, il modo in cui Docker Desktop monta i percorsi
Windows. È R14 applicata sul serio, non un difetto. Va saputo prima di decidere
dove finiscono gli intermedi: NFS, volumi di rete e bind mount possono essere
rifiutati.

## Prove

```
python python/test_plenora.py
```

Dodici verifiche contro le buste **catturate eseguendo i tre CLI**, non scritte
a mano. Se un componente cambia forma lo dicono.
