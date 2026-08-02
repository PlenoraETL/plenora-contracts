# Quindici decisioni di ratifica aperte

Il registro dell'ICD ha 29 voci: **14 ratificate**, 15 `proposta`. Questa pagina
serve a decidere voce per voce senza rileggere il documento.

**Perché conta.** Una regola `proposta` non vincola nessuno. Alla data di questa
pagina, due dei tre rilievi emersi dalla prima qualifica di sistema erano contro
regole non ratificate: tecnicamente nessun componente era in torto. Un registro
che rende opzionale ciò che è stato scritto perché serviva non protegge — sposta
solo il momento in cui il problema si presenta.

**Le tre uscite possibili per ogni voce.** Ratificare, cioè renderla vincolante e
accettare che un componente non conforme registri un gap o una deroga.
Cancellare, se non serve più. Lasciare `proposta` con una condizione di uscita
dichiarata — accettabile, ma solo se la condizione è scritta.

Nella colonna «adozione» sta ciò che i tre componenti già fanno, non ciò che
dovrebbero: ratificare una regola già adottata da tutti e tre costa quasi nulla,
ed è da lì che conviene cominciare.

## Costo quasi nullo — già adottata dai tre

*(§9 era in questo gruppo fino al 31 luglio 2026: rimossa dopo aver verificato
che l'adozione vale dentro le librerie e non al confine degli eseguibili, che è
il confine da cui Plenora le userà.)*

| Voce | Oggetto | Adozione | Cosa comporta ratificare |
|---|---|---|---|


## Costo reale — adozione parziale

| Voce | Oggetto | Adozione | Cosa comporta ratificare |
|---|---|---|---|
| §9 | Errore a quattro assi | **solo dentro le librerie**, non al confine CLI | Apre un gap su tutti e tre. I tipi Rust esistono, ma i tre eseguibili espongono gli assi in tre modi diversi: uno in JSON con gli assi dentro la prosa, uno in testo semplice, uno senza assi. R9.2 vieta di dedurre la ritentabilità dal messaggio, e un chiamante Python oggi non può fare altro |
| §9.9–§9.14 | Diagnostica row-scoped azionabile | **non ancora adottata**: IO-tools interrompe al primo record Shapefile invalido; database-tools conserva solo conteggi aggregati; data-tools non espone ancora lo schema comune | Apre un gap sui tre componenti. Richiede indici sorgente stabili, chiavi policy-safe, cause e conteggi completi con esempi bounded, più stato remoto esplicitamente non conoscibile. Corpus e judge sono definiti in `conformance/campaigns/row-diagnostics-v1/` |
| §2 | Chiavi metadata canoniche, lineage, e da rc12 il riconoscimento (R2.8) | **due su tre** | R2.8 dice che le chiavi canoniche bastano a riconoscere una colonna geometrica. data-tools e database-tools già lo fanno; il driver IPC di IO-tools richiede `ARROW:extension:name` e legge la colonna come binario opaco senza. Ratificarla apre un gap dichiarato su IO-tools e zero sugli altri due |
| §7 | Limiti pre-allocazione, budget ceduto lungo la catena | IO-tools parziale, gli altri due con lease | Un gap dichiarato a carico di IO-tools, oppure una deroga con rientro |
| §12 | Determinismo su quattro livelli | dichiarato da tutti, verificato in modo disuguale | Obbliga a produrre l'evidenza del livello dichiarato. È la voce che costa più lavoro di verifica |
| §10 | Capability dichiarative interrogabili | per driver e per provider, non uniforme | Obbliga a un'interfaccia comune di interrogazione. Tocca tutti e tre |
| §14 | Esiti di scrittura e pubblicazione | IO-tools e database-tools, non applicabile al centro | Basso. Va dichiarato che per data-tools non si applica |

## Le due che governano tutte le altre

