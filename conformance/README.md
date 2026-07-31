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

## Due varianti per caso

Ogni caso è generato due volte: con le sole chiavi canoniche di §2, e con in più
l'estensione GeoArrow `ARROW:extension:name`. Il suffisso `__geoarrow` distingue
la seconda.

Serve a separare due proprietà che il corpus confondeva. Con le sole chiavi
canoniche il driver IPC di `plenora-IO-tools` non riconosce la colonna come
geometrica — `inspect` riporta `geometry: false` — quindi propaga byte e
metadati intatti **senza averli letti**. È conservazione reale, richiesta da
R2.4, ma non è comprensione del contratto. `plenora-data-tools` e
`plenora-database-tools` invece le riconoscono.

Fino a rc12 il corpus portava solo la variante canonica, e un esito positivo su
IO-tools veniva letto come propagazione verificata del contratto: non lo era.
Le due varianti misurano le due cose separatamente, e verificano in più che i
due componenti che già riconoscono le canoniche si comportino identicamente
sulle due — cosa finora assunta da due controlli a campione.

`R2.8` propone che il riconoscimento dalle sole canoniche sia obbligatorio. È
`proposta`: finché non è ratificata, la variante canonica misura ciò che accade,
non ciò che deve accadere.

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
| `conflicting_crs` | `crs_id` e `srid` in conflitto: tre esiti per ruolo | R4.3.1, R4.6 |
| `geography_semantics` | `geography` non degradato a `geometry` | R4.4 |
| `types_mixed` | `types_declaration=mixed` distinto da `unresolved` | R3.4.1 |
| `int64_beyond_2_53` | interi oltre 2⁵³ non collassati | R5.3 |
| `uint64_ordering` | `u64` ordinati per valore, non come stringa | R5.3 |
| `unknown_key` | chiave non canonica propagata invariata | R2.4 |

`conflicting_crs` non ha un'attesa unica: ha tre comportamenti diversi e tutti
corretti sullo stesso dato, secondo R4.6.

| Ruolo | Atteso |
|---|---|
| bordo di lettura | preserva le rappresentazioni e dichiara l'incoerenza nel `LossReport` |
| centro | preserva le rappresentazioni **e** transita a `declared_unresolved` |
| bordo di scrittura | fallisce chiuso con categoria `Crs` |

La transizione al centro è **richiesta, non tollerata**. L'etichetta `resolved`
in ingresso afferma una risoluzione che il contenuto smentisce — `crs_id` e
`srid` si contraddicono — quindi un centro che la conserva rivendica una
risoluzione inesistente. Passare a `declared_unresolved` non cambia una verità:
scopre una menzogna, ed è esattamente ciò che quello stato significa. Le
rappresentazioni restano invariate: si corregge lo stato, non il dato.

Rilievo del team data-tools contro la formulazione precedente di questa fixture,
che pretendeva la conservazione dell'etichetta falsa. Accolto dall'owner.

`int64_beyond_2_53`, `uint64_ordering` e `unknown_key` corrispondono a difetti
realmente trovati durante la revisione iniziale: restano come regressione.

### Le fixture positive devono essere conformi

Il generatore rifiuta una fixture che dovrebbe attraversare la catena intatta ma
viola una regola dell'ICD. Una fixture del genere fa dipendere il corpus dal
fatto che quella regola **non** sia implementata: un componente conforme la
respinge, e il caso fallisce per la ragione sbagliata puntando al posto
sbagliato. Solo i casi dichiarati `fail_closed` possono essere incoerenti, ed è
esattamente ciò che verificano.

I controlli coprono R4.3.3 (`axis_order` obbligatorio in presenza di `crs_id` o
`crs_definition`), R4.3 (definizione e formato sono una coppia), R4.1
(`missing` non convive con un `crs_id`) e gli insiemi ammessi di `axis_order`,
`crs_resolution`, `dimensions` e `types_declaration`.

Le fixture del gate `plenora-system-contract-roundtrip-v1` dichiarato in
`plenora-IO-tools/release/system-rc-gate.json` sono coperte, con il nome del
gate riportato nel campo `gate_fixture` del contratto atteso. Il corpus aggiunge
l'ordine degli assi, la fedeltà numerica a 64 bit e `dimensions=unknown`, che il
gate non elenca.

## Il terzo componente

`plenora-database-cli inspect-dataset <file.arrow>` esiste dalla PR #17 di
plenora-database-tools: legge un dataset Arrow IPC, senza connessione, e riporta
il contratto che ne deriva secondo `plenora-database-core`, con l'ispezione
EWKB di ogni cella. La forma del comando era dichiarata qui in
`roundtrips[database].expected_output` **prima** dell'implementazione, e quella
consegnata vi coincide: il comparatore la legge senza modifiche.

Il terzo è di genere `arrow_to_contract`, non `arrow_to_arrow`: osserva il
dataset invece di riscriverlo. Per questo la catena di `run_chain.py` si esaurisce
in `io → data`, e il contratto in uscita è giudicato dal roundtrip del terzo.

L'oracolo che copriva parzialmente questo ruolo — `three-component-chain` in
IO-tools — è stato rimosso dalla baseline RC3: generava anche il dataset di
partenza, quindi il primo anello scriveva ciò su cui veniva giudicato. Il
comando attuale non ha quel difetto, perché il dataset lo genera PyArrow.

## Chi possiede la qualifica di sistema

Dalla baseline RC3 di IO-tools, il gate `plenora-system-contract-roundtrip-v1`
dichiara `ownership: external_system_qualification` e nomina questo perimetro
come proprietario. Le sue otto fixture, quindici proprietà e sei condizioni di
superamento vincolano `conformance/`, e `components.json` lo registra sotto
`satisfies_gate`.

Lo stato è `not_run`. L'osservazione storica di una tratta Point XYZ conservata
dal tag `v0.1.0-rc.2` resta citata in `system_qualification.historical_observation`
ma non contribuisce al superamento: non è evidenza della baseline corrente e non
proveniva da un giudice terzo.

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
