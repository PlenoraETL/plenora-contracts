# Piano di lavoro — 30 luglio 2026, sera

Istantanea di coordinamento, **non normativa** e con data di scadenza breve. Lo
stato autorevole sta nelle fonti leggibili da macchina citate in Appendice A
dell'ICD. Se questa pagina e quelle divergono, prevalgono quelle.

Sostituisce la versione del mattino, che dopo una giornata era sbagliata in ogni
riga.

## Il collo di bottiglia è uno, e non è tecnico

**La revisione indipendente.** Tutti e tre i componenti la portano, e per uno è
l'unico ostacolo rimasto:

| Componente | Come la registra |
|---|---|
| `plenora-database-tools` | `PLN-DB-REVIEW`, **unico blocker** dell'RC1. Nessun tag autorizzato finché non è registrata |
| `plenora-IO-tools` | `independent_review: assurance_attribute_open_non_blocking` |
| `plenora-data-tools` | dichiarata nel manifesto, `independent_review: false` |

L'owner è eleggibile per il codice di tutti e tre: è proprietario e non autore.
Non lo è per l'ICD chi lo ha co-redatto.

Non serve farla su tutti e tre. Una sola libreria revisionata sblocca un RC1,
sposta la scala dei claim da `verified_internally` a `verified_independently` per
quella, e dimostra che il percorso esiste. La condizione d'uscita più precisa è
quella di database-tools: identità e indipendenza del revisore, baseline esatta,
comandi, rilievi, loro chiusura, esito finale.

**La seconda decisione dell'owner** sono le ratifiche. Quattro voci sono già
adottate da tutti e tre e ratificarle non apre un solo gap — porta il registro da
11 a 15 su 25. E R4.6 sblocca `PLN-DB-R46` in database-tools e l'estrazione del
crate condiviso in IO-tools. Vedi
[`RATIFICA-DECISIONI-APERTE.md`](RATIFICA-DECISIONI-APERTE.md).

## Stato per componente

**`plenora-IO-tools` — `v0.1.0-rc.3` taggato, `component_rc: true`.**
Primo componente con un RC che include la dichiarazione dell'incoerenza CRS.
Lavora su rc4: streaming KML/DXF/XLSX, pushdown OpenFileGDB, matrice
GDAL/Windows. Un difetto aperto trovato con dati reali — `crs_kind` classifica
come geografico ogni CRS proiettato definito via WKT, perché controlla `GEOGCS[`
prima di `PROJCS[` e ogni WKT proiettato contiene un `GEOGCS` annidato. Riguarda
R4.2. Aperto anche un rilievo R5: perdita di precisione sui numerici DBF
riportata come `lossless: true`.

**`plenora-data-tools` — `1bee830`, M3 chiuso, manifesto che passa il gate.**
R4.6.3 attuato: il requisito di CRS è condizionato alle operazioni che lo usano.
Cinque blocchi aperti dichiarati, fra cui la copertura di `plenora-cli` al 59,5%.
Nessun RC dichiarato.

**`plenora-database-tools` — `245be06`, RC1 bloccata solo dalla review.**
Capability di scrittura complete, staging e swap transazionale inclusi. Manifesto
con riduzioni di ambito dichiarate e `runtime_policy` per area. Repository
congelato per scelta: nessun lavoro sul codice finché non arriva la review, la
ratifica di R4.6, o un rilievo critico.

## Qualifica di sistema

Eseguita due volte il 30 luglio, mai soddisfatta. L'ultima:
IO-tools 13/13, database-tools 13/13, data-tools 0/13 — e quello zero era il
container, non la libreria: mancavano `sqlite3` e le dipendenze di `bundled_proj`.
Corretto; la rieseguzione è la prima cosa da rifare quando serve un numero.

L'ambiente esiste ed è riproducibile: `conformance/Dockerfile` e
`conformance/run-in-container.sh`, un container solo, nessun database, nessuna
GDAL.

## Cosa resta a `plenora-contracts`

1. **Rieseguire la matrice** con il container corretto. È l'unica cosa che
   produce un numero di cui fidarsi.
2. **Verificare il secondo obbligo di R4.6.1.** Il roundtrip controlla che i
   metadati sopravvivano, non che l'incoerenza sia dichiarata: il `LossReport`
   dei reader non esce dalla CLI di IO-tools. Capacità richiesta già dichiarata
   in `components.json`.
3. **Direzione inversa `database → data → IO`.** Mai eseguita. Richiede un
   PostgreSQL vivo e uno schema nuovo per ogni caso.
4. **CI della conformità**, dopo che la matrice è verde e non prima: un gate
   rosso permanente insegna a ignorarlo.

## Cosa non fare

Aprire altro lavoro sul codice mentre tre componenti aspettano una decisione che
non è tecnica. Il progetto non è fermo per mancanza di cose da scrivere: è fermo
su due atti dell'owner che insieme valgono una mattinata.
