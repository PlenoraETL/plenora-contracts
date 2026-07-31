# Piano di integrazione in Plenora

Come i tre componenti entrano nel backend, in che ordine e chi fa cosa.

**Lo stato di partenza**, al 31 luglio 2026: tre release candidate taggate,
qualifica di sistema a 84/84 con la catena percorsa fino in fondo, un confine
Python provato contro i binari veri, e **nessuna riga di Plenora che giri sui
tre**. È quest'ultima la distanza vera.

Non è un documento normativo e non entra nel registro di ratifica. È un piano:
cambia quando i fatti lo smentiscono.

---

## Fase 0 — La fetta sottile · 2-3 settimane

**Non serve a integrare. Serve a misurare l'attrito.**

Una pipeline reale di Plenora — la più semplice che tocchi tutti e tre i confini
— ricostruita come tre invocazioni via il confine Python, eseguita su un dataset
vero, con l'uscita confrontata con quella che Plenora produce oggi.

| Chi | Cosa |
|---|---|
| `plenora-contracts` | costruisce ed esegue la fetta, riporta le differenze |
| owner | sceglie la pipeline, fornisce il dataset, **guarda il risultato su una mappa** |
| i tre team | nulla di programmato: rispondono a ciò che si rompe |

**Il deliverable non è una pipeline funzionante**: è la lista delle differenze di
comportamento fra il vecchio stack e il nuovo. Quella lista è il costo della
migrazione, e oggi nessuno la conosce.

Perché serve per prima: questa settimana tre attriti sono emersi per caso in
dieci minuti l'uno — il rifiuto su filesystem non riconosciuti, il
riconoscimento che dipendeva dall'estensione GeoArrow, la riproiezione che non
poteva eseguire. Una pipeline vera ne trova altri, e li trova **prima** che
qualcuno congeli una 1.0 finale attorno a un'ipotesi.

## Fase 1 — Il catalogo delle differenze · in parallelo alla 0

Le stesse operazioni eseguite sui due motori, con gli **output** confrontati —
non i nomi.

La mappatura del 31 luglio dice che 35 operazioni su 40 sono raggiungibili. Ma
«raggiungibile» non è «equivalente»: `geo.buffer` e `op_geo_buffer` sullo stesso
poligono possono dare risultati diversi, e nessuno lo ha verificato.

**Deliverable**: tre colonne — identica, diversa e accettabile, diversa e rompe.
La terza è il lavoro vero della migrazione.

## Fase 2 — Il bordo di lettura · 3-4 settimane

Il primo pezzo che entra davvero in Plenora, e non a caso è un **bordo**: si
integra da un lato solo. `plenora-IO-tools` sostituisce `carica` e `estrai` per
**un** formato, su un ramo. Il resto del backend continua identico — legge il
file con IO-tools, converte l'Arrow in GeoDataFrame, prosegue come prima.

Richiede il via esplicito dell'owner per toccare il backend, e comunque su ramo.

`plenora-IO-tools` è il componente più maturo — `v1.0.0-rc.2`, superficie
compatibile congelata, cinque RC alle spalle — quindi è il momento giusto perché
siano i primi.

## Fase 3 — Il bordo di scrittura · dopo la 2

`plenora-database-tools` sostituisce il percorso di scrittura. È il bordo dove il
danno è permanente, quindi è dove lo staging e lo swap transazionale valgono di
più.

Il componente è congelato per scelta propria, con tre condizioni di riapertura
dichiarate. **Questa fase è una di quelle**, e vale la pena che lo sappiano prima
di arrivarci.

## Fase 4 — Il centro · ultimo

`plenora-data-tools` si innesta **senza glue**: a quel punto il dato arriva già
in Arrow con il contratto canonico da un lato, e va a un consumatore che lo
capisce dall'altro. Integrarlo per primo avrebbe richiesto adattatori su
entrambi i lati, da buttare via subito dopo.

È anche il componente con le differenze di semantica più visibili all'utente —
riproiezione, rifiuto delle dimensioni non-XY, rifiuto dei filesystem non
riconosciuti. Farlo per ultimo significa affrontarle quando i due bordi sono
stabili e si sa che il problema è lì.

Il secondo cantiere di ADR-0014 — `clip`, `overlay`, booleane pairwise,
`dissolve` — serve a questa fase: sono tutte nella lista delle 40 operazioni che
Plenora usa oggi.

---

## In parallelo, senza dipendenze

**La direzione inversa** `database → data → IO`. Perimetro `conformance/`,
richiede un PostgreSQL vivo e uno schema nuovo per ogni caso. Non blocca le fasi
0-4 e chiude l'ultima condizione tecnica del gate di sistema.

**La revisione indipendente**, ferma su tutti e tre. È dell'owner, che è
eleggibile per il codice delle tre librerie in quanto proprietario e non autore.
Una sola libreria revisionata sposta la scala dei claim e dimostra che il
percorso esiste.

**Le quattordici voci `proposta`** del registro. Da guardare quando una serve,
non a calendario.

---

## Quello che resta fuori dal piano

**`arricchisci`** — 11.243 righe di arricchimento via API HTTP esterne. Nessuno
dei tre componenti fa HTTP, e va bene così: è lavoro legato alla latenza di rete,
dove Rust non compra nulla. Ma significa che la migrazione è parziale per disegno
e l'orchestratore vivrà a cavallo dei due mondi.

**L'orchestrazione** — circa 16.700 righe fra `orchestrator`, `scheduler`,
`eseguibili`, `task_runtime` e `lifecycle`. Va riscritta comunque, non per scelta
ma perché metà dei suoi import sparirà quando `carica`, `dataframes` e
`connections` non esisteranno più. Che forma prenda si decide dopo la fase 4, non
prima.

## Limiti dichiarati di chi scrive

`plenora-contracts` può eseguire, misurare e riportare. **Non può giudicare se il
risultato è geograficamente corretto**: una particella spostata di quaranta metri
per un'inversione d'assi ha coordinate valide, tipo valido e CRS dichiarato.
Serve qualcuno che la guardi su una mappa.

Non tocca il backend senza un via esplicito, e comunque su ramo.

E il tasso d'errore va tenuto presente: nella settimana in cui questo piano è
stato scritto, il perimetro di conformità ha prodotto sei difetti — tutti negli
strumenti di misura, nessuno nelle librerie. Davanti a un numero, la prima
domanda giusta resta se lo strumento funziona.
