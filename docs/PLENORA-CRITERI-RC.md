# Criteri di release candidate — Plenora

Versione **1.0-rc1**. Documento di **processo**, non di interfaccia: non
sostituisce né emenda `PLENORA-CONTRATTI-TRASVERSALI.md`, che resta l'unica
fonte normativa sul confine fra i componenti. In caso di conflitto sul contenuto
del contratto dati prevale l'ICD; questo documento non ha voce in capitolo su
quella materia.

## Registro di ratifica

Unica fonte sullo stato normativo di ciascun criterio. Nessuna affermazione
altrove lo sostituisce.

| Criterio | Oggetto | Stato | Nota |
|---|---|---|---|
| C1 | Manifesto di rilascio leggibile da macchina | `proposta` | nuovo 1.0-rc1 |
| C2 | Riproducibilità dell'evidenza | `proposta` | nuovo 1.0-rc1 |
| C3 | Separazione fra RC di componente e RC di sistema | `proposta` | nuovo 1.0-rc1 |
| C4 | Scala dei claim di verifica | `proposta` | rinvia a R0.4 e R0.5 dell'ICD |
| C5 | Enumerazione dei blocchi aperti | `proposta` | nuovo 1.0-rc1 |

La ratifica è atto dell'owner. Ratificare un criterio e conformarvisi sono atti
distinti: un componente non ancora conforme registra un gap, non riscrive il
criterio.

## Perché questo documento esiste

Tre componenti che usano la stessa parola con tre significati diversi rendono
quella parola inutile a chi deve decidere. Alla redazione di questa versione
`plenora-IO-tools` dispone di un apparato di rilascio completo, mentre gli altri
due non hanno una definizione di RC: non sono indietro, semplicemente la parola
non è definita per loro, e la distanza da un RC non è misurabile.

Questi criteri fissano **solo ciò che deve essere confrontabile fra i tre**. Non
stabiliscono quali test eseguire, quale copertura raggiungere, quali piattaforme
coprire: sono decisioni di ciascun team, e generalizzarle produrrebbe vaghezza o
prescrizioni sbagliate. Un componente che non tocca GDAL non ha una matrice
FileGDB da soddisfare.

Cinque criteri sulla comparabilità funzionano. Venticinque sulla completezza
diventano un adempimento da aggirare.

---

## C1 — Manifesto di rilascio leggibile da macchina

> **C1.1** Un componente che dichiara uno stato di rilascio **DEVE** pubblicare
> nel proprio repository almeno un manifesto in JSON che lo dichiari. Lo stato
> non **DEVE** vivere soltanto in prosa: un documento narrativo non è
> interrogabile e invecchia senza che nessuno lo noti.
>
> **C1.2** Il manifesto **DEVE** contenere: `manifest_version`, `component`,
> `component_version`, una `revision` di 40 cifre esadecimali che esista nella
> storia del repository, e un oggetto `claims`.
>
> **C1.3** `claims` **DEVE** contenere le tre chiavi booleane `component_rc`,
> `system_rc` e `avionic_certification`. L'assenza di una chiave non **DEVE**
> essere interpretata come `false`: va dichiarata.

**Perché.** Un booleano esplicito costringe a decidere. Un campo assente lascia
che il lettore assuma ciò che gli conviene, e chi legge un manifesto di rilascio
sta per prendere una decisione.

---

## C2 — Riproducibilità dell'evidenza

> **C2.1** Un risultato prodotto da un albero di lavoro con modifiche non
> committate **NON È** evidenza di rilascio. Può essere registrato come
> osservazione diagnostica, e in tal caso **DEVE** dichiararlo.
>
> **C2.2** Ogni evidenza citata da un manifesto **DEVE** indicare la revisione
> esatta da cui è stata prodotta, e quella revisione **DEVE** esistere nella
> storia del repository.
>
> **C2.3** Un'evidenza prodotta da uno strumento non versionato insieme al
> componente **DEVE** dichiarare la provenienza di quello strumento. Un'impronta
> registrata a posteriori da chi ha eseguito la corsa è una promessa, non
> un'evidenza: diventa evidenza quando lo strumento è pubblicato prima
> dell'esecuzione.

**Perché.** L'evidenza di rilascio serve a permettere a qualcun altro di
rieseguire e ottenere lo stesso risultato. Un risultato ottenuto su una macchina
sola, da codice mai pubblicato, non è verificabile da nessuno tranne chi l'ha
prodotto — e chi l'ha prodotto è la parte meno indicata a giudicarlo.

**Precedente.** Nella campagna fuzz di `plenora-IO-tools` del 29 luglio 2026 due
oracle non erano committati al momento dell'esecuzione. Il team ha rifiutato il
risultato come evidenza di RC pur avendo registrato le impronte dei file, li ha
committati e ha programmato la ripetizione. C2 generalizza quella decisione, che
era corretta.

**Nota sui confronti.** Una ripetizione da checkout pulito parte da un corpus più
povero di quello accumulato dalla corsa precedente. I conteggi non sono quindi
confrontabili, e la mancata comparabilità **DEVE** essere dichiarata accanto ai
risultati perché nessuno li legga come un peggioramento.

---

## C3 — Separazione fra RC di componente e RC di sistema

