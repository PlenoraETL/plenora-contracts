# Farle parlare insieme

Le librerie si scambiano **tabelle Arrow** e **file**. Le tabelle viaggiano
come Arrow IPC (`application/vnd.apache.arrow.stream` o `.file`) col
vocabolario di metadati della famiglia; i file viaggiano per riferimento, col
digest che ne prova l'identità. Questo capitolo descrive le catene provate
dalla suite d'interoperabilità e ciò che uno sviluppatore deve aspettarsi a
ogni cucitura.

## La regola di base: l'IPC è il punto d'incontro

Ogni CLI che produce una tabella sa scriverla come IPC su file, e ogni CLI
che consuma una tabella sa leggerla da lì. La catena minima è quindi sempre:

```
plenora-io read <sorgente> out.arrow --layer ...      # file esterno -> Arrow
plenora-data run piano.json out.arrow out2.arrow      # Arrow -> Arrow
plenora-database write out2.arrow --table ...         # Arrow -> database
```

Gli SDK Python accettano e restituiscono `pyarrow.Table` (o percorsi IPC)
sulle stesse operazioni: una catena può cambiare strada a ogni hop e il
risultato deve restare lo stesso — è una proprietà verificata, non una
speranza (la suite confronta le impronte fra CLI, Python e Rust).

## Che cosa si conserva a ogni hop, e che cosa cambia dichiaratamente

- **I dati**: esatti, byte per byte sui binari (WKB/EWKB) e bit per bit sui
  float. Nessun hop può arrotondare in silenzio.
- **I metadati del vocabolario** (`plenora.*`): ogni hop li conserva, con le
  trasformazioni che il suo contratto dichiara. Esempi dichiarati: `data`
  normalizza `LargeUtf8`→`Utf8` e assegna `plenora.field_id` ai campi che
  non lo portano; `database` riscrive la geometria come EWKB
  (`encoding=ewkb`) e, dove c'è uno SRID, dichiara `axis_order=unknown`;
  i suoi metadati nativi arrivano come `plenora.postgres.*`.
- **Il `field_id`**: identifica il campo logico attraverso la catena, con la
  semantica fissata dalla decisione [0022](../decisions/0022-field-id-across-operations-and-the-mixed-form.md)
  (si conserva per i campi invariati; la provenienza vale per i campi nati
  nello store). Nota: database 8.0.0 lo sostituisce ancora nel round-trip —
  difetto tracciato, vedi sotto.

## Le catene provate

| catena | come si compone | note |
| --- | --- | --- |
| file → tabella → file | `io.read` → `data.run` → `io.write` | il giro base; i formati d'uscita dichiarano le proprie esigenze (un GeoPackage esige un CRS risolto e rifiuta con `unsupported` chi non ce l'ha) |
| file → database | `io.read` → `database.write` | la geometria entra come WKB ISO o EWKB; la tabella si crea (`create`) o si estende (`append`) |
| database → file | `database.read` → `io.write` | la lettura torna ordinata e tipizzata, geometria in EWKB |
| database ↔ tabella | `database.read` → `data.run` → `database.write` | i dati possono nascere in SQL: il vocabolario li descrive comunque |
| storage → file locale → qualunque cosa | `storage.get` → `io.read` → … | il file scaricato porta lo SHA-256: verificarlo è parte del contratto (`plenora-file-interchange-v1`) |
| API HTTP → tabella | `rest.generate`/`rest.enrich` → `data.run` | il risultato REST è JSON: il passaggio a Arrow richiede l'adattatore contrattato (`plenora-rest-arrow-adapter-v1` per un verso; l'altro verso è in contrattazione) |

## Che cosa aspettarsi quando qualcosa rifiuta

Un rifiuto in una catena è **tipizzato e senza dati**: la busta v2 porta la
categoria (`invalid_plan`, `unsupported`, `io`, `conflict`, …), la fase, e un
messaggio fisso che non cita mai i valori del documento. Due proprietà su cui
si può costruire:

- **La stessa causa dà la stessa categoria su ogni strada**: la CLI che esce
  con exit tipizzato e l'SDK che alza l'eccezione corrispondente raccontano
  lo stesso errore (è una cella della matrice: «errori e sentinelle»).
- **Un esito incerto non è un successo**: se la conferma di un commit si
  perde, `database.write` esce con l'errore di esito sconosciuto
  (`remote_effect: committed`/`unknown`), mai con 0. Verificato con un proxy
  che lascia cadere la conferma.

## Lo stato misurato, oggi

La matrice completa (catene × strade CLI/Python/Rust) sta nella suite
d'interoperabilità, con l'ultima esecuzione sulla famiglia corrente. In
sintesi: le catene sopra **funzionano nei dati**; i disallineamenti aperti
sono tracciati — il `field_id` sostituito nel round-trip del database
(database-tools#124), la superficie Rust del database più povera della CLI
(database-tools#125), la forma della dichiarazione `mixed` fra IO e database
(plenora-IO-tools#66) — e due difetti dichiarati restano aperti nelle
librerie (gli assi di `geo.centroid` in data; gli assi delle eccezioni
divergenti fra librerie). Chi costruisce una catena oggi convive con quelli,
sapendolo.
