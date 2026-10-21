# rest

rest esegue richieste HTTP descritte da configurazioni: genera record,
arricchisce quelli ricevuti e trasferisce file. Il risultato strutturato
resta JSON; diventare una tabella Arrow è un passaggio distinto, descritto
in [Farle parlare insieme](insieme.md).

## Le operazioni

Il [catalogo pubblico](../catalogs/rest-tools-v1.json) fissa le righe seguenti.
Nella tabella, **J** = `application/json`, **S** =
`application/vnd.apache.arrow.stream`, **F** =
`application/vnd.apache.arrow.file`. I controlli sono, nell'ordine,
`cancellation` / `deadline` / `idempotency_key` (sì o no).
I valori di `side_effect` sono quelli del catalogo, anche quando la CLI
materializza un file locale.

| id@versione | sintesi | ingresso: contratto · content type | uscita: contratto · content type | side_effect | controlli |
| --- | --- | --- | --- | --- | --- |
| `rest.test@1` | Verifica la connessione con una richiesta HTTP limitata. | `plenora-rest-execution-request-v1` · J | `plenora-rest-execution-result-v1` · J | `remote` | sì / sì / sì |
| `rest.generate@1` | Genera un risultato strutturato dalla richiesta configurata. | `plenora-rest-execution-request-v1` · J | `plenora-rest-execution-result-v1` · J | `remote` | sì / sì / sì |
| `rest.enrich@1` | Arricchisce record conservando ordine ed errori per record. | `plenora-rest-execution-request-v1` · J | `plenora-rest-execution-result-v1` · J | `remote` | sì / sì / sì |
| `rest.download@1` | Scarica una risposta in un artefatto autorizzato. | `plenora-rest-file-transfer-input-v1` · J | `plenora-rest-file-transfer-result-v1` · J | `remote` | sì / sì / sì |
| `rest.upload@1` | Carica un artefatto e restituisce risposta e integrità. | `plenora-rest-file-transfer-input-v1` · J | `plenora-rest-file-transfer-result-v1` · J | `remote` | sì / sì / sì |

Tutte le operazioni dichiarano `remote`, anche `test`: una richiesta HTTP
può avere effetti sul servizio. Download e upload riportano integrità
SHA-256; il JSON descrive il trasferimento, non contiene il file.

## La CLI

Il documento `richiesta.json` contiene l'operazione, la connessione,
l'input e le opzioni. Questo esempio usa un indirizzo illustrativo da
sostituire con un endpoint JSON autorizzato:

```json
{
  "schema_version": 1,
  "operation": "generate",
  "connection": {"url": "https://api.example.com/weather", "method": "GET"},
  "input": {"params": {}, "records": []},
  "options": {}
}
```

```sh
plenora-rest capabilities --format json
plenora-rest generate --input richiesta.json --format json
plenora-rest test --input test.json --format json
plenora-rest enrich --input arricchimento.json --format json
plenora-rest download --input download.json --config engine.json --format json
plenora-rest upload --input upload.json --config engine.json --format json
```

Ogni file deve dichiarare l'operazione del comando: `test`, `enrich`,
`download` o `upload`. In caso contrario si riceve `OPERATION_MISMATCH`
prima della rete. L'arricchimento porta i record in `input.records`;
i trasferimenti hanno il proprio input file. `--input -` legge dallo
standard input. `--config` riceve la configurazione dell'engine: è il punto
in cui si autorizzano, per esempio, reti private e trasferimenti con
`file_root`. Campi sconosciuti sono rifiutati.

Per busta ed exit code si vedano le [fondamenta](fondamenta.md), con una
particolarità decisiva: un risultato REST `partial` produce busta `ok` ed
exit 0, come `success`. Bisogna quindi leggere lo stato dentro il risultato
e i suoi errori per sapere se tutte le righe sono state ottenute.
`failed` diventa una busta d'errore con il primo errore e gli eventuali
handle di recupero. I segreti stanno nel file o sullo standard input,
non negli argomenti della riga di comando.

