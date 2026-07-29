# Tredici decisioni di ratifica aperte

Il registro dell'ICD ha 24 voci: 11 ratificate, 13 `proposta`. Questa pagina
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

| Voce | Oggetto | Adozione | Cosa comporta ratificare |
|---|---|---|---|
| §9 | Errore a quattro assi | tutti e tre, `plenora-database-core` è il riferimento | Nulla di tecnico. Rende esigibile la forma dell'errore attraverso i confini, che è la premessa di R14 e di ogni decisione di retry |
| §11.5–§11.10 | Cancellazione: token, attesa race-free, deadline, propagazione | tutti e tre | Nulla di tecnico. Vincola la forma del token, che il crate condiviso di §15.3 deve esportare |
| §2 | Chiavi metadata canoniche, versione del protocollo, lineage | tutti e tre, sotto deroga DER-ICD-002 | Chiude la deroga o le dà una condizione di rientro. È la voce più a valle di tutte: il corpus di conformità verifica queste chiavi |
| §3.4 | `unknown` non degradabile, tre stati di dichiarazione | tutti e tre | Nulla di tecnico. Rende esigibili due casi del corpus (`dimensions_unknown`, `types_mixed`) |

## Costo reale — adozione parziale

| Voce | Oggetto | Adozione | Cosa comporta ratificare |
|---|---|---|---|
| §7 | Limiti pre-allocazione, budget ceduto lungo la catena | IO-tools parziale, gli altri due con lease | Un gap dichiarato a carico di IO-tools, oppure una deroga con rientro |
| §12 | Determinismo su quattro livelli | dichiarato da tutti, verificato in modo disuguale | Obbliga a produrre l'evidenza del livello dichiarato. È la voce che costa più lavoro di verifica |
| §10 | Capability dichiarative interrogabili | per driver e per provider, non uniforme | Obbliga a un'interfaccia comune di interrogazione. Tocca tutti e tre |
| §14 | Esiti di scrittura e pubblicazione | IO-tools e database-tools, non applicabile al centro | Basso. Va dichiarato che per data-tools non si applica |

## Decisioni di merito ancora aperte

| Voce | Oggetto | Nota |
|---|---|---|
| §4.6 | Collocazione del fail-closed: rapporto in lettura, rifiuto in scrittura, decisione al centro | Decisa dall'owner il 30 luglio e scritta, non ancora ratificata. Nessuno dei tre la implementa: IO-tools non dichiara l'incoerenza, data-tools è da riesaminare. Ratificarla apre due gap veri |
| §4.3.1–§4.3.3 | Formato della definizione, precedenza fra rappresentazioni, coerenza con l'SRID EWKB | Solo `plenora-database-core` le rispetta. Ratificarle apre un gap su IO-tools — è il conflitto CRS accettato in silenzio |
| §4.5 | Riproiezione decisa dal centro, eseguibile dal bordo come pushdown | Emendamento di una regola 1.x che resta in vigore (R4.5.1). Finché non è ratificata vale la formulazione più restrittiva: nessun pushdown |
| §15.2 | Distribuzione: tag firmato e revisione esatta | Nessun tag di questo repository è firmato. Ratificarla richiede una baseline firmata prima di poterla rispettare |
| §15.3 | Contenuto e API del crate condiviso | Il crate non esiste. È il blocco del passo 2 di §15.4, e ora esiste un'implementazione candidata da estrarre: `field_contract.rs` di `plenora-database-core` |

## Ordine suggerito

Le quattro voci a costo quasi nullo prima: portano il registro da 11 a 15
ratificate su 24 senza aprire un solo gap, e rendono esigibile ciò che i tre già
fanno. Poi §4.6 e §4.3.1–§4.3.3 insieme, perché sono la stessa materia e
ratificarle separatamente lascerebbe scoperto proprio il punto che si è voluto
chiarire. Poi §15.3, che sblocca il crate. Il resto quando l'evidenza esiste.

**Cosa non fare.** Ratificare tutto in blocco per portare il contatore a 24. Una
ratifica senza gap dichiarati né deroghe registrate è una dichiarazione di
conformità che nessuno ha verificato, e vale meno di una regola `proposta`
onesta.

---

Fonte dello stato: il registro in testa a
[`PLENORA-CONTRATTI-TRASVERSALI.md`](PLENORA-CONTRATTI-TRASVERSALI.md). Se le due
divergono, prevale il registro. L'adozione riportata qui è rilevata leggendo il
codice dei tre componenti, non dichiarata dalla loro documentazione.