> **C3.1** Un RC di componente **NON IMPLICA** un RC di sistema, in nessuna
> direzione e a nessuna condizione. Un componente **PUÒ** dichiarare
> `component_rc: true` con `system_rc: false`; **NON DEVE** dichiarare
> `system_rc: true` sulla base delle proprie verifiche.
>
> **C3.2** La qualifica di sistema è posseduta dal perimetro `conformance/` di
> `plenora-contracts`. Un componente **NON DEVE** ospitare né eseguire test che
> compilano gli altri due: chi ospita un test ne controlla l'esito, e un
> componente non può essere giudice di sé stesso.
>
> **C3.3** Un componente **PUÒ** citare un'osservazione storica su una tratta
> multi-componente, purché la marchi come tale e non la conteggi come evidenza
> della propria baseline corrente.

**Perché.** Il guasto che questi criteri esistono per prevenire non è un
componente difettoso: è tre componenti corretti che, composti, perdono una
proprietà che nessuno dei tre si riteneva responsabile di conservare.

---

## C4 — Scala dei claim di verifica

> **C4.1** La scala dei claim è quella dell'ICD. `R0.4` stabilisce che finché il
> progetto non dispone di un revisore diverso dall'autore, lo stato massimo
> dichiarabile è `verificato internamente` e non `verificato indipendentemente`.
> Questo documento non la duplica e non la emenda.
>
> **C4.2** Il manifesto **DEVE** dichiarare quale claim rivendica, con un valore
> fra `verified_internally` e `verified_independently`, e **DEVE** dichiarare
> separatamente se la revisione indipendente è avvenuta.
>
> **C4.3** Un claim `verified_independently` **DEVE** registrare l'identità del
> revisore e la revisione revisionata. Un revisore non è eleggibile per il codice
> di cui è autore, né per un documento che ha co-redatto.
>
> **C4.4** Nessun componente **DEVE** dichiarare conformità a DO-178C, DO-330 o
> ad altro standard regolato: `R0.5` dell'ICD lo vieta in assenza di perimetro di
> sistema, livello di assurance, piani approvati ed autorità competente.
> `avionic_certification` **DEVE** valere `false`.

**Perché.** La revisione indipendente è l'unica voce che nessun lavoro tecnico
chiude. Tenerla come campo esplicito impedisce che si dissolva in un «abbiamo
controllato».

---

## C5 — Enumerazione dei blocchi aperti

> **C5.1** Un manifesto che dichiara uno stato diverso da rilasciato **DEVE**
> enumerare i blocchi aperti come elementi distinti, non riassumerli in prosa.
>
> **C5.2** Un blocco **NON DEVE** essere rimosso perché è stato aggirato: se una
> copertura è stata ridotta — un sottoinsieme di casi, una piattaforma non
> provata, un campionamento — la riduzione **DEVE** restare dichiarata.
>
> **C5.3** Un gate che fissa un record a un valore esatto è un cricchetto: fa
> fallire la verifica quando quel record cambia legittimamente. È il
> comportamento corretto, e la sua manutenzione **DEVE** essere prevista come
> atto deliberato — manifesto e gate si aggiornano nello stesso commit.

**Perché.** Una lista vuota si legge come «tutto coperto» anche quando significa
«non abbiamo guardato». L'enumerazione costringe a distinguere le due cose.

---

## Verifica

`scripts/check_release_manifest.py` verifica **C1, C2.2, C3.1, C4.2 e C4.4**, e
la sola forma. Accetta più manifesti insieme, perché C1.1 chiede *almeno un*
manifesto e un componente distribuisce lo stato su più file: i campi obbligatori
si cercano nella loro unione. Le revisioni che appartengono ad altri repository —
quella dell'ICD, quelle degli altri componenti — sono riconosciute e riportate
come non verificabili localmente, non come mancanti.

```
python scripts/check_release_manifest.py release/*.json --repo .
```

**Non verifica C2.1, C2.3, C3.2, C4.3, C5.1 e C5.2.** Richiedono un giudizio che
nessun controllo automatico può dare, sono dichiarati non automatizzati sia nel
documento sia nell'output del gate, e non esiste un controllo che finga di
coprirli.

`scripts/test_check_release_manifest.py` verifica che il gate scatti: dodici
violazioni sintetiche, una per criterio automatizzato, più un caso conforme che
deve passare. Un gate che sembra proteggere e non protegge è peggio di nessun
gate, perché chi lo legge assume una copertura che non c'è.

Il gate non è eseguito dalla CI di questo repository, che non ha accesso ai
repository dei componenti. È pensato per essere invocato dalla CI di ciascun
componente sui propri manifesti.

**Stato di conformità alla redazione.** `plenora-IO-tools` passa sull'unione dei
suoi tre manifesti. `plenora-data-tools` e `plenora-database-tools` non hanno
manifesti di rilascio: non c'è nulla da verificare, ed è il gap che C1 esiste per
rendere visibile.

## Come proporre una modifica

Come per l'ICD: indicare i criteri toccati, l'impatto sui tre componenti e il
piano di migrazione. I tre team registrano la propria posizione; l'owner ratifica
in assenza di rilievi bloccanti.