## L'SDK Python

La distribuzione è `plenora-rest`, l'import `plenora_rest`. Si installa
la wheel della piattaforma; il README documenta anche `python -m pip install .`
dalla working copy. L'SDK supportato è sincrono.

```python
from plenora_rest import Engine

connection = {
    "url": "https://api.example.com/weather",
    "method": "GET",
    "parameters": [
        {"name": "latitude", "mode": "mapped", "source": "lat",
         "location": "query", "required": True},
        {"name": "longitude", "mode": "mapped", "source": "lon",
         "location": "query", "required": True},
    ],
    "response": {"output_mapping": [
        {"path": "current.temperature", "column": "temperature"}
    ]},
}
with Engine() as engine:
    risultato = engine.enrich(
        connection, [{"lat": 41.9028, "lon": 12.4964, "city": "Roma"}],
        concurrency=4,
    )
stato = risultato["status"]
errori = risultato["errors"]
```

Anche qui l'URL è un segnaposto: il servizio scelto deve avere la risposta
configurata. Le firme d'uso sono `test(connection, ...)`,
`generate(connection, ...)`, `enrich(connection, records, ...)`,
`download(connection, destination, ...)` e `upload(connection, source, ...)`.
I controlli includono `deadline` come stringa RFC 3339, `idempotency_key`
e `cancellation=CancellationToken()`. `enrich` accetta `continue_on_error`
e `concurrency`; download accetta `overwrite`, `resume`, `max_bytes` ed
`expected_sha256`. Upload accetta anche `content_type`, `filename` e
`field_name`; quest'ultimo seleziona il multipart.

I trasferimenti su percorsi locali richiedono un engine configurato con
`allow_file_transfers` e `file_root`. Il risultato è un `ExecutionResult`
strutturato: gli errori per record possono stare nel risultato, perciò un
blocco `try/except` da solo non sostituisce il controllo dello stato.
`PlenoraError` è la radice delle eccezioni al confine Python e porta
`category`, `phase`, `remote_effect`, `retry`, `code`, `details` e `payload`.

## I rifiuti e i limiti

- **Rete predefinita**: loopback e reti private sono bloccati. Redirect,
  proxy e file transfer richiedono autorizzazione; un redirect autorizzato
  deve restare sulla stessa origin. TLS viene verificato.
- **Risorse**: request e response in memoria hanno limiti distinti; i file
  hanno un limite di trasferimento. Un download oltre soglia non pubblica
  un file incompleto.
- **Paginazione**: raggiungere `max_rows` o `max_pages` mentre potrebbero
  esserci altri dati produce `partial` e `PAGINATION_LIMIT_REACHED`.
  Anche un'ultima pagina piena esattamente al limite può produrre questo
  esito: non viene fatta una richiesta aggiuntiva per sapere se era l'ultima.
- **Idempotenza**: il registro locale delle chiavi è limitato; le più vecchie
  possono essere dimenticate. Non è una deduplicazione durevole garantita
  dal client: quella appartiene al servizio o all'host.
- **File e concorrenza**: `file_root` viene verificata sul percorso
  canonicalizzato, ma non impedisce la sostituzione concorrente di una
  directory con un collegamento simbolico. La root non va condivisa con
  processi non fidati.
- **Ambito**: nessun SDK Python asincrono e nessuna gestione diretta di
  broker o code non HTTP. Un job è gestibile se espone submit, stato e
  risultato via REST.

## Fonti

- [Catalogo REST v1](../catalogs/rest-tools-v1.json).
- [Binding CLI](../bindings/cli-v1.json) e
  [binding Python](../bindings/python-sdk-v1.json).
- Repository locale `C:/pg/rest-rel`: `README.md`, `docs/limiti.md`;
  firme e forma delle richieste verificate in `python/plenora_rest/_engine.py`.
