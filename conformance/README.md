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
run_roundtrip.py       verifica ogni componente da solo — si esegue per primo
run_chain.py           esegue gli anelli in sequenza — conferma finale
components.json        revisioni, invocazioni, capacità attese
```

Invocazioni e revisioni sono dichiarate in `components.json`, non nei runner: se
una CLI cambia forma, la correzione è un dato e non una modifica di codice.

## Prima il roundtrip, poi la catena

I due runner non sono alternativi e non hanno lo stesso valore diagnostico.

`run_roundtrip.py` fa leggere a **un componente solo** il corpus e glielo fa
riscrivere, poi confronta. Se un componente conserva il contratto in entrata e
in uscita, ogni composizione lo conserva — quindi le sei direzioni fra i tre
(IO↔data, data↔database, IO↔database) sono coperte senza provarle una per una.
E quando un caso fallisce, il colpevole è già noto: non c'è catena da
bisezionare, non servono gli altri due checkout, non conta l'ordine.

`run_chain.py` fa passare il corpus attraverso gli anelli in sequenza. È il test
più costoso e quello che dice meno su *chi* ha sbagliato: serve a confermare che
l'integrazione regge, non a diagnosticare.

Il roundtrip di IO-tools e quello di data-tools sono eseguibili con le CLI che
già esistono, senza attendere il terzo.

Due generi di roundtrip, dichiarati in `components.json` sotto `kind`:

- `arrow_to_arrow` — il componente riscrive un file Arrow; si confrontano i
  metadati prima e dopo;
- `arrow_to_contract` — il componente osserva il dataset e stampa il contratto
  in JSON; si confronta l'osservato con quello dichiarato dal corpus.

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

## Il terzo componente

`plenora-database-cli` non espone ancora un comando che accetti un dataset Arrow
IPC e riporti il contratto geometrico che ne deriverebbe: ha `validate-plan`,
che valida un piano di scrittura e non un dataset, e i comandi `postgres-*`, che
richiedono un server attivo. La capacità è in corso di recepimento in
plenora-database-tools.

La forma attesa del comando è dichiarata in `components.json` sotto
`roundtrips[database].expected_output`, prima dell'implementazione: è il
repository dei contratti a specificare l'interfaccia, e se il comando reale
differirà si correggerà quel file, non i runner.

Finché non c'è, entrambi i runner riportano il terzo come non eseguito e **non
lo contano come superato**: con un roundtrip o uno stadio saltato l'esito
complessivo non è mai `0`.

L'unico controllo oggi esistente sul terzo anello è l'oracolo Rust in
`plenora-IO-tools/conformance/three-component-chain`, che però genera anche il
dataset di partenza: il primo anello scrive ciò su cui verrà giudicato.

## Esecuzione

```
python conformance/corpus/generate.py --out conformance/cases
python conformance/run_roundtrip.py --checkouts .. --report roundtrip.json
python conformance/run_chain.py     --checkouts .. --report chain.json
```

Servono i checkout fratelli alle revisioni dichiarate in `components.json` e una
toolchain Rust. `--component io` limita il roundtrip a un componente solo, che è
il modo per lavorarci senza gli altri due. I runner non modificano i repository
dei componenti.

## Esito

Il runner confronta il contratto dopo ogni stadio con quello precedente e
riporta, per ogni proprietà persa o alterata, **in quale anello** è successo. Un
caso fallito non dice soltanto che la catena è rotta: dice dove.
