# data

data trasforma tabelle Arrow con un piano dichiarativo: input nominati, passi
e output nominati. Prima si scoprono i kernel disponibili, poi si valida il
piano, infine lo si esegue. La validazione non produce le tabelle di risultato.

## Le operazioni

Il [catalogo pubblico](../catalogs/data-tools-v3.json) fissa le righe seguenti.
Nella tabella, **J** = `application/json`, **S** =
`application/vnd.apache.arrow.stream`, **F** =
`application/vnd.apache.arrow.file`. I controlli sono, nell'ordine,
`cancellation` / `deadline` / `idempotency_key` (sì o no).
I valori di `side_effect` sono quelli del catalogo, anche quando la CLI
materializza un file locale.

| id@versione | sintesi | ingresso: contratto · content type | uscita: contratto · content type | side_effect | controlli |
| --- | --- | --- | --- | --- | --- |
| `data.catalog@2` | Elenca kernel, versioni e disponibilità. | `plenora-data-catalog-query-v1` · J | `plenora-data-catalog-result-v2` · J | `none` | no / no / no |
| `data.describe@1` | Descrive una tabella Arrow. | `plenora-data-describe-input-v1` · S, F | `plenora-data-description-v1` · J | `none` | sì / sì / no |
| `data.validate@2` | Valida il piano contro i contratti degli input nominati. | `plenora-data-plan-validation-input-v2` · J, S, F | `plenora-data-plan-validation-result-v1` · J | `none` | sì / sì / no |
| `data.run@2` | Esegue il piano e consegna gli output Arrow nominati. | `plenora-data-execution-input-v2` · J, S, F | `plenora-data-execution-result-v2` · S, F | `local` | sì / sì / no |
| `data.run@3` | Esegue su artefatti e restituisce il manifesto delle pubblicazioni. | `plenora-data-execution-input-v3` · J | `plenora-data-execution-result-v3` · J | `remote` | sì / sì / no |

I passaggi Arrow dichiarano `plenora-arrow-interchange-v1`: schema e
metadati fanno parte dello scambio, come spiegato in [insieme](insieme.md).

`data.run@3` è condizionale e non ha comando CLI né funzione Python:
scambia riferimenti ad artefatti e un manifesto JSON. Le due superfici
qui sotto espongono `data.run@2`. Parquet
(`application/vnd.apache.parquet`) è un'estensione dichiarata per gli
input di describe/validate/run e per gli output di run.

## La CLI

Un piano `piano.json`, nella forma documentata dall'SDK:

```json
{
  "version": 1,
  "inputs": ["t"],
  "steps": [
    {"out": "alti", "op": "table.filter", "in": ["t"],
     "config": {"column": "id", "operator": ">", "value": 1}},
    {"out": "ordinati", "op": "table.sort", "in": ["alti"],
     "config": {"columns": ["id"]}}
  ],
  "outputs": ["alti", "ordinati"]
}
```

Con `dati.arrow` contenente una colonna `id` numerica:

```sh
plenora-data catalog --format json
plenora-data describe --input dati.arrow --format json
plenora-data validate --plan piano.json --input t=dati.arrow --format json
plenora-data run --plan piano.json --input t=dati.arrow --output alti=alti.arrow --output ordinati=ordinati.arrow --timeout-ms 30000 --format json
```

Il nome prima di `=` è quello del piano. Con un solo output è ammesso
`--output risultato.arrow`; con più output si nominano tutte le destinazioni.
Un file esistente è `conflict` senza `--overwrite`. L'estensione sceglie il
formato: `.arrow`, `.feather` e `.ipc` per IPC file, `.arrows` per stream,
`.parquet` per Parquet.

`validate` controlla il piano senza eseguire i passi. Il catalogo ne descrive
la validazione sui contratti; la CLI documenta comunque il caricamento degli
input: non è una promessa di zero letture fisiche. `--deadline` e
`--timeout-ms` sono alternativi.

Per busta ed exit code si vedano le [fondamenta](fondamenta.md). Qui anche
senza `--format json` i comandi operativi producono JSON. Gli alias deprecati
presenti nel binding, come `transform`, non sono accettati dalla CLI corrente.
Un annullamento dopo l'ultima scrittura resta un errore, con effetto
`committed`, non un successo.

## L'SDK Python

La distribuzione è `plenora-data`, l'import `plenora_data`; si installa la
wheel per la propria piattaforma. La superficie accetta tabelle Arrow in
memoria e percorsi IPC o Parquet.

```python
import pyarrow as pa
import plenora_data as pd

tabella = pa.table({"id": [3, 1, 2], "importo": [3.5, 1.0, 2.25]})
piano = {
    "version": 1,
    "inputs": ["t"],
    "steps": [{"out": "ordinati", "op": "table.sort", "in": ["t"],
               "config": {"columns": ["id"]}}],
    "outputs": ["ordinati"],
}
descrizione = pd.describe(tabella)
validazione = pd.validate(piano, {"t": tabella})
risultato = pd.run(piano, {"t": tabella}, timeout=30)
ordinati = risultato.tables["ordinati"]
```

`catalog()` restituisce un dizionario; `describe(data, ...)` e
`validate(plan, inputs, ...)` restituiscono i documenti descrittivi.
`run(plan, inputs, *, outputs=..., overwrite=..., ...)` restituisce
`RunResult(result, tables)`. Omettendo `outputs` si ricevono tabelle;
con `outputs={"ordinati": "ordinati.arrow"}` si scrivono file e `tables`
resta vuoto. `overwrite` senza destinazioni è rifiutato.

Il piano può essere un mapping, testo JSON oppure `pathlib.Path`.
Una stringa è testo JSON, non un percorso. Gli equivalenti asincroni sono
`acatalog`, `adescribe`, `avalidate`, `arun`. Describe, validate e run
accettano `timeout` in secondi oppure `deadline` con fuso orario, e
`cancel=CancellationToken()`.

Gli errori derivano da `PlenoraError`, con sottoclassi quali
`PlenoraTimeoutError`, `PlenoraCancelledError` e `PlenoraResourceLimitError`.
Gli attributi includono `category`, `phase`, `remote_effect`, `retry`,
`code` e `details`; `to_dict()` dà il documento completo. L'annullamento di
un task attende l'arresto del lavoro e propaga `asyncio.CancelledError`, con
l'esito come causa.

## I rifiuti e i limiti

- **Una geometria**: il contratto ammette una sola colonna geometrica.
  Non basta scegliere quale usare lasciandone altre dichiarate nello schema.
- **Materializzazione limitata**: le tabelle stanno intere in memoria,
  entro il budget. Un ingresso a batch non promette elaborazione illimitata
  né un tetto rigido all'RSS del processo.
- **Kernel**: essere nel catalogo non significa essere disponibile.
  `table.transpose` è dichiarato `unavailable`.
- **Parquet**: anche file validi possono essere rifiutati se usano codifiche
  non qualificate, fra cui `DELTA_BINARY_PACKED` e `BYTE_STREAM_SPLIT`.
- **Più output**: la pubblicazione è atomica per file, non una transazione
  unica su tutte le destinazioni. Si esamina l'effetto prima di ritentare.

## Fonti

- [Catalogo data v3](../catalogs/data-tools-v3.json) e
  [catalogo dei kernel](../catalogs/data-kernels-v2.json).
- [Binding CLI](../bindings/cli-v1.json) e
  [binding Python](../bindings/python-sdk-v1.json).
- Repository locale `C:/pg/dt-rel`: `docs/cli.md`, `docs/file.md`,
  `docs/limiti.md` e `crates/plenora-data-py/README.md` (documentazione SDK).
