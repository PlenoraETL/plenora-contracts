# database

database legge e scrive tabelle, interroga gli oggetti visibili e gestisce
transazioni. Il provider conta: una modalità o un tipo disponibili su un
database non sono una promessa per tutti gli altri. Le capacità della
connessione sono il punto da cui partire.

## Le operazioni

Il [catalogo pubblico](../catalogs/database-tools-v2.json) fissa le righe seguenti.
Nella tabella, **J** = `application/json`, **S** =
`application/vnd.apache.arrow.stream`, **F** =
`application/vnd.apache.arrow.file`. I controlli sono, nell'ordine,
`cancellation` / `deadline` / `idempotency_key` (sì o no).
I valori di `side_effect` sono quelli del catalogo, anche quando la CLI
materializza un file locale.

| id@versione | sintesi | ingresso: contratto · content type | uscita: contratto · content type | side_effect | controlli |
| --- | --- | --- | --- | --- | --- |
| `database.test_connection@1` | Verifica connessione e capacità senza esporre credenziali. | `plenora-database-connection-test-input-v1` · J | `plenora-database-connection-test-result-v1` · J | `none` | sì / sì / no |
| `database.list_catalogs@1` | Elenca i cataloghi visibili. | `plenora-database-list-catalogs-input-v1` · J | `plenora-database-list-catalogs-result-v1` · J | `none` | sì / sì / no |
| `database.list_schemas@1` | Elenca gli schemi, eventualmente in un catalogo. | `plenora-database-list-schemas-input-v1` · J | `plenora-database-list-schemas-result-v1` · J | `none` | sì / sì / no |
| `database.list_objects@1` | Elenca tabelle, viste e oggetti equivalenti. | `plenora-database-list-objects-input-v1` · J | `plenora-database-list-objects-result-v1` · J | `none` | sì / sì / no |
| `database.describe_object@1` | Descrive schema e capacità di un oggetto. | `plenora-database-describe-object-input-v1` · J | `plenora-database-describe-object-result-v1` · J | `none` | sì / sì / no |
| `database.read@1` | Legge proiezione e filtro limitati in Arrow. | `plenora-database-read-input-v1` · J | `plenora-database-read-result-v1` · S, F | `none` | sì / sì / no |
| `database.write@1` | Scrive Arrow con modalità, mapping e profilo transazionale espliciti. | `plenora-database-write-input-v1` · J, S, F | `plenora-database-write-result-v1` · J | `remote` | sì / sì / no |
| `database.query@1` | Esegue una query portabile. | `plenora-database-query-input-v1` · J | `plenora-database-query-result-v1` · J, S | `none` | sì / sì / no |
| `database.execute@1` | Esegue uno statement con rendicontazione prudente degli effetti. | `plenora-database-execute-input-v1` · J | `plenora-database-execute-result-v1` · J | `remote` | sì / sì / no |
| `database.transaction.begin@1` | Apre una transazione del chiamante. | `plenora-database-transaction-begin-input-v1` · J | `plenora-database-transaction-handle-v1` · J | `remote` | sì / sì / no |
| `database.transaction.commit@1` | Conferma la transazione, anche quando l'esito è ambiguo. | `plenora-database-transaction-handle-v1` · J | `plenora-database-transaction-outcome-v1` · J | `remote` | no / sì / no |
| `database.transaction.rollback@1` | Annulla la transazione e riporta la conferma. | `plenora-database-transaction-handle-v1` · J | `plenora-database-transaction-outcome-v1` · J | `remote` | no / sì / no |
| `database.transaction.savepoint@1` | Crea, rilascia o ripristina un savepoint. | `plenora-database-savepoint-input-v1` · J | `plenora-database-transaction-outcome-v1` · J | `remote` | sì / sì / no |

I passaggi Arrow dichiarano `plenora-arrow-interchange-v1`: schema e
metadati fanno parte dello scambio, come spiegato in [insieme](insieme.md).

Le prime sette operazioni sono richieste. Query, execute e transazioni sono
condizionali: si interrogano le capacità del provider. Le quattro operazioni
transazionali non hanno un comando CLI nel catalogo; richiedono una sessione
persistente. Commit e rollback dichiarano deadline ma non cancellation.

## La CLI

La richiesta di connessione nomina una variabile d'ambiente protetta, non
scrive il segreto sulla riga di comando. Un `connessione.json` per PostgreSQL:

```json
{"provider": "postgres", "secret_environment": "PLENORA_DB_DSN"}
```

La variabile deve già contenere il DSN della connessione autorizzata.

```sh
plenora-database capabilities --format json
plenora-database test-connection --input connessione.json --format json
plenora-database list-catalogs --input connessione.json --format json
plenora-database list-schemas --input connessione.json --format json
plenora-database read --input lettura.json --output eventi.arrow --format json
plenora-database write --input scrittura.json --data eventi.arrow --format json
```

