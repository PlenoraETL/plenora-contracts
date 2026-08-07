# Proposta di emendamento all'ICD — 2.0-rc18

**Oggetto:** vocabolario sul filo dei quattro assi, degradazione controllata dei
valori non riconosciuti, e separazione della disposizione della sessione dal
ritentativo.

**Regole proposte:** R9.15, R9.16, R9.17, R9.18 · **Regole emendate:** R9.7

**Origine:** rilievo del 2026-08-07. Quattro contraddizioni interne alla
specifica, tutte nella stessa area, tutte riprodotte. La quarta è emersa
dalla prima esecuzione della campagna contro un componente reale.

---

## 1. Le quattro contraddizioni

### 1.1 Il vocabolario sul filo non è specificato

L'ICD elenca i valori dei quattro assi in due modi diversi:

| tabella | vocabolario |
|---|---|
| categoria (R9.4) | `InvalidPlan`, `DataMapping` — PascalCase |
| fase (§9, riga 769) | `Validate`, `Connect` — PascalCase |
| effetto (R9.6) | `none`, `rolled_back` — snake_case |
| ritentativo (R9.7) | `never`, `safe` — snake_case |

Il documento non dice mai se quelle tabelle elencano i **valori sul filo** o gli
**identificatori del tipo**. Per effetto e ritentativo la forma non lascia
dubbi; per categoria e fase sì.

Le conseguenze sono già nel repository:

- i casi di `row-diagnostics-v1` scrivono `"category": "DataMapping"` e
  `"phase": "Read"` — hanno letto le tabelle come valori sul filo;
- i tre componenti serializzano con `rename_all = "snake_case"` ed emettono
  `data_mapping` e `read` — le hanno lette come identificatori di tipo.

**La campagna di conformance, eseguita contro un componente reale, fallirebbe
su due assi su quattro.** Non è stato notato perché il README della campagna
dichiara che gli oracoli non sono ancora stati confrontati con osservazioni
reali.

### 1.2 `quarantine` esiste in una metà della specifica

`conformance/campaigns/row-diagnostics-v1/cases.json` usa
`"retry": "quarantine"` in due casi, ratificati con `feat(contract): define
row-scoped diagnostics (#3)`. La tabella R9.7 elenca cinque valori e non lo
comprende.

Database Tools ha implementato i casi. IO Tools e Data Tools hanno implementato
la tabella. Nessuno dei tre ha sbagliato.

Dimostrazione della rottura, deserializzando con il tipo di IO Tools le sei
forme che Database Tools può emettere:

```
{"kind":"never"}                      -> letto
{"kind":"safe"}                       -> letto
{"kind":"requires_idempotency_key"}   -> letto
{"kind":"requires_recovery"}          -> letto
{"kind":"after","delay_ms":1500}      -> letto
{"kind":"quarantine"}                 -> RIFIUTATO: unknown variant `quarantine`
```

**Il consumer non ha perso un asse: ha perso l'envelope.** Categoria, fase ed
effetto erano leggibili e sono andati persi insieme al valore sconosciuto. Il
caso in cui accade è `cases.json` riga 273: categoria `DataMapping`, fase
`Rollback`, effetto `unknown` — un rollback dall'effetto incerto, cioè il
momento in cui la gestione dell'errore deve essere più affidabile.

### 1.3 Anche un campo nuovo distrugge l'envelope

*Rilevata dalla prima esecuzione della campagna contro un componente reale, non
prevista da questa proposta nella sua prima stesura.*

`PlenoraIoError` è deserializzato con `#[serde(deny_unknown_fields)]`. Un
envelope che porti un campo non previsto — per esempio l'asse sessione di
R9.18 — viene rifiutato **in blocco**:

```
unknown field `session`, expected one of `code`, `category`, `phase`, ...
```

La regola che introduce l'asse sessione violerebbe quindi la regola che
dovrebbe proteggerla: R9.18 sarebbe irricevibile dai componenti che non l'hanno
ancora adottata, cioè tutti tranne l'emittente.

### 1.4 La rappresentazione di `after` non è fissata

R9.7 dice `after(durata)` senza dire come la durata viaggia. IO Tools e
Database Tools usano `delay_ms` intero; Data Tools tiene una `Duration` e non
ha le derive serde. La divergenza è presente da prima del rilievo e non era mai
stata osservata.

---

## 2. Perché non basta correggere i quattro casi

