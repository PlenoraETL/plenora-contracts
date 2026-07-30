# Dati patrimoniali sporchi

Non è il corpus di conformità. Quello verifica proprietà note su casi da due
righe e produce un esito. Questo produce **sorprese**: file grandi, sporchi e
plausibili, nei formati che gli uffici tecnici usano davvero.

Il corpus contiene i modi di rompersi che qualcuno ha saputo immaginare. Un
archivio catastale vero contiene quelli che nessuno ha immaginato — e la
differenza si è vista alla prima esecuzione.

## Cosa genera

`generate_patrimonial.py` scrive uno shapefile completo (`.shp`, `.shx`, `.dbf`,
`.prj`, `.cpg`) più l'equivalente in Arrow IPC per il confronto. Le patologie non
sono inventate: sono quelle dei dati catastali italiani.

| Patologia | Cosa esercita |
|---|---|
| nomi di campo oltre dieci caratteri | il troncamento del DBF, fino alla collisione |
| accenti in CP1252, non UTF-8 | la codepage dichiarata in `.cpg` |
| codici con zeri iniziali | la distinzione fra testo e numero |
| identificativi oltre 2⁵³ | la fedeltà numerica a 64 bit |
| poligoni con buchi | l'anello interno, e il verso di avvolgimento |
| buchi avvolti nel verso sbagliato | la classificazione guscio/buco |
| poligoni auto-intersecanti, ad area nulla | le geometrie formalmente valide e semanticamente no |
| vertici duplicati, anelli non chiusi | la tolleranza alla malformazione |
| quote presenti ma tutte a zero | l'indistinguibilità da quota assente |
| `EPSG:3003` Monte Mario | coordinate a sette cifre, e un CRS proiettato italiano |

La distribuzione è deterministica — nessun `random` — così il dataset è
riproducibile e un difetto trovato oggi si ritrova domani.

## Esecuzione

```
python conformance/realdata/generate_patrimonial.py --out /percorso --rows 50000
```

Poi si dà in pasto a un componente. Nel container:

```
cargo run --locked -p plenora-io-cli -- convert /percorso/particelle.shp out.arrow
```

## Cosa ha trovato la prima passata

Tre reperti su `plenora-IO-tools` alla revisione `v0.1.0-rc.3`, 3.000 particelle
in shapefile `EPSG:3003`. Nessuno era raggiungibile dal corpus sintetico.

**1. Identificativi catastali che collassano, dichiarati senza perdita.** Il
campo DBF `N` largo 18 con zero decimali — la forma convenzionale di un intero —
è letto come `Float64`. **3.000 identificativi distinti diventano 1.501**:
`9007199254740993` e `9007199254740992` sono lo stesso `f64`. La conversione
riporta `lossless: true` e un rapporto di perdita vuoto.

**2. Due colonne diventano una, dichiarate senza perdita.**
`denominazione_catastale` e `denominazione_storica` troncano entrambe a
`DENOMINAZI`. In uscita c'è una sola colonna. Anche qui `lossless: true`.

**3. `EPSG:3003` classificato come geografico.** Monte Mario / Italy zone 1 è
proiettato — Transverse Mercator, unità metri. `inspect` riporta
`kind: geographic`, e poiché l'ordine degli assi è dedotto da quella
classificazione l'esito è `axis_order: unknown` invece di `easting_northing`.

I primi due riguardano R5, che è **ratificata**: una perdita non dichiarata è
una violazione di un vincolo in vigore, non un gap verso una proposta. Il terzo
riguarda R4.2.

## Due difetti del generatore, trovati dal lettore

Vanno registrati perché sono la ragione per cui il primo esito era illeggibile.

Il verso degli anelli era invertito: `_ring` deduceva l'orientamento dalla
direzione dell'indice invece di misurarlo. Ogni guscio usciva antiorario, cioè
un buco, e il lettore respingeva con `anello interno Shapefile senza anello
esterno`. Ora il verso si verifica con l'area con segno, che è la definizione e
non un'inferenza.

E la patologia `unclosed` produce un file che viola la specifica shapefile: il
rifiuto è la risposta corretta, non un difetto. È isolata perché un solo record
malformato rende illeggibile l'intero file — comportamento fail-closed
legittimo, ma che impedisce di misurare il resto.

In entrambi i casi il messaggio d'errore ha portato alla causa in un passo. Vale
la pena dirlo: un rifiuto diagnostico è ciò che ha reso utilizzabile questo
strumento.
