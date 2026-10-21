# IO

IO porta un file esterno nel mondo Arrow e lo riporta in un formato di consegna.
Schema, geometria, CRS e fedeltà accompagnano i dati: riuscire a scrivere non
significa che il formato abbia conservato tutto. Il catalogo dell'installazione
dice quali formati e quali direzioni sono disponibili.

## Le operazioni

Il [catalogo pubblico](../catalogs/io-tools-v3.json) fissa le righe seguenti.
Nella tabella, **J** = `application/json`, **S** =
`application/vnd.apache.arrow.stream`, **F** =
`application/vnd.apache.arrow.file`. I controlli sono, nell'ordine,
`cancellation` / `deadline` / `idempotency_key` (sì o no).
I valori di `side_effect` sono quelli del catalogo, anche quando la CLI
materializza un file locale.

| id@versione | sintesi | ingresso: contratto · content type | uscita: contratto · content type | side_effect | controlli |
| --- | --- | --- | --- | --- | --- |
| `io.catalog@2` | Elenca formati, capacità e requisiti dei sink. | `plenora-io-catalog-query-v1` · J | `plenora-io-catalog-v2` · J | `none` | no / no / no |
| `io.inspect@1` | Descrive formato, layer, schema e fedeltà. | `plenora-io-inspect-input-v1` · J | `plenora-io-inspect-v1` · J | `none` | sì / sì / no |
| `io.layers@1` | Elenca i layer indirizzabili. | `plenora-io-layers-input-v1` · J | `plenora-io-layers-v1` · J | `none` | sì / sì / no |
| `io.read@2` | Legge un layer in Arrow, con evidenze di fedeltà. | `plenora-io-read-input-v1` · J | `plenora-io-read-result-v2` · S, F | `none` | sì / sì / no |
| `io.write@2` | Pubblica Arrow in un formato esplicito. | `plenora-io-write-input-v1` · J, S, F | `plenora-io-write-result-v2` · J | `local` | sì / sì / no |
| `io.convert@1` | Converte fra formati e riporta la fedeltà complessiva. | `plenora-io-convert-input-v1` · J | `plenora-io-convert-v1` · J | `local` | sì / sì / no |

I passaggi Arrow dichiarano `plenora-arrow-interchange-v1`: schema e
metadati fanno parte dello scambio, come spiegato in [insieme](insieme.md).

## La CLI

Si parte dalla scoperta, poi si sceglie un layer. Qui `punti.geojson` è una
sorgente esistente; le destinazioni sono nuovi file.

```sh
plenora-io catalog --format json
plenora-io inspect punti.geojson --format json
plenora-io layers punti.geojson --format json
plenora-io read punti.geojson --layer 0 --output punti.arrow --format json
plenora-io write punti.arrow copia.geojson --to geojson --format json
plenora-io convert punti.geojson punti.parquet --from geojson --to geoparquet --format json
```

`--format json` sceglie la risposta macchina; `--to` sceglie il formato
di destinazione; `convert` richiede anche `--from`. Il binding comune
registra `write --input … --output …`, ma il repository corrente accetta
`write INPUT OUTPUT --to FORMATO`: gli esempi usano questa forma verificata.
La differenza riguarda gli argomenti, non l'identità dell'operazione.

`read` senza `--output` attraversa i dati e restituisce conteggi e fedeltà,
non righe JSON. `--limit` serve alla validazione limitata e dichiara
`truncated`; non è il modo di consegnare una tabella completa. La lettura
con destinazione consegna IPC e ne descrive la pubblicazione.

`--assume-crs EPSG:4326` dichiara il CRS di una sorgente che non lo porta:
non riproietta. `--in-opt chiave=valore` e `--out-opt chiave=valore`
separano le opzioni delle due direzioni; le chiavi dipendono dal formato.
`--deadline-ms` limita l'operazione; il primo Ctrl+C chiede l'annullamento,
il secondo termina subito. Per busta ed exit code valgono le
[fondamenta](fondamenta.md).

## L'SDK Python

La distribuzione è `plenora-io`, l'import `plenora_io`. Si installa la
wheel consegnata con la release; per gli oggetti PyArrow serve l'extra
`pyarrow`. La wheel pura richiede anche un binario disponibile;
`Client(binary=...)` permette di sceglierlo esplicitamente.

```python
from plenora_io import Client

client = Client()
capacita = client.capabilities()
layer = client.layers("punti.geojson")
lettura = client.read("punti.geojson", "punti.arrow", layer=0)
tabella = client.read_table("punti.geojson", layer=0)
scrittura = client.write(tabella.table, "copia.geojson", format="geojson")
```

Le firme d'uso principali sono `catalog()`, `inspect(source, ...)`,
`layers(source, ...)`, `validate(source, ...)`, `read(source, output, ...)`,
`read_table(source, ...)`, `write(source, destination, *, format, ...)` e
`convert(source, target, *, source_format, target_format, ...)`. `validate` è una forma di `io.read`,
non una settima operazione. `read_table` restituisce `TableRead(table, result)`:
la tabella e le evidenze della lettura restano entrambe disponibili.
`write` accetta IPC su percorso oppure una tabella, batch o produttore Arrow.

La radice degli errori è `PlenoraError`. Fra i rifiuti utili al chiamante:
`InvalidArgumentError` per argomenti non validi, `OptionalDependencyError`
per l'adattatore Arrow non disponibile, `ProtocolError` per una risposta
non interpretabile. Dopo l'avvio di una scrittura, un errore di protocollo
può portare `remote_effect: unknown`: non prova che il file sia assente.
`CleanupError` dopo una pubblicazione porta invece effetto `committed`.
L'SDK è sincrono.

## I rifiuti e i limiti

- **CRS**: nessuna riproiezione implicita. CSV e XLSX con geometria
  richiedono `--assume-crs`; un GeoPackage richiede un CRS risolto.
  Una tabella geometrica senza quel CRS viene rifiutata dal sink.
- **Fedeltà**: ogni formato ha capacità proprie. Si legge il report di
  lettura e scrittura, non il solo esito della pubblicazione.
- **IPC esterno**: il CRS presente soltanto in `ARROW:extension:metadata`
  non viene letto; il risultato dichiara CRS mancante. I metadati
  `plenora.geometry.*` sono quindi essenziali nelle catene di famiglia.
- **Memoria**: `read_table` materializza tutta la tabella. Per dati grandi
  si usa `read` verso IPC e si consuma quel file a batch.
- **FileGDB**: la disponibilità dipende dall'artefatto installato; una
  capacità assente dà un rifiuto tipizzato.

## Fonti

- [Catalogo IO v3](../catalogs/io-tools-v3.json).
- [Binding CLI](../bindings/cli-v1.json) e
  [binding Python](../bindings/python-sdk-v1.json).
- Repository locale `C:/pg/io-rel`: `README.md`, `docs/PRODUCT.md`,
  `docs/PIANO-4.0.0.md`, `sdk/python/README.md`; firme pubbliche di `Client`
  e argomenti della CLI verificati anche nei sorgenti.