`lettura.json` aggiunge alla connessione `"operation_path": "read-plan.json"`;
`scrittura.json` aggiunge `"operation_path": "write-plan.json"`. Questi file
sono piani di lettura e scrittura già preparati secondo il contratto del
repository database: la richiesta esterna non è il piano stesso.
La lettura ammette anche `parameters_path`. Per `list-objects` si aggiunge
`schema`; per `describe-object` anche `object`. Le forme sono:

```sh
plenora-database list-objects --input oggetti.json --format json
plenora-database describe-object --input oggetto.json --format json
plenora-database query --input query.json --format json
plenora-database execute --input statement.json --format json
```

Query ed execute non sono intercambiabili: la prima produce risultati,
la seconda può mutare il database. Non si deduce dal solo nome del comando
che una richiesta sia supportata dal provider. Per busta ed exit code valgono
le [fondamenta](fondamenta.md). Un esito di commit sconosciuto resta un errore:
prima di ritentare si leggono effetto remoto e indicazioni di recupero.

## L'SDK Python

La distribuzione è `plenora-database`, l'import `plenora_database`. Si installa
la wheel locale della release per la propria piattaforma; Db2 richiede
l'artefatto dedicato e il runtime IBM documentato dal repository.
L'engine crea le sessioni, che delimitano il lavoro del chiamante.

```python
import os
import pyarrow as pa
import plenora_database as p

engine = p.engine_from_url(p.EngineConfig.from_url(os.environ["PLENORA_DB_URL"]))
try:
    with engine.session() as session:
        reader = session.read(
            "public", "events", projection=["id"],
            order_by=[("id", "asc")], limit=1000,
        )
        eventi = reader.read_all()
        esito = session.copy_from(
            "public", "measurements_new", pa.table({"id": [1, 2]}),
            mode="create", mapping_policy="compatible",
        )
finally:
    engine.close()
```

L'esempio presuppone `public.events(id)` leggibile e un target
`measurements_new` ancora assente. `Session.read(schema, table, ...)`
restituisce un lettore a batch; `read_all()` materializza una `pyarrow.Table`.
`Session.copy_from(schema, table, source, *, mapping_policy=..., mode=...)`
accetta tabelle, batch, iterabili di batch o IPC stream in byte e restituisce
un dizionario con esito e conteggi delle righe confermate.

Il binding associa l'ispezione a `Session.inspect().catalogs`, `.schemas`,
`.tables`, `.describe`; la query a `Session.select`. Una forma documentata
è `session.select("users").where_eq("id", 42).one()`. Gli statement
possono essere eseguiti con `Session.execute(statement, parameters)`.
Le varianti asincrone comprendono `AsyncSession.aread` e `.acopy_from`.

`with session.begin() as tx` conferma all'uscita normale e annulla su
un'eccezione. Sono disponibili `tx.commit()`, `tx.rollback()`,
`tx.savepoint("sp1")`, `tx.rollback_to_savepoint("sp1")` e
`tx.release_savepoint("sp1")`, nei limiti dichiarati dalla connessione.

Gli errori derivano da `PlenoraError`, fra cui `PlenoraUnsupportedError`,
`PlenoraNotFoundError`, `PlenoraTimeoutError`, `PlenoraCancelledError` e
`PlenoraConcurrentModificationError`. Si leggono `category`, `phase`,
`remote_effect`, `retry`, `details` e `provider`, senza analizzare il messaggio.

## I rifiuti e i limiti

- **Mapping esplicito**: `mapping_policy` è obbligatoria in scrittura.
  `strict` rifiuta ogni perdita; `compatible` ammette quelle che non sono
  perdita di dati. Nessuna policy promette una mappatura per ogni tipo.
  Per esempio, il bind Oracle `TIMESTAMP WITH TIME ZONE` in scrittura è
  rifiutato; la lettura con offset è invece documentata come supportata.
- **Modalità e transazioni**: `create`, `append`, `replace` e le altre
  modalità non sono garanzie universali. Si verificano insieme al profilo
  transazionale nelle capacità del provider.
- **Memoria Python**: `copy_from` e `acopy_from` materializzano l'intero
  input in un buffer IPC; passare piccoli batch non limita la memoria
  complessiva della chiamata.
- **Db2**: la wheel standard ne rifiuta l'uso con `PlenoraUnsupportedError`.
- **Oracle**: una riga molto grande e frammentata può richiedere lavoro
  sproporzionato. Timeout e limiti di byte restano necessari; non si
  aggirano per forzare una lettura.

Per lo scambio di metadati e i limiti del round-trip si veda
[Farle parlare insieme](insieme.md).

## Fonti

- [Catalogo database v2](../catalogs/database-tools-v2.json).
- [Binding CLI](../bindings/cli-v1.json) e
  [binding Python](../bindings/python-sdk-v1.json).
- Repository locale `C:/pg/db-rel`: `README.md`, `docs/README.md`,
  `docs/oracle-ttc-limits.md`, `contracts/v2/public-operation-contracts.schema.json`
  e `crates/plenora-database-py/README.md` (documentazione SDK).
  Le spellature CLI sono verificate anche nell'aiuto del binario nei sorgenti.