Ogni contraddizione qui sopra si può chiudere con una modifica puntuale. Ma la
ragione per cui sono arrivate fin qui è la stessa per tutte, e resterebbe.

Gli assi viaggiano come enumerazioni chiuse: un valore non previsto fa fallire
la lettura dell'**intero** envelope, e il fallimento si manifesta nel consumer,
a runtime. Ogni valore aggiunto in futuro romperà allo stesso modo ogni
componente non ancora aggiornato — e i tre hanno release indipendenti, quindi
esistere disallineati è la condizione normale, non l'eccezione.

Il vocabolario per risolverlo è già nell'ICD: **R9.6** definisce `unknown` come
valore dell'asse effetto, cioè un valore che dichiara «non è determinabile»
invece di far cadere tutto. Manca sugli altri assi.

---

## 3. Testo proposto

### §9.15 — Vocabolario sul filo

> **R9.15** *(nuova 2.0-rc18)* Le tabelle dei valori d'asse di questo documento
> elencano i **valori sul filo**, non gli identificatori dei tipi che li
> implementano.
>
> Il vocabolario è `snake_case` per tutti e quattro gli assi. Le tabelle di
> categoria (R9.4) e fase, scritte in PascalCase, si leggono di conseguenza:
> `InvalidPlan` viaggia come `invalid_plan`, `DataMapping` come `data_mapping`,
> `Read` come `read`.
>
> Un componente **NON DEVE** emettere né accettare la forma PascalCase. Gli
> oracoli di conformance che la usano **DEVONO** essere aggiornati.
>
> La forma sul filo di ogni valore **DEVE** essere fissata caso per caso in una
> campagna di conformance. Un valore nuovo la cui forma non è fissata **NON È**
> parte del contratto.

### §9.16 — L'envelope non cade su un valore sconosciuto

> **R9.16** *(nuova 2.0-rc18)* Un consumer che riceve un **valore** che non
> conosce su un asse, o un **campo** che non conosce nell'envelope, **NON DEVE**
> far fallire la lettura. Gli altri assi e il messaggio **DEVONO** restare
> leggibili.
>
> Il valore o il campo ricevuto **DEVE** essere conservato così com'è. Un
> componente che inoltra l'envelope **DEVE** ritrasmetterlo invariato: non gli è
> consentito né normalizzare a un valore noto ciò che non ha compreso, né
> scartare un campo che non riconosce, perché il destinatario successivo
> potrebbe comprenderli.
>
> Di conseguenza l'envelope **NON DEVE** essere deserializzato con una politica
> che rifiuta i campi sconosciuti. È una rinuncia deliberata a una difesa
> normalmente corretta: su un piano o su una configurazione il rifiuto dei campi
> ignoti intercetta un refuso, ed è giusto tenerlo. Sull'envelope d'errore no —
> è l'unica struttura che **deve** sopravvivere al disallineamento fra versioni,
> perché è quella che viaggia proprio quando qualcosa è già andato storto. Un
> refuso in un campo dell'envelope produce un campo ignorato; il rifiuto
> produce la perdita dell'intera diagnosi.

### §9.17 — Il valore conservativo

> **R9.17** *(nuova 2.0-rc18)* Sugli assi che governano il comportamento del
> chiamante — **effetto** e **ritentativo** — un valore non riconosciuto
> **DEVE** essere interpretato come il valore conservativo dell'asse:
>
> | Asse | Valore conservativo | Perché |
> |---|---|---|
> | effetto | `unknown` | non si può asserire né che l'effetto ci sia né che non ci sia |
> | ritentativo | `requires_recovery` | prima di ritentare occorre accertare lo stato reale: è l'unica lettura sicura di una disposizione che non si comprende |
>
> Sugli assi descrittivi — **categoria** e **fase** — non esiste un valore
> conservativo, perché non determinano un'azione. Il valore ricevuto **DEVE**
> essere conservato e reso disponibile alla diagnostica, e il comportamento
> **DEVE** essere governato dagli altri due assi.
>
> Interpretare un valore ignoto come `safe` o come `none` **È VIETATO**: sono le
> due letture che autorizzano l'azione più rischiosa proprio quando
> l'informazione manca.

### §9.18 — Disposizione della sessione

