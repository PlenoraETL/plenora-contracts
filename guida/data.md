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

## Le trasformazioni del piano

I passi di `data.run` nominano i kernel del
[catalogo delle trasformazioni](../catalogs/data-kernels-v2.json):
146 in tutto, 71 della famiglia `table` e 75 della famiglia `geo`.
Un piano reale, da `docs/runner.md` di `C:/pg/dt-rel`, filtra gli ordini,
li unisce ai clienti e somma gli importi per regione:

```json
{
  "version": 1,
  "inputs": ["ordini", "clienti"],
  "limits": {"max_rows_per_edge": 1000000},
  "steps": [
    {"out": "validi", "op": "table.filter", "in": ["ordini"],
     "config": {"column": "importo", "operator": ">", "value": 0}},
    {"out": "uniti", "op": "table.join", "in": ["validi", "clienti"],
     "config": {"left_keys": ["cliente"], "right_keys": ["id"], "how": "inner"}},
    {"out": "totali", "op": "table.aggregate", "in": ["uniti"],
     "config": {"group_by": ["regione"],
                "aggregations": [{"column": "importo", "function": "sum"}]}}
  ],
  "outputs": ["totali"]
}
```

`op` è l'id canonico del kernel, senza suffisso di versione; gli alias
legacy sono rifiutati. `in` elenca gli input del passo nell'ordine richiesto:
nel join, sinistra e destra. Ogni nome deve essere un input del piano o
l'output di un passo precedente. `out` assegna un nome nuovo alla tabella
prodotta; `outputs` sceglie quali tabelle consegnare. `config` contiene i
parametri del kernel e, se omesso, vale `{}`.

