# Piano di lavoro — 30 luglio 2026

Istantanea di coordinamento, **non normativa** e con data di scadenza breve. Lo
stato autorevole sta nelle fonti leggibili da macchina citate in Appendice A
dell'ICD. Se questa pagina e quelle divergono, prevalgono quelle.

## Il collo di bottiglia

Un'azione sola sblocca tutto il resto: **rieseguire la matrice di conformità con
il manifesto corretto**. Il risultato del 30 luglio, 26/39, non è utilizzabile
per decidere:

- undici fallimenti di data-tools erano l'assenza di `--features proj-backend`
  nel manifesto, non un difetto della libreria;
- l'unico caso superato da data-tools era un falso positivo: il runner accettava
  qualunque uscita diversa da zero come rifiuto corretto;
- il fallimento a carico di IO-tools era una fixture che chiedeva a un bordo di
  lettura di rifiutare, cioè il contrario di R4.6.1.

Tutte e tre le cause sono corrette in `conformance/`. Finché la matrice non è
rieseguita **non sappiamo dove siamo**, e ogni intervento sui componenti rischia
di inseguire un numero sbagliato.

Serve una toolchain Rust e i tre checkout alle revisioni di
`conformance/components.json`. Chi ha `cargo` esegue:

```
python conformance/corpus/generate.py --out conformance/cases
python conformance/run_roundtrip.py --checkouts .. --report roundtrip.json
```

## Owner

Due decisioni, entrambe economiche, entrambe sbloccanti.

**1. Ratificare le quattro voci a costo nullo.** §2, §3.4, §9 e §11.5–§11.10 sono
già adottate da tutti e tre i componenti: ratificarle non apre un solo gap e
porta il registro da 11 a 15 voci su 24. Vedi
[`RATIFICA-DECISIONI-APERTE.md`](RATIFICA-DECISIONI-APERTE.md).

Perché conta: `icd_ratification_alignment` è elencato fra i prerequisiti esterni
di IO-tools, e non è esterno. È una mattinata di lettura.

**2. Decidere sulla revisione indipendente.** È l'unica voce che nessun lavoro
tecnico chiude, ed è ferma su tutti e tre con
`no_eligible_reviewer_recorded`. L'owner è eleggibile per il codice delle tre
librerie, in quanto non autore. Non lo è per l'ICD chi lo ha co-redatto.

Non serve farla su tutto: una sola libreria revisionata sposta la scala dei claim
da `verified_internally` a `verified_independently` per quella, e dimostra che il
percorso esiste.

## IO-tools

Stato: `2f56844`, cinque flussi rc3 aperti su sette, `component_rc: false`. La
baseline rc2 resta un RC di componente taggato.

**1. Gap R4.6.1 — dichiarare l'incoerenza del CRS.** `driver.rs:579` confronta
l'SRID incorporato con quello dichiarato, ma solo per payload EWKB (R4.3.2). Su
WKB nessun confronto avviene: `crs_id=EPSG:4326` contro `srid=3003` passa in
silenzio. Manca la risoluzione del codice di autorità da `crs_id` e il confronto
con `plenora.geometry.srid`, con l'esito registrato nel `LossReport`.

Il meccanismo esiste (`plenora-io-core/src/loss.rs:155`) e la logica esiste
altrove (`authority_srid` in `plenora-database-core/src/field_contract.rs`): è da
sollevare, non da inventare. Non dipende dalla ratifica di R4.6 — un lettore che
vede due rappresentazioni discordanti e non lo dichiara perde informazione, e
R5 è ratificata.

**2. Riconsiderare lo scopo di rc3.** Streaming, pushdown FileGDB e ambiente GDAL
Windows sono tre lavori grossi e indipendenti; la via del bundling è chiusa dal
veto prestazionale, quindi il terzo è diventato più difficile. Un RC che aspetta
cinque cose non arriva; uno che ne aspetta due arriva e dichiara cosa non copre.

## data-tools

Stato: `e6f3f92`, **zero manifesti di rilascio**, ADR-0012 M2 chiuso con −16,2%
sulla catena completa.

**1. Manifesto di rilascio (C1).** È l'unico dei tre senza alcuna definizione di
RC: la distanza da un RC non è misurabile, non perché sia indietro. La forma
minima è in [`PLENORA-CRITERI-RC.md`](PLENORA-CRITERI-RC.md) e i tre manifesti di
IO-tools sono un esempio funzionante. Il gate
`scripts/check_release_manifest.py` lo verifica.

**2. Attendere la rieseguzione** prima di qualunque intervento sul contratto.
Oggi nessuna delle sue tredici verifiche è interpretabile.

## database-tools

Stato: `1292089`, 13/13 alla qualifica, **zero manifesti di rilascio**.

**1. Manifesto di rilascio (C1).** Stessa lacuna di data-tools, con un merito in
più da registrare: è l'unico componente con un esito di qualifica di sistema.

**2. Fissare l'immagine SQL Server.** `docker-compose.sqlserver.yml` usa
`mcr.microsoft.com/mssql/server:2022-latest`, un tag mobile: un aggiornamento a
monte cambia il risultato senza che nessuno abbia toccato niente. PostGIS è già
fissato bene. Cinque minuti, e chiude un residuo di C2.2.

## plenora-contracts

**1. Verificare il secondo obbligo di R4.6.1.** Il roundtrip controlla che i
metadati sopravvivano, non che l'incoerenza sia dichiarata. Dove l'attesa è
`preserve`, il record riporta `unverified_obligation` — è onesto, ma resta un
obbligo non verificato. Richiede di leggere il `LossReport` in forma leggibile da
macchina.

**2. Direzione inversa `database → data → IO`.** Dichiarata obbligatoria dal
gate, mai eseguita. Richiede un PostgreSQL vivo e un disegno che risolva lo stato
fra un caso e l'altro — schema nuovo per ogni caso. I due container esistono già
in database-tools.

**3. CI della conformità.** Un'esecuzione che avviene una volta è un aneddoto. Da
fare dopo che la matrice è verde, non prima: un gate rosso permanente su `main`
non aggiunge informazione.

## Ordine

1. Rieseguire la matrice. Cambia ciò che sappiamo di due componenti su tre.
2. In parallelo, senza dipendenze: le quattro ratifiche a costo nullo; il gap
   R4.6.1 su IO-tools; i due manifesti di rilascio; il pin di SQL Server.
3. Poi: §4.6 e §4.3.1–§4.3.3 ratificate insieme — sono la stessa materia, e
   separarle lascerebbe scoperto il punto che si è voluto chiarire.
4. Poi: §15.3 e l'estrazione del crate condiviso, con `field_contract.rs` come
   implementazione candidata.
5. Quando la matrice è verde: la CI della conformità, poi la direzione inversa.
