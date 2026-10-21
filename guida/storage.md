# storage

storage trasferisce file e ne descrive i metadati. Non interpreta CSV, Arrow
o geometrie: per quello il file scaricato passa a IO. Local, S3, Azure, GCS,
FTP/FTPS, SFTP, SMB e WebDAV condividono le operazioni, ma non tutte le
garanzie di pubblicazione.

## Le operazioni

Il [catalogo pubblico](../catalogs/storage-tools-v1.json) fissa le righe seguenti.
Nella tabella, **J** = `application/json`, **S** =
`application/vnd.apache.arrow.stream`, **F** =
`application/vnd.apache.arrow.file`. I controlli sono, nell'ordine,
`cancellation` / `deadline` / `idempotency_key` (sì o no).
I valori di `side_effect` sono quelli del catalogo, anche quando la CLI
materializza un file locale.

| id@versione | sintesi | ingresso: contratto · content type | uscita: contratto · content type | side_effect | controlli |
| --- | --- | --- | --- | --- | --- |
| `storage.test@1` | Verifica raggiungibilità con lavoro limitato. | `plenora-storage-test-input-v1` · J | `plenora-storage-test-output-v1` · J | `none` | sì / sì / no |
| `storage.list@1` | Elenca oggetti con cursore opaco, senza snapshot. | `plenora-storage-list-input-v1` · J | `plenora-storage-list-output-v1` · J | `none` | sì / sì / no |
| `storage.stat@1` | Legge i metadati senza scaricare i byte. | `plenora-storage-stat-input-v1` · J | `plenora-storage-stat-output-v1` · J | `none` | sì / sì / no |
| `storage.get@1` | Scarica in una destinazione autorizzata e riporta integrità. | `plenora-storage-get-input-v1` · J | `plenora-storage-get-output-v1` · J | `remote` | sì / sì / no |
| `storage.put@1` | Carica una sorgente autorizzata con policy esplicita. | `plenora-storage-put-input-v1` · J | `plenora-storage-put-output-v1` · J | `remote` | sì / sì / no |
| `storage.copy@1` | Copia fra chiavi della stessa connessione. | `plenora-storage-copy-input-v1` · J | `plenora-storage-copy-output-v1` · J | `remote` | sì / sì / no |
| `storage.delete@1` | Elimina con comportamento esplicito se l'oggetto manca. | `plenora-storage-delete-input-v1` · J | `plenora-storage-delete-output-v1` · J | `remote` | sì / sì / no |

Tutte le richieste e risposte sono JSON. I byte dei file non sono incorporati
nel documento: get e put li trasferiscono separatamente e riportano SHA-256.
Il catalogo classifica `get` come `remote`, anche quando la destinazione è
un file locale. Per comporlo con IO si veda [insieme](insieme.md).

## La CLI

Un esempio senza credenziali remote parte da `locale.json`. La directory
`C:/dati/storage` deve già esistere:

```json
{
  "provider": "local",
  "config_contract": "plenora-storage-local-connection-v1",
  "config": {"root": "C:/dati/storage"},
  "credential_ref": "local:process"
}
```

Con `report.csv` presente nella directory di lavoro:

```sh
plenora-storage test --connection locale.json --format json
plenora-storage list --connection locale.json --all --max-items 100 --format json
plenora-storage put --connection locale.json --key report.csv --input report.csv --overwrite false --publication-policy atomic-required --format json
plenora-storage stat --connection locale.json --key report.csv --format json
plenora-storage get --connection locale.json --key report.csv --output copia.csv --overwrite false --format json
plenora-storage copy --connection locale.json --source-key report.csv --destination-key archivio.csv --overwrite false --publication-policy atomic-required --format json
plenora-storage delete --connection locale.json --key archivio.csv --ignore-missing false --format json
```

`--overwrite`, `--publication-policy` e `--ignore-missing` sono obbligatori
quando applicabili. Non esiste un default implicito per queste decisioni.
Il binding comune conserva `--allow-experimental-contracts`; il repository
corrente documenta che non serve più e resta accettato per compatibilità.