Nelle tabelle `@3` significa kernel v3: il numero è il campo `version` del
catalogo, specifico di ciascun id. Non è la versione del piano (`1`)
né quella dell'operazione `data.run` (`2` o `3`). `data.validate` verifica
il piano sui contratti degli input senza eseguirne i passi. Restano i
[rifiuti e i limiti](#i-rifiuti-e-i-limiti) del capitolo, inclusa la
disponibilità dei kernel: la presenza nell'elenco non garantisce
l'esecuzione.

Le sintesi derivano da «Che cosa fa» delle schede in
`C:/pg/dt-rel/docs/schede/<id>.md`, raccolte anche in
`C:/pg/dt-rel/docs/operazioni.md`. La scheda con lo stesso id documenta
parametri, tipi, errori ed esempi; le sottofamiglie qui servono a trovare
la trasformazione. Ogni kernel compare una sola volta.

### Table: selezione e colonne (11)

| id@versione | sintesi |
| --- | --- |
| `table.select_columns@1` | Tiene solo le colonne elencate in `columns`, nell'ordine in cui sono elencate, e scarta le altre. |
| `table.drop_columns@1` | Toglie dalla tabella le colonne elencate in `columns` e lascia le altre come sono, nello stesso ordine. |
| `table.rename@1` | Cambia il nome delle colonne secondo le coppie `old_name` → `new_name`. |
| `table.reorder_columns@1` | Cambia l'ordine delle colonne senza toglierne né aggiungerne: prima quelle elencate in `columns`, nell'ordine dato, poi tutte le altre, nell'ordine d'ingresso oppure, con `alphabetical`, in ordine alfabetico. |
| `table.align_schema@3` | Porta la tabella allo schema dichiarato in `columns`: le colonne escono nell'ordine dichiarato; una colonna che esiste deve avere già il tipo dichiarato (nessuna conversione implicita); una che manca si aggiunge, tutta null oppure costante col `default`. |
| `table.type_cast@4` | Converte la colonna `column` nel tipo `target_type`, nella stessa posizione. |
| `table.flatten_json@3` | Legge ogni cella di una colonna come documento JSON e ne estrae i valori nominati in `output_columns`, uno per colonna d'uscita. |
| `table.unnest@1` | Apre una colonna struct: ogni campo dello struct diventa una colonna, con il nome preceduto da `prefix`. |
| `table.melt@3` | Porta la tabella da larga a lunga: ogni colonna valore diventa un blocco di righe, con il nome della colonna in `var_name` e la cella in `value_name`; le colonne id si ripetono su ogni blocco. |
| `table.pivot@3` | Porta la tabella da lunga a larga aggregando `value_col` per `index_col` e `pivot_col`; nel piano richiede `mapping` per fissare le colonne d'uscita. |
| `table.transpose@3` | Traspone righe e colonne; è dichiarato `unavailable` e il piano lo rifiuta in validazione. |

### Table: righe e insiemi (13)

| id@versione | sintesi |
| --- | --- |
| `table.filter@3` | Tiene le righe in cui la colonna `column` soddisfa la condizione `operator value` e scarta le altre. |
| `table.sort@2` | Riordina le righe secondo le colonne `columns`: decide la prima, a parità la seconda, e così via. |
| `table.limit@1` | Tiene al più `n` righe consecutive, a partire dalla riga `offset` (contata da 0), e scarta le altre. |
| `table.top_n@2` | Tiene le prime `n` righe secondo l'ordinamento di `table.sort` sulle colonne `columns`. |
| `table.sample@2` | Estrae un campione pseudocasuale delle righe: `n` righe, oppure una frazione `fraction` della tabella, eventualmente per strati di una colonna. |
| `table.distinct@2` | Toglie le righe ripetute: due righe sono uguali se hanno gli stessi valori nelle colonne di `subset` (tutte le colonne se `subset` è vuoto). |
| `table.dedup_advanced@2` | Ordina per `order_column` e toglie i duplicati come `table.distinct`: prima e ultima occorrenza si riferiscono a quell'ordine. |
| `table.concat@1` | Impila le righe di due tabelle con lo stesso schema: prima tutte le righe di sinistra, poi tutte quelle di destra. |
| `table.concat_by_name@1` | Impila le righe di due tabelle abbinando le colonne per nome, non per posizione: prima tutte le righe di sinistra, poi quelle di destra. |
| `table.union_distinct@2` | Unione insiemistica di due tabelle con lo stesso schema (`UNION` di SQL): le righe distinte che compaiono in almeno uno dei due ingressi, ognuna una volta. |
| `table.intersect@2` | Intersezione insiemistica di due tabelle con lo stesso schema (`INTERSECT` di SQL): le righe distinte di sinistra che compaiono anche a destra, ognuna una volta. |
| `table.except@2` | Differenza insiemistica di due tabelle con lo stesso schema (`EXCEPT` di SQL): le righe distinte di sinistra che non compaiono a destra, ognuna una volta. |
| `table.explode@2` | Espande una colonna lista in una riga per elemento: ogni riga d'ingresso si ripete una volta per ogni elemento della sua lista, e la colonna d'uscita contiene l'elemento. |

### Table: join (6)

| id@versione | sintesi |
| --- | --- |
| `table.join@3` | Unisce ogni riga di sinistra alle righe di destra che hanno la stessa chiave, fatta di una o più colonne (`left_keys[i]` con `right_keys[i]`). |
| `table.cross_join@2` | Prodotto cartesiano: ogni riga di sinistra affiancata a ogni riga di destra. |
| `table.anti_join@2` | Tiene le righe di sinistra la cui chiave non compare a destra, e scarta le altre. |
| `table.semi_join@2` | Tiene le righe di sinistra la cui chiave compare almeno una volta a destra, e scarta le altre. |
| `table.asof_join@3` | Affianca a ogni riga di sinistra al più una riga di destra: quella con il valore ordinato (`right_on`) più vicino al valore della riga (`left_on`), nella direzione scelta, dentro lo stesso gruppo (`left_by` con `right_by`) ed entro la tolleranza. |
| `table.fuzzy_join@2` | Join per somiglianza fra due colonne di testo, per anagrafiche sporche: abbina ogni riga di sinistra alle righe di destra la cui chiave ha una somiglianza (`metric`) almeno pari a `threshold`, e aggiunge in coda la colonna della somiglianza. |

### Table: date e tempo (5)

| id@versione | sintesi |
| --- | --- |
| `table.date_extract@4` | Legge la colonna `column` come data o data e ora e ne estrae le parti chieste (anno, mese, giorno, trimestre, giorno della settimana, settimana ISO, ora, minuto, secondo), una colonna `int64` per parte. |
| `table.date_add@4` | Legge date e ore scritte come testo, vi aggiunge (o toglie, con `amount` negativo) una quantità fissa di anni, mesi, settimane, giorni, ore, minuti o secondi e scrive il risultato come testo in una colonna nuova. |
| `table.date_diff@4` | Legge due colonne di date e ore scritte come testo, con lo stesso formato, e scrive la differenza `fine - inizio` in giorni, ore, minuti o secondi, come numero con parte frazionaria (un giorno e mezzo è `1.5`) e con segno. |
| `table.date_format@4` | Legge date e ore scritte come testo con un formato e le riscrive con un altro formato in una colonna nuova (per esempio da `31/01/2024` a `2024-01-31`). |
| `table.timezone_convert@4` | Legge date e ore scritte come testo, le interpreta come ora locale di un fuso orario di partenza e le riscrive come ora locale di un fuso di arrivo, con un formato che può mostrare l'offset o il nome del fuso. |

### Table: stringhe (8)

| id@versione | sintesi |
| --- | --- |
| `table.concat_columns@1` | Unisce riga per riga il testo delle colonne `columns`, nell'ordine dato e con `separator` fra una parte e l'altra, in una colonna `utf8`. |
| `table.split_column@1` | Divide il testo della colonna `column` sul delimitatore `delimiter`, da sinistra, e scrive le parti nelle colonne `new_columns`, una parte per colonna. |
| `table.replace@1` | Sostituisce testo nella colonna `utf8` `column`. |
| `table.lookup@2` | Traduce i valori di una colonna con una tabella di corrispondenza scritta nella config: ogni cella il cui testo è una chiave di `mapping` diventa il valore associato; le altre diventano `default`, oppure, se `default` è `null`, restano come sono. |
| `table.string_extract@1` | Cerca l'espressione regolare `pattern` nel testo della colonna `column` ed estrae ciò che trova in colonne `utf8`. |
| `table.string_length@1` | Scrive in una colonna `int64` la lunghezza del testo della colonna `column`, contata in code point Unicode (non in byte e non in grafemi). |
| `table.string_pad@1` | Allunga il testo della colonna `column` fino a `width` caratteri, aggiungendo `fill_char` a sinistra (default) o a destra. |
| `table.text_normalize@1` | Normalizza il testo delle colonne `columns` con una regola sola, scelta in `operations`: toglie gli spazi ai lati, cambia maiuscole e minuscole, toglie gli accenti, riduce gli spazi multipli, o fa tutto insieme (`full`, il default). |

### Table: numerica e formule (4)

| id@versione | sintesi |
| --- | --- |
| `table.bin@3` | Divide i valori numerici di una colonna in classi e scrive, per ogni riga, l'etichetta della sua classe in una colonna di testo. |
| `table.conditional@3` | Aggiunge una colonna calcolata con regole «se… allora»: per ogni riga valuta le `conditions` sulla colonna `column`, nell'ordine, e scrive il `result` della prima vera; se nessuna è vera scrive `default_value`. |
| `table.formula@4` | Calcola una colonna nuova da una formula aritmetica scritta come testo, per esempio `prezzo * quantita + 2`: quattro operazioni, parentesi, numeri, testi fra apici e nomi di colonna. |
| `table.expression@6` | Calcola una colonna nuova da un'espressione scritta come albero JSON: colonne, letterali, operatori aritmetici, di confronto e logici, funzioni e `case`. |

### Table: asserzioni e qualità (13)

| id@versione | sintesi |
| --- | --- |
| `table.assert_cardinality@1` | Verifica il numero di righe della tabella: esattamente `exact_rows`, oppure almeno `min_rows` e al più `max_rows`. |
| `table.assert_foreign_key@3` | Verifica un vincolo di chiave esterna: ogni chiave `left_keys` della tabella sinistra deve comparire fra le chiavi `right_keys` della tabella destra. |
| `table.assert_metadata@1` | Verifica i metadati di schema dell'ingresso: ogni coppia di `expected` deve esserci, con lo stesso valore; con `allow_extra=false` non devono esserci altre chiavi. |
| `table.assert_not_null@2` | Verifica che nessuna delle colonne `columns` contenga un null. |
| `table.assert_range@4` | Verifica che ogni valore della colonna `column` stia fra `min` e `max`. |
| `table.assert_regex@2` | Verifica che ogni valore della colonna di testo `column` corrisponda all'espressione regolare `pattern`. |
| `table.assert_schema@2` | Verifica che lo schema dell'ingresso sia quello atteso: per ogni voce di `fields` una colonna con quel nome, un tipo della famiglia indicata e, se richiesta, quella nullabilità. |
| `table.assert_unique@3` | Verifica che la chiave formata dalle colonne `columns` sia unica nella tabella: nessuna coppia di righe ha gli stessi valori in tutte le colonne della chiave. |
| `table.validate_rules@4` | Valuta un elenco di regole dichiarative su ogni riga, senza mai fallire sui dati: una regola violata è un esito, non un errore. |
| `table.fill_na@2` | Riempie le celle null di una colonna, o di tutte se `column` manca: con un valore fisso (`method = "value"`), con l'ultimo valore non nullo che le precede (`ffill`) o con il primo che le segue (`bfill`), nell'ordine delle righe. |
| `table.coalesce@1` | Riga per riga, prende il primo valore non nullo fra le colonne `columns`, nell'ordine in cui sono elencate, e lo scrive in `output_column`. |
| `table.reconcile@3` | Confronta due tabelle sulle chiavi `left_keys` e `right_keys` e restituisce un resoconto di cinque metriche: quante righe si abbinano, quante restano solo a sinistra o solo a destra, quante sono duplicati di una chiave su ciascun lato. |
| `table.table_diff@2` | Confronta due versioni di una tabella, allineate su una chiave: la sinistra è la versione vecchia, la destra la nuova. |

### Table: hash e mascheramento (6)

| id@versione | sintesi |
| --- | --- |
| `table.md5_hash@3` | Aggiunge una colonna con l'hash MD5, in esadecimale minuscolo, dei valori di alcune colonne di ogni riga. |
| `table.sha256_hash@3` | Aggiunge una colonna con l'hash SHA-256, in esadecimale minuscolo, dei valori di alcune colonne di ogni riga. |
| `table.hmac_sha256@2` | Aggiunge a ogni riga l'HMAC-SHA256 (RFC 2104), in esadecimale minuscolo, dei valori di alcune colonne, con una chiave segreta letta da una variabile d'ambiente. |
| `table.stable_fingerprint@2` | Aggiunge un'impronta SHA-256 o MD5 dei valori, con nomi e tipi delle colonne, senza normalizzazione e distinguendo null da testo vuoto. |
| `table.mask_data@2` | Maschera la parte centrale del testo con forme per codici fiscali, email, telefoni e IBAN, oppure con una regola `custom`. |
| `table.uuid_generator@1` | Aggiunge una colonna con un UUID versione 4 casuale per riga, in forma testuale minuscola con i trattini (36 caratteri, `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`). |

### Table: finestre e aggregazioni (5)

| id@versione | sintesi |
| --- | --- |
| `table.add_row_number@3` | Aggiunge una colonna `int64` con il numero progressivo di ogni riga nell'ordine d'ingresso, a partire da `start`. |
| `table.aggregate@3` | Raggruppa le righe per i valori delle colonne `group_by` e produce una riga per gruppo: le colonne di gruppo, poi una colonna per ogni aggregazione di `aggregations` (conteggi, somme, medie, estremi, varianze, quantili, testi). |
| `table.statistics@3` | Calcola statistiche descrittive (conteggio, minimo, massimo, somma, media, mediana, deviazione standard, varianza, quartili) dei valori di una colonna numerica, sull'intera tabella o per gruppi, e le scrive in colonne nuove ripetute su ogni riga del gruppo. |
| `table.window_function@3` | Aggiunge una funzione finestra per riga e partizione: rango, somma cumulata, valore precedente o successivo, variazione percentuale o quantile di posizione. |
| `table.rolling_window@3` | Aggiunge per riga l'aggregazione delle ultime `window` righe della partizione, riga corrente compresa. |

### Geo: misure (14)

| id@versione | sintesi |
| --- | --- |
| `geo.area@2` | Aggiunge una colonna `float64` con l'area planare, senza segno, della geometria di ogni riga, nelle unità del CRS al quadrato. |
| `geo.length@2` | Aggiunge una colonna `float64` con la lunghezza planare della geometria di ogni riga, nelle unità del CRS. |
| `geo.perimeter@2` | Aggiunge una colonna `float64` con il perimetro planare della geometria di ogni riga, nelle unità del CRS. |
| `geo.distance@1` | Aggiunge una colonna `float64` con la distanza euclidea planare fra la geometria di ogni riga e una geometria fissa scritta nella config (`other_wkb`), nelle unità del CRS: la distanza minima fra i due insiemi di punti, 0 quando si intersecano (anche quando uno contiene l'altro). |
| `geo.bounds_extractor@2` | Aggiunge quattro colonne `float64` con il rettangolo d'ingombro della geometria di ogni riga: coordinate minime e massime in x e in y, nelle unità del CRS. |
| `geo.vertex_count@2` | Aggiunge una colonna `uint64` con il numero di coordinate della geometria di ogni riga, sommato su tutte le parti. |
| `geo.geometry_accessors@1` | Aggiunge colonne che descrivono la geometria di ogni riga: il tipo, il numero di parti, il numero di anelli interni, il primo e l'ultimo punto di una linea aperta e se la geometria è chiusa. |
| `geo.geodesic_area@3` | Aggiunge l'area geodetica dei poligoni in metri quadrati, sull'ellissoide del datum del CRS della colonna. |
| `geo.geodesic_distance@2` | Aggiunge la distanza geodetica in metri fra il punto della riga e `other_wkb`, sull'ellissoide del datum del CRS della colonna. |
| `geo.geodesic_line_length@3` | Aggiunge la lunghezza geodetica delle linee in metri, sommando le geodetiche fra vertici sull'ellissoide del datum del CRS della colonna. |
| `geo.haversine_distance@2` | Aggiunge la distanza fra punti in metri lungo il cerchio massimo di una sfera con il raggio medio IUGG dell'ellissoide del datum del CRS. |
| `geo.hausdorff_distance@2` | Aggiunge una colonna `float64` con la distanza di Hausdorff discreta fra la geometria di ogni riga e una geometria fissa della config (`other_wkb`), nelle unità del CRS. |
| `geo.frechet_distance@2` | Aggiunge la distanza di Fréchet discreta fra la linea della riga e `other_wkb`, confrontando i percorsi sui vertici e tenendo conto del verso. |
| `geo.bearing@2` | Aggiunge l'azimut geodetico iniziale in gradi dal punto della riga al punto `other_wkb`, in senso orario dal nord. |

### Geo: costruzioni (10)

| id@versione | sintesi |
| --- | --- |
| `geo.from_coords@2` | Costruisce una colonna geometria di punti da due colonne numeriche: per ogni riga il `Point` (x, y), nel CRS dato dalla config o dal piano. |
| `geo.from_wkt@3` | Crea la colonna geometria di una tabella che non ne ha, leggendo il testo WKT di una colonna `utf8`: ogni cella diventa la geometria WKB corrispondente, una cella nulla una geometria nulla. |
| `geo.centroid@2` | Sostituisce ogni geometria con il suo centroide, un `Point`, nella stessa colonna. |
| `geo.point_on_surface@2` | Sostituisce ogni geometria con un `Point` che le appartiene, nella stessa colonna. |
| `geo.envelope@2` | Sostituisce ogni geometria con il suo rettangolo d'ingombro, nella stessa colonna. |
| `geo.convex_hull@2` | Sostituisce ogni geometria con il suo inviluppo convesso, un `Polygon`, nella stessa colonna: il più piccolo poligono convesso che contiene tutti i vertici. |
| `geo.concave_hull@3` | Sostituisce ogni geometria con un poligono concavo che ne racchiude tutte le coordinate (vertici degli anelli interni e punti ripetuti compresi). |
| `geo.boundary@2` | Sostituisce ogni geometria con il suo confine OGC, nella stessa colonna. |
| `geo.buffer@2` | Sostituisce ogni geometria con il suo buffer planare a distanza `distance`, nelle unità del CRS: l'insieme dei punti che distano al più `distance` dalla geometria, sempre un `MultiPolygon` (anche vuoto). |
| `geo.polygon_builder@2` | Costruisce un `Polygon` senza buchi dai punti della colonna geometria, nell'ordine delle righe: i punti sono l'anello esterno, chiuso da sé se l'ultimo non ripete il primo. |

### Geo: predicati (12)

| id@versione | sintesi |
| --- | --- |
| `geo.predicate_intersects@1` | Aggiunge una colonna `bool` che dice se la geometria della riga (A) e la geometria costante `other_wkb` (B) hanno almeno un punto in comune: interno o confine dell'una che tocca interno o confine dell'altra. |
| `geo.predicate_disjoint@1` | Aggiunge una colonna `bool` che dice se la geometria della riga (A) e la geometria costante `other_wkb` (B) non hanno alcun punto in comune. |
| `geo.predicate_contains@1` | Aggiunge una colonna `bool` che dice se la geometria della riga (A) contiene la geometria costante `other_wkb` (B): nessun punto di B è fuori da A e almeno un punto dell'interno di B è nell'interno di A. |
| `geo.predicate_within@1` | Aggiunge una colonna `bool` che dice se la geometria della riga (A) sta dentro la geometria costante `other_wkb` (B): nessun punto di A è fuori da B e almeno un punto dell'interno di A è nell'interno di B. |
| `geo.predicate_equals_topo@1` | Aggiunge una colonna `bool` che dice se la geometria della riga (A) e la geometria costante `other_wkb` (B) sono lo stesso insieme di punti, qualunque sia la loro rappresentazione: vertici in più su un lato, punto iniziale e verso degli anelli, ordine delle parti. |
| `geo.predicate_covers@1` | Aggiunge una colonna `bool` che dice se la geometria della riga (A) copre la geometria costante `other_wkb` (B): nessun punto di B è fuori da A, confine di A compreso. |
| `geo.predicate_covered_by@1` | Aggiunge una colonna `bool` che dice se la geometria della riga (A) è coperta dalla geometria costante `other_wkb` (B): nessun punto di A è fuori da B, confine di B compreso. |
| `geo.predicate_contains_properly@1` | Aggiunge una colonna `bool` che dice se la geometria della riga (A) contiene propriamente la geometria costante `other_wkb` (B): ogni punto di B è nell'interno di A, senza toccarne il confine. |
| `geo.predicate_touches@1` | Aggiunge una colonna `bool` che dice se la geometria della riga (A) e la geometria costante `other_wkb` (B) si toccano soltanto: hanno punti in comune, ma solo sui confini, mai fra gli interni. |
| `geo.predicate_crosses@1` | Aggiunge una colonna `bool` che dice se la geometria della riga (A) attraversa la geometria costante `other_wkb` (B): gli interni si intersecano, ma solo in parte. |
| `geo.predicate_overlaps@1` | Aggiunge una colonna `bool` che dice se la geometria della riga (A) e la geometria costante `other_wkb` (B) si sovrappongono: stessa dimensione, interni che si intersecano, e ciascuna con punti interni fuori dall'altra. |
| `geo.within@2` | Aggiunge alla sinistra un booleano che indica se la sua geometria sta dentro almeno una geometria destra; il solo bordo non basta. |

### Geo: trasformazioni (11)

| id@versione | sintesi |
| --- | --- |
| `geo.affine_transform@2` | Applica a ogni geometria la trasformazione affine 2D di matrice `[a, b, xoff, d, e, yoff]`: ogni vertice `(x, y)` diventa `(a x + b y + xoff, d x + e y + yoff)`. |
| `geo.translate@2` | Sposta ogni geometria di `(x_offset, y_offset)` nelle unità del CRS. |
| `geo.scale@2` | Scala ogni geometria di `x_factor` lungo x e `y_factor` lungo y attorno all'origine `(x_origin, y_origin)`, che resta ferma: `x' = x_factor x + x_origin (1 - x_factor)`, e lo stesso per y. |
| `geo.rotate@2` | Ruota ogni geometria di `degrees` gradi in verso antiorario attorno al centro `(x_origin, y_origin)`. |
| `geo.reproject@2` | Riproietta la colonna geometria dal suo CRS a `target_crs`, fra i CRS supportati, densificando i lati per conservarne la precisione. |
| `geo.simplify@3` | Semplifica le geometrie togliendo vertici con `douglas_peucker` o `preserve_topology`. |
| `geo.densify@3` | Aggiunge vertici ai lati delle geometrie: ogni lato più lungo di `max_segment_length` si divide in parti uguali, abbastanza da non superarla. |
| `geo.snap_to_grid@2` | Porta ogni vertice sul nodo più vicino di una griglia di passo `grid_size` con origine `(0, 0)`; non ripara i collassi. |
| `geo.snap@1` | Aggancia ogni vertice della geometria di ogni riga al vertice più vicino di una geometria di riferimento data nella config, se dista al più `tolerance`; i vertici più lontani restano dove sono. |
| `geo.make_valid@3` | Ripara le geometrie non valide secondo OGC; lascia invariate quelle valide e può cambiare il tipo della geometria riparata. |
| `geo.to_wkt@2` | Aggiunge una colonna `utf8` con il testo WKT della geometria di ogni riga. |

### Geo: overlay e insiemi (12)

| id@versione | sintesi |
| --- | --- |
| `geo.clip@2` | Ritaglia ogni poligono della sinistra sull'unione dei poligoni della destra. |
| `geo.difference@1` | Restituisce la parte dei poligoni di sinistra esterna ai poligoni di destra, come `MultiPolygon`. |
| `geo.intersection@1` | Restituisce l'intersezione dei poligoni di sinistra e di destra, come `MultiPolygon`. |
| `geo.union@2` | Restituisce l'unione dei poligoni di sinistra e di destra, come `MultiPolygon`. |
| `geo.symmetric_difference@1` | Restituisce le parti dei poligoni presenti in uno solo dei due ingressi, come `MultiPolygon`. |
| `geo.overlay@3` | Sovrappone due tabelle di poligoni e produce le intersezioni e, secondo `mode`, i resti, con la riga sorgente di ciascun lato. |
| `geo.dissolve@2` | Unisce tutti i poligoni della tabella in un solo `MultiPolygon`, fondendo le parti che si toccano o si sovrappongono. |
| `geo.collect@3` | Raggruppa per `group_by` e raccoglie le geometrie in una geometria per gruppo, senza unione topologica. |
| `geo.explode@1` | Spezza le geometrie multi-parte in una riga per parte: un `MultiPoint`, una `MultiLineString` o un `MultiPolygon` danno una riga per ogni punto, linea o poligono; una `GeometryCollection` una riga per ogni membro, di un solo livello (una collezione annidata resta una riga). |
| `geo.split@2` | Divide la geometria di ogni riga con una lama lineare e scrive una riga per parte, con gli attributi della riga d'origine e il suo indice in `__parent_index`. |
| `geo.subdivide@1` | Spezza le geometrie che superano `max_vertices` in parti entro la soglia, conservando gli attributi e l'indice sorgente in `__parent_index`. |
| `geo.clean_topology@2` | Pulisce poligoni già validi: chiude varchi stretti con `fill_gaps` e toglie le sovrapposizioni con `remove_overlaps`, dando precedenza alle righe precedenti. |

### Geo: linee (7)

| id@versione | sintesi |
| --- | --- |
| `geo.line_builder@2` | Costruisce una `LineString` dai punti della colonna geometria, nell'ordine delle righe. |
| `geo.line_interpolate_point@2` | Sostituisce ogni linea con il punto che sta alla frazione `ratio` della sua lunghezza, misurata dall'inizio: la distanza `ratio * L` si percorre lato per lato e il punto si interpola sul lato in cui cade. |
| `geo.line_locate_point@1` | Aggiunge una colonna `float64` con la posizione, lungo la linea di ogni riga, del punto della linea più vicino a un punto fisso dato nella config: la frazione della lunghezza totale da 0 (inizio) a 1 (fine), come `ST_LineLocatePoint` di PostGIS. |
| `geo.line_substring@2` | Sostituisce ogni linea con la sua porzione fra le frazioni `start_ratio` e `end_ratio` della lunghezza, misurate dall'inizio. |
| `geo.line_merge@3` | Fonde le linee in percorsi più lunghi possibile: due linee si uniscono in un estremo solo se quell'estremo è condiviso da esattamente due linee. |
| `geo.polygonize@3` | Costruisce i poligoni racchiusi dalle linee della tabella, una riga per faccia, e restituisce anche i residui classificati. |
| `geo.shared_paths@1` | Restituisce per ogni coppia di poligoni i tratti di confine condivisi, la lunghezza totale e le posizioni delle righe; esclude i soli contatti puntuali. |

### Geo: griglie e analisi (9)

| id@versione | sintesi |
| --- | --- |
| `geo.generate_grid@2` | Genera una griglia regolare di celle poligonali che copre il rettangolo `extent`, una riga per cella, con gli indici di colonna e di riga della cella e, a richiesta, il suo centro. |
| `geo.delaunay@3` | Triangola i vertici di ogni geometria (triangolazione di Delaunay non vincolata) e ne fa una riga per triangolo. |
| `geo.voronoi@3` | Sostituisce il punto di ogni riga con la sua cella di Voronoi, calcolata sui punti di tutte le righe: la regione del piano più vicina a quel punto che a ogni altro. |
| `geo.cluster_dbscan@1` | Raggruppa i punti per densità con DBSCAN e aggiunge l'etichetta del cluster; i punti di rumore ricevono null. |
| `geo.count_points_in_polygons@2` | Aggiunge alla sinistra il numero di geometrie della destra contenute in ogni sua geometria; i punti sul solo bordo non contano. |
| `geo.sjoin@3` | Esegue un join spaziale interno secondo `predicate`: una riga per coppia abbinata, con la posizione destra in `__right_index`. |
| `geo.nearest@2` | Abbina ogni riga sinistra alle righe destre alla minima distanza planare, includendo tutti i pari merito. |
| `geo.geometry_diagnostics@1` | Sostituisce la colonna geometria con dieci colonne che la descrivono: tipo, numero di coordinate, se è vuota, se ha solo coordinate finite, se è valida per l'OGC e perché no, e il rettangolo d'ingombro. |
| `geo.coverage_validate@2` | Segnala le coppie di poligoni con area sovrapposta maggiore di `tolerance`, con indici, area e geometria della sovrapposizione; non cerca i buchi. |

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
  `docs/limiti.md`, `docs/runner.md`, `docs/operazioni.md`,
  `docs/schede/<id>.md` e `crates/plenora-data-py/README.md`
  (documentazione SDK).