| Voce | Oggetto | Nota |
|---|---|---|
| §0 | Disciplina di sviluppo, scala dei claim, revisione indipendente | Era assente dal registro fino a 2.0-rc14 pur essendo citata come operante: R0.4 è stata invocata quattro volte per stabilire che la ratifica non serve a un tag di componente, e non aveva uno stato |
| §16 | Deroghe, procedura di modifica e di ratifica | R16.3 stabilisce che l'owner può ratificare solo con le tre posizioni dei team e la revisione di R0.4. La regola che governa la ratifica non era a sua volta ratificata — un anello che va chiuso prima o insieme al primo atto |

Ratificarle è ricorsivo per costruzione: si ratifica secondo una procedura che
la ratifica stessa rende vincolante. Non è un paradosso, è il primo atto — e
vale la pena che sia esplicito invece di implicito.

## Decisioni di merito ancora aperte

| Voce | Oggetto | Nota |
|---|---|---|
| §4.6 | Collocazione del fail-closed, e da rc12 propagare contro scegliere quando i bordi coincidono (R4.6.5) | R4.6.1 è ora implementata da IO-tools. R4.6.5 risponde alla domanda che blocca `1.0.0-rc.1` di IO-tools: un comando che legge e scrive rifiuta solo quando la destinazione non può rappresentare l'incoerenza, cioè quando scrivere impone una scelta. Ratificarla sblocca quella RC |
| §4.3.1–§4.3.3 | Formato della definizione, precedenza fra rappresentazioni, coerenza con l'SRID EWKB | Solo `plenora-database-core` le rispetta. Ratificarle apre un gap su IO-tools — è il conflitto CRS accettato in silenzio |
| §4.5 | Riproiezione decisa dal centro, eseguibile dal bordo come pushdown | Emendamento di una regola 1.x che resta in vigore (R4.5.1). Finché non è ratificata vale la formulazione più restrittiva: nessun pushdown |
| §15.2 | Distribuzione: tag firmato e revisione esatta | Nessun tag di questo repository è firmato. Ratificarla richiede una baseline firmata prima di poterla rispettare |
| §15.3 | Contenuto e API del crate condiviso | Il crate non esiste. È il blocco del passo 2 di §15.4, e ora esiste un'implementazione candidata da estrarre: `field_contract.rs` di `plenora-database-core` |
| §15.4 | Passi della migrazione, doppia lettura prima della ratifica di §2 | Era prosa fino a 2.0-rc9 e non vincolava; promossa a regola in rc10. Ratificarla rende esigibile l'ordine dei passi e la deroga DER-ICD-002 sull'emissione canonica |

## Ordine suggerito

**Fatto il 31 luglio 2026**: §3.4, §11.5–§11.10 e §4.1.1 sono ratificate, e il
registro è passato da 11 a 14 su 28. Le prime due non hanno aperto un solo gap
perché tutti e tre le rispettavano già; la terza ne ha aperto uno solo, su
IO-tools, che l'aveva chiuso lo stesso giorno.

Nello stesso atto R16.3 è stata alleggerita con R16.3.1: le posizioni tecniche
servono solo dai componenti su cui la modifica apre un gap, e la revisione di
R0.4 solo quando la modifica cambia un comportamento. Chiedere tre firme per una
regola che nessuno deve cambiare produceva cerimonia e non informazione, e rendono esigibile ciò che i tre già
fanno. Poi §4.6 e §4.3.1–§4.3.3 insieme, perché sono la stessa materia e
ratificarle separatamente lascerebbe scoperto proprio il punto che si è voluto
chiarire. Poi §15.3, che sblocca il crate. Il resto quando l'evidenza esiste.

**Cosa non fare.** Ratificare tutto in blocco per portare il contatore a 25. Una
ratifica senza gap dichiarati né deroghe registrate è una dichiarazione di
conformità che nessuno ha verificato, e vale meno di una regola `proposta`
onesta.

---

Fonte dello stato: il registro in testa a
[`PLENORA-CONTRATTI-TRASVERSALI.md`](PLENORA-CONTRATTI-TRASVERSALI.md). Se le due
divergono, prevale il registro. L'adozione riportata qui è rilevata leggendo il
codice dei tre componenti, non dichiarata dalla loro documentazione.