`list --all` mantiene la sessione per l'enumerazione, entro i limiti di
numero di oggetti. Senza `--all`, una pagina incompleta produce errore;
un cursore non si può riutilizzare fra processi CLI distinti. Per busta
ed exit code si vedano le [fondamenta](fondamenta.md).

## L'SDK Python

La distribuzione è `plenora-storage`, l'import `plenora_storage`. Si installa
la wheel scaricata per la piattaforma. Il seguente esempio presuppone la
root `storage` già esistente e `report.csv` leggibile:

```python
from pathlib import Path
from plenora_storage import Connection, Engine

connection = Connection(
    "local", "plenora-storage-local-connection-v1",
    {"root": str(Path("storage").resolve())}, "local:process",
)
with Engine() as engine:
    esito = engine.put(
        connection, "report.csv", "report.csv", overwrite=False,
        publication_policy="atomic_required", timeout_ms=5000,
    )
    scaricato = engine.get(connection, "report.csv", "copia.csv", overwrite=False)
```

Le firme d'uso sono `test(connection, ...)`, `list(connection, ...)`,
`stat(connection, key, ...)`, `get(connection, key, output, ...)`,
`put(connection, key, input, ...)`, `copy(connection, source_key, destination_key, ...)`
e `delete(connection, key, ...)`; negli esempi i percorsi sono posizionali.
I controlli comuni sono `timeout_ms` e `cancellation=CancellationToken()`.
Le policy Python sono `atomic_required` e `best_effort`, con underscore;
la CLI usa il trattino.

I risultati sono dizionari tipizzati, con metadati non disponibili a `None`.
`list` restituisce una pagina e un cursore del medesimo engine; `copy`
opera dentro una connessione. Le credenziali remote si risolvono da
`env:NAME` o tramite `Engine(credential_resolver=callback)`; il riferimento
non è il segreto.

`AsyncEngine` offre gli stessi metodi con `await` e `async with`.
L'annullamento di un task attende l'esito dell'operazione;
`cancellation_outcome(error)` restituisce il risultato, un `PlenoraError`
o `None`. Quest'ultimo non dimostra assenza di effetti.
`StorageError`, sottoclasse di `PlenoraError`, espone `code`, `category`,
`phase`, `remote_effect`, `retry` e `provider`.

## I rifiuti e i limiti

- **Pubblicazione**: FTP e FTPS rifiutano `overwrite=false` e
  `atomic-required`. Non sostituiscono la garanzia con un controllo preliminare.
  `copy` rifiuta sorgente e destinazione uguali prima della mutazione.
- **Elenchi**: il cursore è opaco e legato alla richiesta e all'engine;
  la paginazione non offre isolamento snapshot.
- **Rete**: reti private, FTP in chiaro e host key non verificata richiedono
  autorizzazioni distinte. I client HTTP non seguono redirect né usano proxy.
- **Dimensioni**: put/copy su local, Azure, GCS, SMB e WebDAV hanno limiti
  di buffering predefiniti. `--spool-uploads`, oppure
  `Engine(spool_uploads=True)`, abilita la preparazione su disco conservando
  i vincoli di pubblicazione. Non elimina il limite totale del trasferimento.
- **Conferma persa**: su S3, SFTP e FTP/FTPS alcuni errori di mutazione
  possono risultare `execution` anziché `io`; restano `unknown` e
  `requires_recovery`. La sola categoria non basta per decidere il recupero.
- **Callback Python**: il resolver delle credenziali deve terminare in
  tempo limitato; non può essere interrotto forzatamente.

## Fonti

- [Catalogo storage v1](../catalogs/storage-tools-v1.json).
- [Binding CLI](../bindings/cli-v1.json) e
  [binding Python](../bindings/python-sdk-v1.json).
- Repository locale `C:/pg/st-rel`: `README.md`, `docker/local-connection.json`,
  `docs/contract-limits.md` e `crates/plenora-storage-py/README.md`
  (documentazione SDK).
