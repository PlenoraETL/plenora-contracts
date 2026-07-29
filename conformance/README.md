# Conformità della catena

Verifica che un dataset attraversi **IO-tools → data-tools → database-tools**
conservando il contratto dichiarato in `docs/PLENORA-CONTRATTI-TRASVERSALI.md`.

## Perché vive qui e non in un componente

Un test che verifica i tre non può essere ospitato da uno dei tre: chi lo ospita
ne controlla il merge, e un difetto nel proprio componente diventa un difetto nel
proprio giudice. §15.1 assegna a questo repository il ruolo di fonte autorevole,
e questo è il suo primo contenuto eseguibile.

## Perché il corpus è generato con PyArrow

Il corpus **non** è prodotto dai componenti che deve verificare. Se IO-tools
generasse i file che IO-tools rilegge, un difetto nel writer si annullerebbe con
il difetto speculare nel reader e il test passerebbe.

PyArrow è neutro rispetto ai tre, ed è anche l'ambiente dell'orchestratore reale:
generare il corpus da lì verifica in più il confine Python↔Rust, che è quello
attraverso cui il backend comporrà le pipeline.

## Struttura

```
corpus/generate.py     genera i casi in Arrow IPC + il contratto atteso
cases/                 output generato, non versionato
run_chain.py           esegue gli anelli disponibili e confronta
components.json        revisioni, invocazioni degli stadi, capacità mancanti
```

Gli stadi sono dichiarati in `components.json`, non nel runner: se una CLI
cambia forma, la correzione è un dato e non una modifica di codice.

## Casi coperti

Ogni caso isola una proprietà che si perde in silenzio quando un anello non la
propaga. Non sono casi felici: sono i modi documentati in cui un contratto
geospaziale si degrada senza errori.

| Caso | Proprietà verificata | Regola |
|---|---|---|
| `point_z` | dimensione `xyz` propagata, byte Z intatti | R3.3 |
| `point_zm` | `xyzm`, la M sopravvive a tutti e tre | R3.3 |
| `multipolygon_xyzm_srid` | geometria composta ZM con SRID non appiattita | R3.3 |
| `dimensions_unknown` | `unknown` non degradato a `xy` | R3.4 |
| `crs_unresolved` | `declared_unresolved` distinto da `missing` | R4.1 |
| `crs_missing` | `missing` distinto da `declared_unresolved` | R4.1 |
| `axis_lat_lon` | `EPSG:4326` lat/lon non confuso con `OGC:CRS84` | R4.2 |
| `conflicting_crs` | `crs_id` e `srid` in conflitto: **fallisce chiuso** | R4.3 |
| `geography_semantics` | `geography` non degradato a `geometry` | R4.4 |
| `types_mixed` | `types_declaration=mixed` distinto da `unresolved` | R3.4.1 |
| `int64_beyond_2_53` | interi oltre 2⁵³ non collassati | R5.3 |
| `uint64_ordering` | `u64` ordinati per valore, non come stringa | R5.3 |
| `unknown_key` | chiave non canonica propagata invariata | R2.4 |

`conflicting_crs` è l'unico caso il cui esito atteso è un errore: se un anello
concilia il conflitto in silenzio, sceglie un sistema di riferimento per conto
dell'utente su dati patrimoniali. Gli ultimi tre corrispondono a difetti
realmente trovati durante la revisione iniziale: restano come regressione.

Le fixture del gate `plenora-system-contract-roundtrip-v1` dichiarato in
`plenora-IO-tools/release/system-rc-gate.json` sono coperte, con il nome del
gate riportato nel campo `gate_fixture` del contratto atteso. Il corpus aggiunge
l'ordine degli assi, la fedeltà numerica a 64 bit e `dimensions=unknown`, che il
gate non elenca.

## Il terzo anello non è ancora eseguibile

`plenora-database-cli` non espone alcun comando che accetti un dataset Arrow IPC
e riporti il contratto geometrico che ne deriverebbe: ha `validate-plan`, che
valida un piano di scrittura e non un dataset, e i comandi `postgres-*`, che
richiedono un server attivo. Il runner salta lo stadio e **non lo conta come
superato**: con uno stadio saltato l'esito complessivo non è mai `0`.

L'unico controllo esistente sul terzo anello è l'oracolo Rust in
`plenora-IO-tools/conformance/three-component-chain`, che però genera anche il
dataset di partenza: il primo anello scrive ciò su cui verrà giudicato. Serve la
capacità dichiarata in `components.json` sotto `required_capability`.

## Esecuzione

```
python conformance/corpus/generate.py --out conformance/cases
python conformance/run_chain.py --checkouts .. --report report.json
```

Servono i tre checkout fratelli alle revisioni dichiarate in `components.json` e
una toolchain Rust. Il runner non modifica i repository dei componenti.

## Esito

Il runner confronta il contratto dopo ogni stadio con quello precedente e
riporta, per ogni proprietà persa o alterata, **in quale anello** è successo. Un
caso fallito non dice soltanto che la catena è rotta: dice dove.