> **R9.18** *(nuova 2.0-rc18)* La sorte della sessione che ha eseguito
> l'operazione è un **asse distinto** dal ritentativo, e ammette:
>
> | Valore | Significato |
> |---|---|
> | `reusable` | la sessione resta utilizzabile (predefinito) |
> | `discard` | la sessione va chiusa, il pool resta sano |
> | `quarantine` | né un ritentativo automatico né un riuso della connessione sono autorizzati finché l'effetto remoto non è stato verificato fuori banda |
>
> L'asse è **indipendente** da quello del ritentativo: una sessione riusabile
> può accompagnare un'operazione da riverificare, e una sessione in quarantena
> può accompagnare un'operazione che non va comunque ritentata.
>
> L'assenza dell'asse **DEVE** essere letta come `reusable`, così che un
> emittente che non lo dichiara resti conforme.

### §9.7 — Emendamento

> **R9.7** *(emendata 2.0-rc18)* La tabella dei valori resta a cinque:
> `never`, `safe`, `requires_idempotency_key`, `requires_recovery`,
> `after(durata)`.
>
> `quarantine` **NON** è un valore di questo asse: descrive la sessione, non
> l'operazione, e vive su R9.18. I casi di conformance di
> `plenora-row-diagnostics-v1` che lo collocano qui **DEVONO** essere
> aggiornati.
>
> La durata di `after` **DEVE** viaggiare come numero intero di millisecondi
> nel campo `delay_ms`. La rappresentazione interna è libera; una durata non
> rappresentabile **DEVE** saturare al massimo del campo e **NON DEVE**
> avvolgersi, perché un'attesa avvolta a zero produce un ritentativo immediato,
> cioè l'opposto di ciò che la disposizione chiedeva.

---

## 4. Conseguenze per i tre componenti

| | cosa cambia |
|---|---|
| **tutti e tre** | nulla sul filo per gli assi effetto e ritentativo: già `snake_case`. R9.15 li dichiara conformi e sposta la correzione sugli oracoli |
| **Database Tools** | `RetryDisposition::Quarantine` esce dall'enum; il concetto si sposta sul nuovo asse. Il valore continua a viaggiare, su un campo diverso |
| **IO Tools** | aggiunge l'asse sessione in lettura e la degradazione; `After` può passare a `Duration` senza toccare il filo |
| **Data Tools** | aggiunge le derive serde, oggi assenti, e fissa `delay_ms`; la degradazione vale anche qui |

R9.15 va nella direzione che costa meno: **i componenti hanno già ragione sul
filo**, sono le tabelle dell'ICD e gli oracoli a dover essere letti e riscritti
in `snake_case`. La scelta opposta — imporre PascalCase — obbligherebbe tutti e
tre a cambiare ciò che emettono, senza alcun guadagno.

## 5. Cosa deve verificare la conformance

Tre gate, oggi assenti:

1. **La forma sul filo di ogni valore di ogni asse**, fissata caso per caso ed
   esaustiva per costruzione: aggiungere un valore senza dichiararne la forma
   deve far fallire la campagna.
2. **La degradazione**: dato un envelope con un valore inventato su ciascun
   asse, ogni componente deve leggere gli altri assi e applicare il valore
   conservativo dove previsto.
3. **L'inoltro senza perdita**: un envelope che attraversa due componenti deve
   uscire con il valore sconosciuto invariato.

Il terzo è quello che tre implementazioni separate non possono garantire da
sole, ed è la ragione per cui `check_contract.py` — che dichiara di verificare
il documento e non i componenti — non basta.

## 6. Rapporto con §15

Questo emendamento **non anticipa** l'estrazione del crate condiviso e non ne
cambia l'ordine (R15.4.1). La degradazione è una proprietà del formato, e va
posseduta dai tre componenti anche mentre le implementazioni restano separate —
anzi soprattutto allora, perché è esattamente la condizione in cui il
disallineamento è normale.

Quando il crate sarà estratto, R9.15–R9.18 diventeranno una sola
implementazione invece di tre. Fino ad allora sono tre implementazioni con una
campagna che le confronta, che è ciò che oggi manca.

## 7. Registro

| Voce | Stato proposto | Nota |
|---|---|---|
| §9.15–§9.18 | `proposta` | nuova 2.0-rc18: vocabolario sul filo, degradazione controllata, asse sessione |
| §9 | `proposta` | emendata: R9.7 perde `quarantine` e fissa `delay_ms` |
| §9.9–§9.14 | `proposta` | i casi di `row-diagnostics-v1` vanno aggiornati su due punti: vocabolario degli assi e collocazione di `quarantine` |
