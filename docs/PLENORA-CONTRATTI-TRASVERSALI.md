# Plenora — Contratti trasversali

**Documento normativo di interfaccia (ICD) · versione 2.0-rc11 · 30 luglio 2026**

> **Owner: Marco Bonamente.** Nominato il 27 luglio 2026.
>
> **Stato: parzialmente ratificato.**
>
> ## Registro di ratifica
>
> Questa tabella è l'**unica** fonte sullo stato normativo. Nessuna affermazione
> altrove nel documento, nei messaggi di commit o nei tag la sostituisce: dove
> divergono, prevale la tabella.
>
> Stati: **ratificata** (vincolante) · `proposta` (non vincolante: mai
> ratificata, oppure ratificata e poi riaperta da un rilievo accolto).
>
> **Clausola di chiusura.** Ogni regola non elencata qui ha stato `proposta`.
> Se compare nel corpo ma non in tabella, non obbliga nessuno.
>
> | Sezione | Oggetto | Stato | Nota |
> |---|---|---|---|
> | §1 | Versione Arrow unica e pinnata | **ratificata** | dal 27 lug |
> | §2 | Chiavi metadata canoniche, versione del protocollo, lineage | `proposta` | riaperta dopo i rilievi 2.0; emendata, attende ratifica |
> | §3.1 | Sedici tipi geometrici, forma `linestring` | **ratificata** | dal 27 lug |
> | §3.2 | Rifiuto esplicito dei tipi non supportati | **ratificata** | dal 27 lug |
> | §3.3 | Cinque dimensioni rappresentabili e propagabili | **ratificata** | dal 27 lug, ambito in R3.3.1 |
> | §3.4 | `unknown` non degradabile; tre stati di dichiarazione | `proposta` | emendata 2.0 |
> | §3.5 | Encoding come enumerazione chiusa | **ratificata** | dal 27 lug |
> | §4.1–§4.4 | CRS: tre stati, axis order non canonicalizzato, definizione preservata, nessun default | **ratificata** | dal 27 lug, testo 1.x |
> | §4.3.1–§4.3.3 | Formato della definizione, precedenza fra rappresentazioni, coerenza con l'SRID EWKB | `proposta` | nuove 2.0, dentro una sezione ratificata |
> | §4.5 | Riproiezione decisa dal centro, eseguibile dal bordo come pushdown | `proposta` | emendata 2.0 |
> | §4.6 | Collocazione del fail-closed: rapporto in lettura, rifiuto in scrittura, decisione al centro | `proposta` | nuova 2.0-rc9 |
> | §5 | Perdita di informazione mai silenziosa | **ratificata** | dal 27 lug |
> | §6 | Nessun panic nei crate `lib` | **ratificata** | dal 27 lug; R6.6-R6.7 sul gate minimo attendono ratifica |
> | §7 | Limiti pre-allocazione e budget ceduto lungo la catena | `proposta` | emendata 2.0 |
> | §8 | Identità di crate e colonne | **ratificata** | dal 27 lug |
> | §9 | Errore a quattro assi | `proposta` | emendata 2.0; già adottata dai tre |
> | §10 | Capability dichiarative interrogabili | `proposta` | forma da definire |
> | §11.5–§11.10 | Cancellazione: token, attesa asincrona race-free, deadline, token figli | `proposta` | emendata 2.0; già adottata dai tre |
> | §12 | Determinismo su quattro livelli | `proposta` | emendata 2.0 |
> | §13 | Toolchain e baseline riproducibile | **ratificata** | dal 27 lug |
> | §14 | Esiti di scrittura e pubblicazione | `proposta` | emendata 2.0 |
> | §15.1 | Repository autonomo come fonte autorevole | **ratificata** | dal 27 lug |
> | §15.2 | Distribuzione: tag firmato e revisione | `proposta` | vedi deroga DER-ICD-001 |
> | §15.3 | Contenuto e API del crate condiviso | `proposta` | il crate non va creato finché non è ratificata |
> | §15.4 | Passi della migrazione e doppia lettura prima della ratifica di §2 | `proposta` | nuova 2.0-rc11: era prosa fino a rc9, promossa a regola in rc10 senza riga di registro |
>
> **Effetto pratico.** Una sezione `proposta` non obbliga, ma non vieta: un
> componente può adottarla per scelta propria, e i tre lo stanno facendo su §9 e
> §11. Ciò che è vincolante va rispettato o derogato per iscritto (§16).
>
> Restano in vigore, indipendentemente da questa tabella, le regole che ciascun
> componente si è dato internamente. IO-tools ha chiuso la distinzione fra
> dimensioni legacy assenti ed `unknown` esplicito, dovuta per PLN-ASR-007 e
> H-01 a prescindere dallo stato di §3.4.
>
> **Cronologia.** §9 e §11 recepiscono i rilievi del team IO-tools; §5, §9 e §12
> la fotografia del team data-tools; l'Appendice A §R13.3 corregge un dato errato
> della 1.0. La 2.0 emenda le sei sezioni che erano `sospesa` e le sei `proposta`
> con rilievi aperti: nessuna sezione risulta più sospesa, tutte attendono
> ratifica. Le revisioni successive alla 2.0 aggiornano la fotografia
> dell'Appendice A e la forma normativa; la sola modifica di sostanza è
> l'emendamento di §15.4 in rc5 (emissione canonica ammessa con deroga
> registrata, DER-ICD-002).

Governa i confini fra i tre componenti Plenora sviluppati separatamente. Le regole
qui contenute prevalgono sulla documentazione locale dei singoli repository.

| Componente | Ruolo nella catena | Repository |
|---|---|---|
| **plenora-IO-tools** | Bordo verso i formati file | `plenora-IO-tools` |
| **plenora-data-tools** | Motore di trasformazione (centro) | `plenora-data-tools` |
| **plenora-database-tools** | Bordo verso i database | `plenora-database-tools` |

---

## §0 Come si usa questo documento

**Stato normativo.** Le regole usano `DEVE` / `NON DEVE` / `DOVREBBE` con il
significato consueto: `DEVE` è vincolante e la sua violazione blocca il merge;
`DOVREBBE` ammette deroga motivata secondo §16.

**Autorità.** In caso di conflitto fra questo documento e la documentazione di un
singolo repository (`Architetture.md`, ADR, `IMPLEMENTATION_STATUS.md`), prevale
questo documento. Gli ADR locali possono restringere una regola, mai allargarla.

**Verificabilità.** Ogni regola deve essere associata a un metodo e a un'evidenza
nella matrice di verifica del componente. Una regola che non si può verificare
meccanicamente è marcata `[ispezione]` e richiede evidenza scritta nella change
impact analysis. L'Appendice E stabilisce il minimo comune; ogni componente può
rafforzarlo.

**Aggancio all'assurance.** Le regole sono collegate agli hazard definiti in
`plenora-IO-tools/docs/assurance/TRACEABILITY.md` (H-01…H-09). Un componente che
viola una regola ha un hazard non controllato, non solo un difetto di stile.

> **R0.1** *(nuova 2.0-rc2)* Una dichiarazione di conformità **DEVE** essere
> sostenuta da evidenza riproducibile che identifichi almeno: requisito, hazard
> controllato, revisione del codice, configurazione e piattaforma, comando o caso
> di prova, risultato e data. L'ispezione del codice da sola non dimostra un
> requisito verificabile dinamicamente.
>
> **R0.2** *(nuova 2.0-rc2)* La tracciabilità **DEVE** essere bidirezionale:
> requisito → hazard → verifica ed evidenza, ed evidenza → requisito. Un requisito
> `DEVE` privo di verifica, o un test safety privo di requisito, è un gap di
> assurance.
>
> **R0.3** *(nuova 2.0-rc2)* La verifica dei requisiti che controllano H-01,
> H-02, H-04, H-05 o H-06 **DEVE** includere almeno un caso negativo o di fault
> injection e un valore limite pertinente. Il solo happy path non è evidenza
> sufficiente.
>
> **R0.4** *(nuova 2.0-rc2)* Una modifica a una regola ratificata, al relativo
> codice di confine o alla verifica che ne dimostra la conformità **DEVE** ricevere
> una revisione indipendente da una persona diversa dall'autore. Finché il
> progetto non dispone di tale revisore, lo stato massimo dichiarabile è
> `verificato internamente`, non `verificato indipendentemente`.
>
> **R0.5** *(nuova 2.0-rc2)* Questo ICD adotta una disciplina di sviluppo
> safety-critical, ma **NON** costituisce da solo conformità o certificazione
> avionica. Nessun componente **DEVE** dichiarare conformità a DO-178C,
> DO-330 o ad altro standard regolato senza perimetro di sistema, livello di
> assurance, piani approvati, evidenze complete e autorità competente
> identificati separatamente.

**Dove sta lo stato di fatto.** Il corpo di questo documento contiene solo
regole. La fotografia della conformità dei tre componenti sta **esclusivamente**
nell'Appendice A, ancorata a revisioni esatte. Nessuna sezione la ripete: una
fotografia duplicata invecchia sempre in un punto solo, ed è il modo in cui il
documento inizia a contraddirsi.

**Lettura minima per un team che parte.** §0, la regola che riguarda il proprio
confine, la riga del proprio componente nell'Appendice A, e la tabella di
rinomina in Appendice C.

---

## §1 R1 — Versione Arrow

> **R1.1** I tre componenti **DEVONO** dipendere dalla stessa versione esatta di
> Arrow, dichiarata con pin esatto (`=x.y.z`), non con caret.
>
> **R1.2** La versione corrente della baseline è **`=59.1.0`** per tutti i crate
> `arrow-*` e `parquet`.
>
> **R1.3** Un cambio di versione Arrow **DEVE** essere coordinato: i tre
> componenti cambiano nella stessa finestra, con una change impact analysis unica.

**Perché.** I `RecordBatch` attraversano i confini senza conversione solo se il
layout in memoria coincide. Una divergenza di versione non produce un errore di
compilazione al confine: produce due tipi `RecordBatch` incompatibili che il
sistema dei tipi tratta come estranei.

**Verifica.** `grep -h 'arrow-' */Cargo.toml` — tutte le occorrenze pinnate e uguali.

---

## §2 R2 — Chiavi dei metadati Arrow

Il trasporto delle proprietà geometriche fra componenti avviene tramite i
metadati di campo (`Field::metadata`) dello schema Arrow.

> **R2.1** Le chiavi **DEVONO** appartenere al namespace `plenora.` e usare la
> forma canonica della tabella sottostante. Nessun componente può introdurre un
> nome alternativo per una nozione già presente in tabella.
>
> **R2.2** Le proprietà **NON DEVONO** essere veicolate come blob serializzato in
> una chiave unica: ogni proprietà è una chiave separata, così un consumatore che
> ne ignora una non perde le altre.
>
> **R2.3** Le estensioni specifiche di un formato o di un provider **DEVONO** usare
> un sotto-namespace proprio (`plenora.filegdb.*`, `plenora.postgres.*`) e non
> possono duplicare una nozione canonica.
>
> **R2.4** *(emendata 2.0)* La propagazione di una chiave non interpretata segue
> la **lineage** del campo, non una regola unica:
>
> | Trasformazione | Regola |
> |---|---|
> | Identity-preserving (proiezione, rinomina, filtro di righe) | copia invariata |
> | Type-preserving (cast compatibile, riordino) | copia selettiva: cadono le chiavi la cui validità dipende dal tipo mutato |
> | Campo derivato (nuova geometria, aggregazione, union, join che fonde sorgenti) | ricostruzione dalle proprietà effettive del risultato; **NON** si eredita |
> | Conflitto fra più sorgenti con valori diversi | errore, oppure `LossReport` esplicito se il componente sa scegliere |
>
> Propagare invariata una chiave dopo un `aggregate` o la costruzione di una nuova
> geometria è una violazione di R5.1: descriverebbe il risultato con le proprietà
> dell'ingresso.
>
> **R2.5** *(nuova 2.0)* Ogni schema che porta chiavi canoniche **DEVE** dichiarare
> `plenora.contract.version` **nei metadati dello schema** (`Schema::metadata`),
> non in quelli dei singoli campi: la versione descrive il protocollo, non la
> colonna, e ripeterla per campo permetterebbe schemi internamente incoerenti. La versione corrente del protocollo dei metadati è
> **`1`**. Un consumatore che riceve una versione maggiore di quella che conosce
> **DEVE** fallire in modo esplicito, mai interpretare parzialmente.
>
> **R2.6** *(nuova 2.0)* Le chiavi definite da standard esterni — segnatamente
> `ARROW:extension:name` e `ARROW:extension:metadata` per GeoArrow — sono
> **ammesse ed esenti** da R2.1. Quando coesistono con le chiavi canoniche, le due
> descrizioni **DEVONO** essere coerenti; in caso di divergenza il componente
> **DEVE** fallire, non scegliere.
>
> **R2.7** *(nuova 2.0)* La precedenza — chiave canonica, poi legacy, poi standard
> esterno — si applica **solo quando le rappresentazioni di rango inferiore sono
> assenti o coerenti** con quella superiore. Se due rappresentazioni presenti
> divergono, vale R2.6: il componente fallisce, non sceglie. La precedenza è una
> regola di completamento, non di arbitrato, e **DEVE** essere decidibile senza
> ispezionare i dati.

### Chiavi canoniche

| Chiave | Valore | Obbligatoria |
|---|---|---|
| `plenora.geometry.encoding` | `wkb` \| `ewkb` | sì per colonne geometriche |
| `plenora.geometry.dimensions` | `xy` \| `xyz` \| `xym` \| `xyzm` \| `unknown` | sì |
| `plenora.geometry.types` | lista canonica separata da `,`: valori unici, ordinati come in §3.1, senza spazi | no; obbligatoria e non vuota se `types_declaration=exact` |
| `plenora.geometry.srid` | intero decimale senza segno | no |
| `plenora.geometry.crs_id` | identificatore d'autorità, es. `EPSG:4326` | no |
| `plenora.geometry.crs_resolution` | `resolved` \| `declared_unresolved` \| `missing` | sì |
| `plenora.geometry.crs_definition` | WKT o PROJJSON, testuale | no |
| `plenora.geometry.axis_order` | `lon_lat` \| `lat_lon` \| `easting_northing` \| `northing_easting` \| `other` \| `unknown` | sì se `crs_id` o `crs_definition` presente |
| `plenora.geometry.spatial_semantics` | `geometry` \| `geography` | no |
| `plenora.geometry.precision` | `float64` \| `float32` \| `native` | no |
| `plenora.field_id` | intero decimale senza segno | no |
| `plenora.contract.version` | intero decimale; oggi `1`. **Vive in `Schema::metadata`**, non nel campo | sì se sono presenti chiavi canoniche |
| `plenora.geometry.crs_definition_format` | `wkt` \| `wkt2` \| `projjson` | sì se `crs_definition` è presente |
| `plenora.geometry.types_declaration` | `exact` \| `mixed` \| `unresolved` | sì in emissione per colonne geometriche; vedi R3.4.1 |

**Perché R2.2.** Un blob unico è opaco: un componente che non sa deserializzarlo
perde tutte le proprietà insieme, e la perdita è silenziosa (H-01).

**Perché R2.4.** Il componente centrale non conosce le estensioni dei due bordi.
Se le elimina, un round-trip file → trasformazione → file perde i metadati nativi
che il driver aveva preservato con cura.

**Verifica.** `grep -rhoE '"plenora\.[a-z_.]+"' crates/ | sort -u` confrontato con
la tabella; test di round-trip dei metadati attraverso il componente centrale.

---

## §3 R3 — Modello geometrico

> **R3.1** I tipi geometrici canonici sono i sedici seguenti, serializzati in
> **minuscolo senza separatore**:
>
> `point` · `linestring` · `polygon` · `multipoint` · `multilinestring` ·
> `multipolygon` · `geometrycollection` · `circularstring` · `compoundcurve` ·
> `curvepolygon` · `multicurve` · `multisurface` · `polyhedralsurface` · `tin` ·
> `triangle` · `unknown`
>
> **R3.2** Un componente **PUÒ** supportare un sottoinsieme dei tipi, ma **DEVE**
> rifiutare esplicitamente quelli che non supporta. **NON DEVE** degradarli,
> approssimarli o ignorarli in silenzio.
>
> **R3.3** Le dimensioni canoniche sono `xy`, `xyz`, `xym`, `xyzm`, `unknown`.
> Ogni componente **DEVE** essere in grado di *rappresentare e propagare* tutte e
> cinque, anche quando non sa *elaborare* Z o M.
>
> **R3.3.1** *(ambito della ratifica del 27 luglio)* L'obbligo copre la
> rappresentazione nel contratto e la propagazione attraverso le operazioni che
> non ricostruiscono la geometria. **Non** impone di eseguire calcoli in tre
> dimensioni. Un componente che non sa elaborare Z o M **DEVE** rifiutare
> esplicitamente l'operazione (R3.2), mai eseguirla scartando le ordinate né
> dichiarare `xy` un dato che ne porta altre.
>
> **R3.4** `unknown` significa «byte preservati, dimensionalità non risolta». Un
> componente **NON DEVE** convertire `unknown` in `xy` per convenienza: è una
> reinterpretazione silenziosa dei dati (H-01).
>
> **R3.4.1** *(emendata 2.0)* Sul **tipo** geometrico vanno distinti tre stati, che
> la 1.x confondeva in `unknown`:
>
> | Stato | Chiave `types_declaration` | Significato |
> |---|---|---|
> | Dichiarazione esatta | `exact` | l'insieme dei tipi presenti è noto ed è quello elencato |
> | Dichiarazione eterogenea | `mixed` | la colonna ammette tipi diversi **per dichiarazione**: è informazione, non ignoranza (una colonna PostGIS `geometry` senza vincolo) |
> | Non risolto | `unresolved` | i byte non sono stati ispezionati e nessuna dichiarazione è disponibile |
>
> `types_declaration` è semanticamente distinta da
> `plenora.geometry.types`. `exact` richiede un elenco presente e non vuoto;
> `mixed` può portare l'elenco non vuoto dei tipi ammessi o osservati;
> `unresolved` **NON DEVE** portarlo, perché dichiarare tipi non è coerente con
> l'assenza di risoluzione. Quando presente, l'elenco **DEVE** contenere valori
> unici, nell'ordine canonico di §3.1 e senza spazi, così che una stessa
> dichiarazione abbia una sola serializzazione. Un produttore conforme **DEVE**
> emettere `types_declaration` per ogni colonna geometrica. Un consumatore può
> ricevere entrambe le chiavi assenti solo da un ingresso legacy: tale stato
> significa «proprietà non dichiarata» e va preservato o normalizzato con un
> `LossReport`, mai interpretato come `unresolved`. Un componente **NON DEVE**
> convertire `mixed` in `unresolved` né viceversa.
>
> **R3.5** L'encoding canonico è `wkb` o `ewkb`, come enumerazione chiusa. **NON
> DEVE** essere modellato come stringa libera.

**Perché la forma senza separatore (R3.1).** I valori serializzati vengono
confrontati con i tipi dichiarati dai sistemi esterni — PostGIS, GeoPackage, OGC
WKT — che usano tutti `LINESTRING`, `MULTIPOLYGON`. La forma `line_string`
richiederebbe una traduzione a ogni confine, e ogni traduzione è un punto in cui
si perde informazione.

**Perché R3.3 è la regola più costosa.** Impone di rappresentare e propagare una
dimensionalità che un componente può non saper elaborare. La regola non chiede
calcoli tridimensionali: chiede di non distruggere e di non descrivere in modo
errato ciò che si attraversa.

Vanno distinti tre comportamenti, perché solo il terzo è un difetto:

1. **Operazione geometrica su Z/M non supportata: rifiuto esplicito.** È
   fail-closed, conforme a R5.1 e R3.2.
2. **Operazione tabellare su dati Z/M: i byte transitano.** La colonna
   geometrica resta un buffer opaco e nulla si perde.
3. **Contratto che dichiara `xy` per dati che portano Z o M.** Questo è il
   difetto: non perdita di dati, ma un metadato che contraddice i byte che
   accompagna. Un consumatore che decide sulla dimensionalità dichiarata riceve
   un'informazione falsa. È H-01 nella forma «reinterpretazione», non in quella
   «perdita».

**Verifica.** `[ispezione]` sulle definizioni dei tipi; test di round-trip
end-to-end XYZM attraverso i tre componenti; grep di assegnazioni che portano a
`Xy` un valore letto dai metadati.

---

## §4 R4 — Sistema di riferimento (CRS)

> **R4.1** Lo stato di risoluzione del CRS **DEVE** distinguere tre casi:
> `resolved`, `declared_unresolved`, `missing`. Un componente **NON DEVE**
> collassarne due su una stessa rappresentazione, né nel modello interno né nei
> metadati che emette.
>
> **R4.2** L'ordine degli assi **DEVE** essere trasportato esplicitamente e **NON
> DEVE** essere canonicalizzato. `EPSG:4326` (lat/lon) e `OGC:CRS84` (lon/lat)
> **NON DEVONO** essere trattati come equivalenti.
>
> **R4.3** La definizione sorgente (WKT o PROJJSON) **DEVE** essere preservata
> quando disponibile, anche se il componente sa già risolvere l'identificatore. Il
> formato **DEVE** essere dichiarato in `plenora.geometry.crs_definition_format`:
> una definizione senza discriminatore non è interpretabile senza indovinare.
>
> **R4.3.1** *(nuova 2.0)* La precedenza fra le rappresentazioni del CRS è:
> **definizione** (`crs_definition` con il suo formato), poi **identificatore**
> (`crs_id`), poi **SRID** numerico. Quando due rappresentazioni sono presenti e
> discordano, il componente **DEVE** fallire con categoria `Crs`: non deve
> scegliere silenziosamente la più conveniente.
>
> **R4.3.2** *(nuova 2.0)* Se il payload è EWKB e porta un SRID incorporato,
> questo **DEVE** coincidere con `plenora.geometry.srid`. La divergenza è un
> errore, non una precedenza da risolvere.
>
> **R4.3.3** *(emendata 2.0)* `plenora.geometry.axis_order` ammette:
> `lon_lat`, `lat_lon`, `easting_northing`, `northing_easting`, `other`,
> `unknown`. È obbligatorio quando è presente `crs_id` **oppure**
> `crs_definition`: una definizione priva di identificatore non esime
> dal dichiarare l'ordine.
>
> **R4.4** Nessun componente **DEVE** assumere un CRS di default. In particolare,
> l'assenza di CRS **NON DEVE** essere interpretata come WGS84.
>
> **R4.5** *(emendata 2.0)* Il componente centrale è l'unico autorizzato a
> **decidere** una riproiezione. Un bordo **PUÒ eseguirla** come pushdown, a tre
> condizioni: che il centro l'abbia richiesta esplicitamente, che il bordo la
> dichiari fra le proprie capability (§10), e che non ne alteri parametri né
> semantica — CRS di partenza, CRS di arrivo e ordine degli assi restano quelli
> decisi dal centro. Un bordo **NON DEVE** riproiettare di propria iniziativa.
>
> **R4.5.1** *(testo 1.x, tuttora in vigore: resta la formulazione valida finché
> l'emendamento R4.5 non è ratificato)* La riproiezione è responsabilità esclusiva del componente centrale. I
> bordi **NON DEVONO** riproiettare: preservano il CRS sorgente e lo dichiarano.
>
> **R4.6** *(nuova 2.0-rc9)* Le regole di coerenza del CRS — in particolare
> R4.1, R4.3.1 e R4.3.2 — stabiliscono **cosa** è incoerente, non **dove** un
> componente deve rifiutare. La collocazione è la seguente:
>
> **R4.6.1** Un **bordo di lettura** che incontra un dato incoerente **NON DEVE**
> rifiutarlo per la sola incoerenza. **DEVE** leggerlo, preservare ogni
> rappresentazione così come si presenta senza conciliarla né sceglierne una, e
> **DEVE** dichiarare l'incoerenza nel proprio `LossReport` o
> `FidelityAssessment`. Rifiutare in lettura rende inservibile la funzione stessa
> del bordo: i file dei terzi vanno aperti come sono, non come dovrebbero essere.
>
> **R4.6.2** Un **bordo di scrittura** che sta per rendere permanente un dato
> incoerente **DEVE** fallire chiuso, con la semantica dei quattro assi di §7 e
> categoria `Crs`. Qui l'incoerenza non è più un'osservazione: è una scelta di
> sistema di riferimento fatta al posto dell'utente su un archivio che resterà.
>
> **R4.6.3** Il **componente centrale** è l'unico che **PUÒ decidere** come
> risolvere un'incoerenza, e la decisione **DEVE** essere esplicita nel piano.
> In assenza di una decisione nel piano il centro **DEVE** propagare
> l'incoerenza dichiarata senza risolverla. Il centro **NON DEVE** pretendere un
> CRS risolvibile per un'operazione che non lo richiede: un filtro tabellare su
> una colonna non geometrica non ha bisogno di alcun CRS, e rifiutarlo è più
> restrittivo del ruolo.
>
> **R4.6.4** Un'incoerenza dichiarata da un bordo di lettura e non risolta dal
> centro **DEVE** arrivare al bordo di scrittura, dove R4.6.2 la ferma. Nessun
> componente **DEVE** silenziarla lungo il percorso: propagarla non è tollerarla.

**Perché.** L'inversione lat/lon è il fallimento geospaziale più costoso e più
silenzioso che esista: produce coordinate plausibili in un punto sbagliato del
pianeta, senza alcun errore (H-06).

**Perché R4.6.** Senza collocazione, «il componente DEVE fallire» si legge come
«tutti e tre devono fallire», e produce due difetti opposti: un lettore che non
apre i file malfatti che è nato per aprire, e un archivio scritto con un sistema
di riferimento scelto da qualcuno che non aveva l'autorità per scegliere. Il
rifiuto va dove la conseguenza è permanente; la dichiarazione va dove
l'informazione nasce; la decisione va dove c'è un piano che la registra.

**Verifica.** `[ispezione]` più matrice di test axis-order per componente.

---

## §5 R5 — Perdita di informazione

> **R5.1** Nessuna conversione **DEVE** perdere dati o metadati in silenzio. Ogni
> perdita **DEVE** essere: rifiutata (fail-closed), oppure registrata in un
> report di perdita esplicito restituito al chiamante.
>
> **R5.2** Un valore di default **NON DEVE** sostituire un dato assente quando
> l'assenza è informativa. `unwrap_or(default)` su una proprietà del contratto è
> una violazione salvo motivazione nella CIA.
>
> **R5.3** Un ordinamento, un raggruppamento o un confronto **DEVE** usare la
> semantica nativa del tipo. La conversione a un tipo più povero per comodità di
> confronto è una violazione: `i64` oltre 2⁵³ convertito a `f64` collassa valori
> distinti; `u64` confrontato come stringa ordina `"10"` prima di `"9"`.
>
> **R5.4** Il troncamento numerico implicito attraverso un confine è vietato. Le
> conversioni fra larghezze **DEVONO** usare `try_from` con errore esplicito.

**Perché R5.3 è qui e non nel repository di data-tools.** È la regola che vale
per chiunque manipoli valori attraversando il confine: gli stessi dati devono
ordinarsi allo stesso modo nei tre componenti, altrimenti un risultato dipende da
quale libreria l'ha prodotto.

**Verifica.** Censimento di `unwrap_or`, `unwrap_or_default`, `unwrap_or_else` nei
crate `lib`; test di ordinamento su valori limite (`i64::MAX`, `u64` a più cifre);
grep dei cast `as` su tipi interi.

---

## §6 R6 — Fallimento invece di panic

> **R6.1** Nei crate **libreria**, un input esterno malformato **DEVE** produrre un
> errore tipizzato. **NON DEVE** produrre `panic`, in nessuna forma.
>
> **R6.2** I crate libreria **NON DEVONO** contenere `unsafe`, né le primitive
> `unwrap()`, `expect()`, `panic!`, `unreachable!`, `todo!`, `unimplemented!`.
>
> **R6.3** Il vincolo si applica ai soli target `--lib`. Le asserzioni nei test
> restano un meccanismo di verifica legittimo.
>
> **R6.4** Un'invariante che oggi giustifica un `expect` **DOVREBBE** essere
> codificata nel sistema dei tipi (newtype validato) anziché documentata in un
> messaggio.
>
> **R6.5** La sostituzione di una primitiva di panic **NON DEVE** introdurre un
> default silenzioso. `expect("X")` diventa `ok_or_else(|| errore("X"))?`, non
> `unwrap_or(valore)`: altrimenti si scambia un H-04 rumoroso con un H-01 muto,
> che è peggio.
>
> **R6.6** *(nuova 2.0)* Il gate Clippy è un **gate minimo** e non dimostra R6.1.
> Intercetta le primitive esplicite, non: indicizzazione fuori limite, overflow
> aritmetico, panic dentro le dipendenze, API di terze parti che panicano —
> incluse diverse di Arrow — esaurimento dello stack, o panic generati da macro.
> Un componente **NON DEVE** dichiarare R6.1 soddisfatta sulla sola base del gate.
>
> **R6.7** *(nuova 2.0)* R6.1 richiede evidenza complementare: fuzzing sugli
> input esterni, test sui valori limite dei tipi in ingresso, `overflow-checks`
> attivi anche in release per i crate di libreria, e un audit documentato delle
> API di terze parti che possono panicare.

**Verifica** — identica per i tre componenti, da aggiungere alla CI:

```
cargo clippy --workspace --lib --all-features --locked --
  -D warnings -D unsafe-code
  -D clippy::unwrap_used -D clippy::expect_used -D clippy::panic
  -D clippy::unreachable -D clippy::todo -D clippy::unimplemented
```

---

## §7 R7 — Limiti di risorsa

> **R7.1** Ogni operazione che alloca in funzione dell'input **DEVE** applicare un
> limite prima dell'allocazione, non dopo.
>
> **R7.2** I limiti **DEVONO** essere controllati dal chiamante, con un default
> documentato, e coprire almeno: byte totali, righe, colonne, componenti
> geometrici, profondità di annidamento.
>
> **R7.3** Le strutture ricorsive che attraversano un confine (AST, WKB annidato,
> piani) **DEVONO** avere un limite di profondità applicato **prima** della
> ricorsione, e la validazione stessa **DOVREBBE** essere iterativa, per non
> esaurire lo stack nel verificarlo.
>
> **R7.5** *(nuova 2.0)* Il budget di risorse **DEVE attraversare** la pipeline,
> non ripartire da capo in ogni componente. Tre limiti indipendenti da 512 MiB
> non valgono 512 MiB: ne valgono 1,5 GiB, e il consumo reale sfugge al
> chiamante.
>
> **R7.6** *(nuova 2.0)* Il budget condiviso **DEVE** offrire assegnazione per
> **lease**: un componente ottiene una quota, la consuma, la restituisce. Ogni
> aritmetica sul budget **DEVE** usare operazioni controllate (`checked_*`):
> un overflow che azzera il residuo è un limite disattivato in silenzio.
>
> **R7.7** *(nuova 2.0)* I limiti **DEVONO** coprire almeno: byte di memoria,
> righe, colonne, componenti geometrici, profondità di annidamento, **grado di
> concorrenza**, **fattore di espansione dell'output** rispetto all'ingresso,
> **tempo di CPU o durata**, **byte di spill su disco**, **dimensione della
> singola cella** e **rapporto di decompressione** per i formati compressi.
> L'assenza di quest'ultimo espone a decompression bomb (H-03).
>
> **R7.4** I limiti **DEVONO** essere espressi nelle stesse unità nei tre
> componenti: byte per la memoria, righe per il conteggio, millisecondi per il
> tempo. Un limite passato attraverso un confine non richiede conversione.

**Verifica.** `[ispezione]` dei punti di allocazione; fuzzing con input ostili.

---

## §8 R8 — Identità dei crate e delle colonne

> **R8.1** Due crate distinti **NON DEVONO** avere lo stesso nome di pacchetto.
>
> **R8.2** L'identità logica di una colonna è `FieldId(u32)`, stabile attraverso
> le rinomine e assegnata in un namespace globale del grafo.
>
> **R8.3** I tipi di confine **DEVONO** vivere in un crate condiviso, non essere
> ridefiniti in ciascun componente.
>
> **R8.4** Due tipi pubblici omonimi con forma diversa **NON DEVONO** esistere nel
> perimetro Plenora.

---

## §9 R9 — Modello di errore attraverso i confini

> **R9.1** *(emendata 2.0)* Un errore che attraversa un confine **DEVE** portare
> **quattro assi indipendenti**, più il messaggio:
>
> ```
> categoria   — che cosa è andato storto        (causa)
> fase        — dove, nel ciclo dell'operazione
> effetto     — che cosa resta sul sistema remoto o sul supporto
> ritentativo — che cosa può fare il chiamante
> ```
>
> Comprimere causa ed effetto su un solo asse **perde la causa**: un timeout dopo
> l'invio del commit ha causa `Timeout` ed effetto `Unknown`, e un modello a un
> asse costringe a scegliere quale delle due informazioni buttare.
>
> **R9.2** La ritentabilità **DEVE** essere esplicita e non dedotta dal messaggio.
> Un chiamante non deve interpretare del testo per decidere se riprovare.
>
> **R9.3** *(emendata 2.0)* L'esito ignoto **NON** è una categoria d'errore: è un
> valore dell'asse **effetto**. Un'operazione che non sa se è andata a buon fine
> **NON DEVE** essere riportata come fallita né come riuscita.
>
> **R9.6** *(nuova 2.0)* L'asse **effetto remoto** ammette:
>
> | Valore | Significato |
> |---|---|
> | `none` | l'operazione non ha prodotto alcun effetto osservabile |
> | `rolled_back` | l'effetto è stato annullato, con conferma |
> | `partial` | una parte dell'effetto è visibile e una no |
> | `committed` | l'effetto è definitivo, benché l'operazione riporti un errore |
> | `unknown` | l'effetto non è determinabile con i mezzi disponibili |
>
> **R9.7** *(nuova 2.0)* L'asse **ritentativo** sostituisce il booleano
> `retryable`, che è insufficiente e pericoloso: un timeout in lettura è
> ritentabile, lo stesso timeout dopo l'invio di un commit non lo è.
>
> | Valore | Significato |
> |---|---|
> | `never` | ritentare è sempre errato |
> | `safe` | l'operazione è idempotente o priva di effetti: si può ritentare |
> | `requires_idempotency_key` | ritentabile solo con una chiave che deduplichi l'effetto |
> | `requires_recovery` | prima di ritentare occorre accertare lo stato reale |
> | `after(durata)` | ritentabile non prima della durata indicata |
>
> La disposizione **DEVE** essere calcolata da fase, effetto e idempotenza
> dell'operazione, mai dalla sola categoria.
>
> **R9.8** *(nuova 2.0)* Il tipo condiviso che trasporta i quattro assi **NON
> DEVE** chiamarsi `PlenoraError`: quel nome designa già due tipi divergenti in
> IO-tools e data-tools, e un terzo omonimo aggraverebbe R8.4.
>
> **R9.4** I messaggi d'errore **NON DEVONO** contenere credenziali, stringhe di
> connessione, percorsi assoluti dell'ambiente o contenuto dei dati. Il
> riferimento al dato avviene per posizione (riga, colonna, offset), mai per valore.
>
> **R9.5** Le categorie d'errore **DEVONO** provenire da un'enumerazione condivisa.
> Un componente può usarne un sottoinsieme, non può inventarne di proprie.

**Perché R9.3.** È la distinzione che rende un'API onesta e che oggi solo
database-tools modella (`WriteStatus::OutcomeUnknown`, `ErrorCategory::OutcomeUnknown`,
e in IO-tools `PublishedButDurabilityUnconfirmed`). Se il commit di una
transazione fallisce dopo l'invio, l'operazione può essere andata a buon fine: dire
«fallito» invita a ritentare e a duplicare i dati (H-01, H-02).

**Perché R9.4.** Un messaggio d'errore attraversa i confini e finisce nei log.
È il canale attraverso cui i dati sfuggono al perimetro senza che nessuno se ne accorga.

### Enumerazione canonica delle categorie

Base: il modello di `plenora-database-tools`, esteso con le categorie che servono
ai bordi su filesystem e all'esecuzione delle trasformazioni. Ogni componente ne
usa il sottoinsieme che gli compete (R9.5); nessuno ne aggiunge.

| Categoria | Significato | Ritentabile |
|---|---|---|
| `InvalidPlan` | La richiesta è malformata o incoerente | no |
| `InvalidConfiguration` | La configurazione del componente è invalida | no |
| `Schema` | Schema Arrow o contratto dati incoerente | no |
| `DataMapping` | Un valore non è rappresentabile nella destinazione | no |
| `Crs` | CRS assente, irrisolto o incoerente | no |
| `Unsupported` | Capability non offerta dal componente | no |
| `NotFound` | Risorsa, layer o tabella inesistente | no |
| `Conflict` | Destinazione già esistente o conflitto di scrittura | no |
| `Authentication` | Credenziali assenti o rifiutate | no |
| `Authorization` | Permessi insufficienti | no |
| `Timeout` | Scadenza superata | dipende da fase ed effetto (R9.7) |
| `Cancelled` | Annullato dal chiamante | no |
| `ResourceLimit` | Limite di byte, righe, profondità o quota superato | no |
| `Io` | Errore del filesystem o del dispositivo | dipende |
| `Protocol` | Violazione del protocollo di trasporto o di rete | dipende |
| `Transient` | Condizione temporanea, ritentabile per natura | sì |
| `Execution` | Fallimento di un nodo durante la trasformazione | no |
| ~~`OutcomeUnknown`~~ | *rimossa in 2.0: è un valore dell'asse effetto, non una causa (R9.6)* | — |
| `Internal` | Invariante interna violata | no |

La colonna «ritentabile» è **indicativa e non normativa**: la disposizione
effettiva si calcola secondo R9.7 da fase, effetto e idempotenza. Nessun default
per categoria è sicuro — in particolare `Timeout`, che la 1.x dava come
ritentabile e che dopo l'invio di un commit non lo è.

### Enumerazione canonica delle fasi

`Validate` · `Connect` · `Probe` · `Prepare` · `Read` · `Write` · `Finalize` ·
`Commit` · `Rollback` · `Cleanup`

Per i bordi su filesystem, `Connect` copre l'acquisizione dell'handle e del lease
sulla risorsa, `Probe` l'ispezione preliminare del formato, `Commit` il rename
atomico di publish.

---

## §10 R10 — Capability e negoziazione

> **R10.1** Un componente che non può eseguire un'operazione richiesta **DEVE**
> fallire prima di iniziarla, non a metà.
>
> **R10.2** Le capability **DEVONO** essere interrogabili in forma dichiarativa e
> leggibile da un programma, prima dell'esecuzione, non desumibili per tentativi.
>
> **R10.3** Il rifiuto per capability mancante **DEVE** indicare quale capability
> manca, in forma tipizzata, non come messaggio libero.
>
> **R10.4** Una capability assente **NON DEVE** essere sostituita da un
> comportamento approssimato. La degradazione silenziosa è una violazione di R5.1.

**Perché.** Il valore di un modello di capability sta nel fallire *presto*: un
fallimento a metà scrittura lascia lo stato parziale che H-02 descrive.

---

## §11 R11 — Cancellazione

> **R11.1** Ogni operazione potenzialmente lunga **DEVE** accettare un segnale di
> cancellazione dal chiamante.
>
> **R11.2** La cancellazione **DEVE** essere cooperativa e osservata a intervalli
> limitati: fra un batch e il successivo come minimo.
>
> **R11.3** *(emendata 2.0)* Un'operazione cancellata **NON DEVE** lasciare output
> parziale visibile **quando la piattaforma consente di garantirlo**. Dove la
> garanzia non è ottenibile — perdita di connessione, crash del processo,
> destinazione non atomica — il componente **DEVE**: riportare l'effetto secondo
> R9.6 (`partial` o `unknown`), rendere disponibile una procedura di recovery, e
> **non** dichiarare uno stato che non ha verificato. La formulazione assoluta
> della 1.x prometteva ciò che nessun sistema può dimostrare dopo un crash.
>
> **R11.4** La cancellazione **DEVE** essere riportata come categoria d'errore
> propria, mai confusa con un fallimento o con un successo parziale.
>
> **R11.5** Il meccanismo canonico è un **token concreto e clonabile** definito nel
> crate condiviso, non un trait per componente. Il token **DEVE** essere `Send`,
> `Sync` e `Clone`; senza deadline, l'osservazione **DEVE** avere il fast path di
> una lettura atomica. Con deadline può aggiungere soltanto la lettura monotona
> del clock: resta non bloccante e senza allocazioni, perché va controllata fra
> un batch e il successivo.
>
> **R11.6** *(emendata 2.0)* Il token **DEVE** poter essere segnalato da un altro
> thread e **atteso** senza polling. L'osservazione a intervalli fra batch non
> basta: un'operazione bloccata su socket o su una query remota non raggiunge mai
> il punto di controllo successivo.
>
> **R11.7** *(nuova 2.0)* L'interfaccia minima del token è:
>
> ```
> is_cancelled() -> bool          osservazione non bloccante, costo di una lettura atomica
> cancel()                        segnalazione, idempotente
> cancelled() -> Future           attesa asincrona di cancel(), padre o segnale esterno
> deadline() -> Option<Instant>   scadenza oltre la quale il token si considera cancellato
> reason() -> Option<Reason>      motivo: richiesta esplicita, scadenza, propagazione dal padre
> child_token() -> Token          token figlio: cancellabile da solo, cancellato dal padre
> ```
>
> **R11.8** *(nuova 2.0)* La scadenza è parte del token, non un parametro separato:
> un'operazione che riceve token e timeout da due canali diversi non può garantire
> che il primo scada prima del secondo.
>
> **R11.9** *(nuova 2.0)* `cancelled()` **NON** richiede dipendenze esterne: il
> trait `Future` vive in `core::future` e il risveglio si implementa con
> `core::task::Waker` più un registro dei waker registrati. Il crate condiviso
> **NON DEVE** dipendere né da `futures-core` né da un runtime. Registrazione e
> controllo **DEVONO** essere privi della race «check-then-sleep»: il `poll`
> controlla lo stato, registra il waker e ricontrolla prima di restituire
> `Pending`; `cancel()` pubblica lo stato prima di risvegliare tutti gli
> attendenti. La rimozione di un future o di un token figlio **NON DEVE** causare
> crescita illimitata del registro.
>
> **R11.10** *(nuova 2.0)* La deadline è **dichiarativa**: il token la espone e
> `is_cancelled()` la valuta al momento della chiamata. Il risveglio *automatico*
> alla scadenza richiede un timer, che il crate non ha e non deve avere: è il
> chiamante a combinare `cancelled()` con il proprio meccanismo temporale, oppure
> a iniettare un clock e un notificatore. Il future restituito da `cancelled()`
> **NON DEVE** promettere da solo il risveglio alla deadline. Un token che lo
> promettesse senza un notificatore starebbe nascondendo una dipendenza da
> runtime.

**Perché un token concreto e non un trait (R11.5).** Un trait per componente è
un token per componente, non interoperabile: un'operazione che attraversa i tre
richiederebbe un adattatore per confine. L'obiettivo del contratto è che un token
creato dall'orchestratore attraversi i tre componenti invariato. La flessibilità del trait serve a chi deve
astrarre *implementazioni* diverse; qui l'implementazione è una sola e la
flessibilità che serve davvero — collegare una sorgente esterna di segnale — la
dà R11.6.

---

## §12 R12 — Determinismo e riproducibilità dei risultati

> **R12.1** *(emendata 2.0)* Il determinismo si dichiara su **quattro livelli
> distinti**, e ogni operazione **DEVE** dichiarare quale garantisce:
>
> | Livello | Garanzia |
> |---|---|
> | **Semantico** | stesso insieme di righe e stessi valori, a prescindere dall'ordine |
> | **Dell'ordine** | stessa sequenza di righe |
> | **Byte-for-byte** | stessa rappresentazione serializzata, bit per bit |
> | **Non ordinato** | dichiarazione esplicita che l'ordine **non** è garantito |
>
> A parità di input, opzioni e versione, il determinismo **semantico** è sempre
> dovuto. Nessun risultato può dipendere dalla schedulazione dei thread,
> dall'iterazione di una mappa non ordinata o dall'orologio.
>
> **R12.5** *(nuova 2.0)* Una sorgente remota non offre determinismo per sola
> lettura: una query senza `ORDER BY` non garantisce l'ordine, e i dati possono
> cambiare fra due esecuzioni. Quando il determinismo dell'ordine è richiesto su
> una sorgente remota, il componente **DEVE** imporre un ordinamento esplicito
> oppure dichiarare il risultato `non ordinato`. Dove la sorgente espone uno
> snapshot o una versione, questa **DEVE** essere registrata nel risultato.
>
> **R12.6** *(nuova 2.0)* Restano fuori dalla garanzia byte-for-byte, salvo
> dichiarazione esplicita: l'ordinamento di stringhe soggetto a collation, la
> rappresentazione dei valori in virgola mobile, la posizione dei `NaN`, le
> conversioni dipendenti dal fuso orario e le funzioni che leggono l'ora corrente.
>
> **R12.2** *(emendata 2.0)* Un ordinamento **DEVE** essere totale e stabile
> **oppure** dichiarare il risultato `non ordinato`. La totalità richiede un
> criterio di spareggio esplicito — una chiave univoca o l'indice di origine —
> che non sempre esiste: dove non esiste, la dichiarazione sostituisce la
> garanzia. Un ordine deciso dall'algoritmo di sort non è un ordine.
>
> **R12.3** L'esecuzione parallela e quella sequenziale **DEVONO** produrre lo
> stesso risultato. La soglia di parallelizzazione è un dettaglio prestazionale,
> mai semantico.
>
> **R12.4** Un percorso che ricade su disco (spill) **DEVE** produrre lo stesso
> risultato del percorso in memoria. Il superamento di una soglia di memoria non
> può cambiare l'output.

**Perché R12.4.** È la forma più insidiosa di non determinismo: il risultato
cambia in funzione della dimensione dei dati o della memoria disponibile, quindi
non si riproduce sulla macchina di chi lo segnala.

**Verifica.** Test di snapshot canonico; confronto esplicito fra percorso in
memoria e percorso con spill; confronto fra sopra e sotto la soglia di
parallelizzazione.

---

## §13 R13 — Toolchain e baseline

> **R13.1** I tre componenti **DEVONO** compilare con la stessa versione esatta
> del compilatore, fissata da un file `rust-toolchain.toml` versionato.
>
> **R13.2** La CI **DEVE** usare `--locked`. Un `Cargo.lock` modificato dalla
> build è un fallimento, non un aggiornamento.
>
> **R13.3** Le dipendenze **DEVONO** essere dichiarate con pin esatto e in un
> punto unico per workspace (`[workspace.dependencies]`).
>
> **R13.4** L'edition è `2021` e la versione minima dichiarata è `1.92` in tutti i
> crate.
>
> **R13.5** Ogni variazione di dipendenza o toolchain **DEVE** essere accompagnata
> da change impact analysis.

**Perché R13.1.** Una CI che installa «stable» compila con una versione diversa
ogni settimana: la baseline non è riproducibile e un difetto introdotto da un
cambio di compilatore è indistinguibile da uno di codice (H-07).

Il pin esatto va accompagnato da un controllo automatico che ne impedisca la
regressione: senza, un `cargo add` reintroduce un caret senza che nulla lo
segnali.

---

## §14 R14 — Esiti di scrittura e pubblicazione

> **R14.1** Un output **NON DEVE** sovrascrivere una destinazione esistente, salvo
> richiesta esplicita del chiamante. Il controllo **DEVE** essere atomico, non
> una verifica seguita da una scrittura.
>
> **R14.2** Quando la piattaforma offre una pubblicazione atomica, un output
> **DEVE** diventare visibile solo quando è completo. Quando non la offre,
> l'operazione **DEVE** essere rifiutata oppure dichiarare prima dell'esecuzione
> la capability non atomica; ogni stato parziale o ignoto segue R14.4. Un
> componente **NON DEVE** promettere invisibilità degli stati intermedi se non
> può garantirla.
>
> **R14.3** Una garanzia di durabilità **NON DEVE** essere dichiarata se la
> piattaforma non la conferma. L'esito **DEVE** distinguere «pubblicato e durevole»
> da «pubblicato, durabilità non confermata».
>
> **R14.4** *(emendata 2.0)* Un fallimento **DEVE** lasciare la destinazione nello
> stato precedente **e dichiararlo** solo quando il componente lo ha verificato.
> Dove l'atomicità è supportata, il rollback è confermato e l'effetto è
> `rolled_back` (R9.6). Dove non lo è — crash, perdita di connessione, provider
> non transazionale — l'effetto è `partial` o `unknown`, **DEVE** esistere una
> procedura di recovery, e il componente **NON DEVE** affermare di aver
> ripristinato ciò che non ha potuto osservare. Lo staging va ripulito in ogni
> caso in cui sia raggiungibile.
>
> **R14.5** Quando l'atomicità non è tecnicamente ottenibile, il componente
> **DEVE** dichiararlo nel proprio contratto anziché simularla.

**Perché.** H-02 e H-05 sono gli hazard che riguardano l'uscita, e valgono
identici su un file e su una tabella: sostituire un dataset pubblicato con uno
parziale ha lo stesso effetto sul consumatore, che si tratti di uno Shapefile o
di una tabella PostGIS.

---

## §15 Crate condiviso e migrazione

Le tre sottosezioni che seguono hanno stati normativi distinti nel registro e
vanno citate separatamente.

### §15.1 — Repository e autorità

> **R15.1.1** Il documento normativo e il crate dei tipi di confine **DEVONO**
> risiedere in un repository autonomo, condiviso fra i tre team e **non** interno
> a uno dei tre componenti. Il repository è `plenora-contracts`.
>
> **R15.1.2** Documento e crate **DEVONO** condividere lo stesso repository e la
> stessa versione: quando cambia il contratto cambiano insieme, e una change
> impact analysis può citare un riferimento unico.
>
> **R15.1.3** Una collocazione provvisoria altrove è ammessa solo se dichiarata
> tale secondo §16, con condizione di rientro esplicita.

**Perché non in uno dei tre.** Chi ospita un contratto ne controlla di fatto il
merge, e un componente non può essere giudice di sé stesso.

### §15.2 — Distribuzione e immutabilità del riferimento

> **R15.2.1** La dipendenza dal crate **DEVE** essere risolta per revisione
> esatta, registrata nel `Cargo.lock`, e la CI **DEVE** usare `--locked`.
>
> **R15.2.2** *(emendata 2.0)* Il riferimento umano a una versione del contratto
> **DEVE** essere un tag annotato e firmato. Un tag è spostabile: la firma lega il
> nome al contenuto, e la revisione registrata nel `Cargo.lock` lega la build a un
> commit preciso. Le due protezioni sono complementari e servono entrambe.
>
> **R15.2.3** *(rinumerata)* Ogni change impact analysis **DEVE** citare il tag
> **e** la revisione, non il solo tag.
>
> **R15.2.4** La distribuzione per `path` locale è **vietata**: riprodurrebbe il
> problema che il crate deve risolvere, dando a ogni team una copia non
> verificabile — un terzo modello anziché un contratto comune.

### §15.3 — Contenuto e API del crate

> **R15.3.1** Il crate **DEVE** essere definito nella sua interezza prima di
> essere creato: un'estrazione parziale costringerebbe i team ad adottarlo due
> volte.
>
> **R15.3.2** Il crate **NON DEVE** dipendere da altro che dai crate strettamente
> necessari ai tipi di confine, e **NON DEVE** contenere `unsafe` né primitive di
> panic.

| Attributo | Valore |
|---|---|
| Nome del pacchetto | `plenora-contracts` |
| Versione iniziale | `0.1.0`, `publish = false` |
| Contenuto — geometria e CRS | `FieldId`, `CoordinateDimensions`, `GeometryType`, `TypesDeclaration` (R3.4.1), `GeometryEncoding`, `SpatialSemantics`, `CrsResolution`, `ResolvedCrs`, `CrsDefinitionFormat`, `AxisOrder` |
| Contenuto — protocollo | costanti delle chiavi §2, `ContractVersion` (R2.5), policy di lineage (R2.4) |
| Contenuto — esiti e errori | envelope a quattro assi (R9.1) con `ErrorCategory`, `ErrorPhase`, `RemoteEffect` (R9.6), `RetryDisposition` (R9.7); `WriteOutcome` e handle di recovery (R14.4). Il tipo **non** si chiama `PlenoraError` (R9.8) |
| Contenuto — risorse e controllo | `ResourceBudget` con lease e aritmetica controllata (R7.6), `CancellationToken` completo (R11.7) |
| Contenuto — fedeltà | `LossReport` e la policy che stabilisce quando è obbligatorio (R5.1) |
| Contenuto — capability | descrizione dichiarativa interrogabile prima dell'esecuzione (§10), inclusa la capability di pushdown della riproiezione (R4.5) |
| Vincoli di dipendenza | `serde` e `arrow-schema`; `cancelled()` usa `core::future::Future` e `core::task::Waker`. **Né `futures-core` né runtime asincroni.** Nessun `unsafe`, nessuna primitiva di panic |

### §15.4 — Migrazione

> **R15.4.1** La convergenza avviene per passi verificabili e indipendenti, in
> quest'ordine: allineamento delle chiavi §2; estrazione del crate a semantica
> zero dai tipi di confine di `plenora-io-model`; adozione da parte di
> data-tools e database-tools, una per volta con la propria change impact
> analysis; allargamento del modello geometrico solo quando i tre dipendono
> dallo stesso crate.
>
> **R15.4.2** Prima della ratifica di §2 la doppia lettura è sempre consentita.
> L'**emissione** canonica richiede una deroga registrata nel repository che la
> pratica, con l'hazard per i consumatori non allineati e la condizione di
> rientro. Tutti e tre sono oggi in questa condizione: vedi DER-ICD-002.

**Perché l'estrazione parte da `plenora-io-model`.** Non per maturità, ma perché
i vincoli dei formati file non sono negoziabili: `unknown`,
`declared_unresolved` e l'ordine degli assi non canonicalizzato sono scoperte
fatte contro dati reali, non scelte rifacibili a tavolino. L'eccezione è il
modello d'errore di §9, dove il riferimento è `plenora-database-core`.

Il piano operativo dei passi vivrà nel README del crate, non qui: un documento
normativo dice cosa deve valere, non come si organizza il lavoro.

## §16 Deroghe e modifiche

> **R16.1 — Deroga.** Un componente che non può rispettare una regola **DEVE**
> dichiararlo esplicitamente: regola, motivo, impatto sugli hazard, owner della
> deroga e condizione di rientro. Una deroga dichiarata è un gap noto; una regola
> aggirata in silenzio è un difetto.
>
> **R16.2 — Registro.** Le deroghe attive **DEVONO** essere elencate in un punto
> solo per componente, così che si possano contare. Una deroga senza condizione
> di rientro è permanente: va scritto.
>
> **R16.3 — Modifica e ratifica.** Una proposta di modifica **DEVE** indicare:
> regole toccate, impatto sui tre componenti, hazard interessati, piano di
> migrazione e retrocompatibilità. Ciascun team **DEVE** registrare la propria
> posizione tecnica (`accetta`, `accetta con deroga`, `rilievo bloccante`) su una
> revisione esatta. L'owner è l'unica autorità che cambia lo stato nel registro e
> **PUÒ** ratificare solo quando non esistono rilievi bloccanti aperti e sono
> disponibili le tre posizioni e la revisione richiesta da R0.4. L'atto di
> ratifica **DEVE** registrare data, commit e tag firmato della baseline.
>
> Ratificare un requisito e implementarlo sono atti distinti: la ratifica lo
> rende vincolante; un componente non ancora conforme registra un gap o una
> deroga. Fino alla ratifica resta vincolante la precedente baseline ratificata.
>
> **R16.4 — Versionamento.** Questo documento **DEVE** essere versionato in un
> repository, non distribuito come file sciolto: senza storia non esiste
> baseline, i team non sanno a quale versione si stanno conformando e nessuna
> change impact analysis è possibile. La versione è dichiarata in testa al
> documento e citata nelle CIA.
>
> **R16.5 — Proprietà.** Questo documento **DEVE** avere un owner nominato.
> L'owner controlla il registro ma **NON DEVE** sostituire la revisione
> indipendente richiesta da R0.4 quando è anche autore della modifica. Un
> contratto trasversale senza proprietario diventa tre interpretazioni
> divergenti: è già successo con i due `plenora-core`, ricopiati consapevolmente
> e poi lasciati derivare fino a definire due `PlenoraError` incompatibili.

---

## §16-ter Deroghe attive di questo documento

| ID | Regola | Motivo | Rientro |
|---|---|---|---|
| DER-ICD-001 | R15.2.2 — tag annotati **e firmati** | Nessuna chiave di firma nell'ambiente in cui il documento è mantenuto: i tag pubblicati sono annotati ma non firmati | Alla disponibilità di una chiave dell'owner, **creare una nuova baseline firmata**. I tag già pubblicati non vanno riscritti: chi li ha recuperati ne conserverebbe una versione divergente |
| DER-ICD-002 | §15.4 passo 1 — nessuna emissione canonica prima della ratifica | Tutti e tre i componenti emettono già le chiavi candidate di §2, per scelta propria e con deroga registrata nei rispettivi repository | Ratifica di §2 con nomi compatibili, oppure migrazione degli emittenti |

Finché DER-ICD-001 è attiva, la revisione esatta resta l'unico riferimento
autorevole: ogni change impact analysis **DEVE** citare il commit, non il solo tag.

---

## §17 Come si misura la conformità

Tre grandezze distinte, da non confondere:

| Grandezza | Definizione | Obbliga |
|---|---|---|
| **Conformità corrente** | rispetto delle sole sezioni **ratificate** del registro | sì |
| **Distanza dal traguardo** | scarto dalle sezioni ancora `proposta` | no |
| **Deroghe attive** | scostamenti dichiarati secondo §16, con condizione di rientro | vanno registrate |

Il registro in testa al documento dice quali sezioni sono ratificate. Nessun elenco altrove lo sostituisce.

---

## Appendice A — Dove sta lo stato di fatto

Lo stato di conformità **non** vive in questo documento. Le versioni precedenti
ne tenevano qui una fotografia scritta a mano, e invecchiava da sola: dichiarava
ancoraggi superati, conteggi sbagliati e un lavoro «da fare» che era già fatto.
Una tabella che nessun controllo può smentire diventa falsa senza che nessuno se
ne accorga.

Le fonti autorevoli, tutte leggibili da macchina e verificabili:

| Cosa | Dove |
|---|---|
| Revisioni su cui la qualifica va eseguita | `conformance/components.json`, `components[]` |
| Esito della qualifica di sistema | `conformance/components.json`, `system_qualification` |
| Evidenza di un'esecuzione | `conformance/evidence-<data>-roundtrip.json` |
| Stato di rilascio di un componente | i manifesti in `release/` del componente, secondo `PLENORA-CRITERI-RC.md` |
| Stato normativo di ogni sezione | il registro di ratifica in testa a questo documento |

Nessuna affermazione altrove sostituisce queste fonti. Un componente che si
ritiene conforme a una regola lo dimostra con l'esito della qualifica sulla
propria revisione, non con una riga in una tabella.

## Appendice B — Hazard di riferimento

Da `plenora-IO-tools/docs/assurance/TRACEABILITY.md`. Le regole di questo
documento controllano gli hazard indicati.

| Hazard | Descrizione | Regole |
|---|---|---|
| H-01 | Corruzione, perdita o reinterpretazione silenziosa dei dati | R2.2, R2.4, R3.2, R3.4, R5, R6.5, R9.3, R10.4 |
| H-02 | Sovrascrittura o pubblicazione parziale di un dataset | R11.3, R14 |
| H-03 | Esaurimento non controllato di memoria, CPU o storage | R7 |
| H-04 | Panic, comportamento indefinito o arresto del processo | R6 |
| H-05 | Dichiarazione di durabilità non realmente confermata | R14.3 |
| H-06 | CRS o ordine assi interpretato in modo errato | R4 |
| H-07 | Artefatto non riproducibile o dipendenza non controllata | R1, R12, R13 |
| H-08 | Difetto non rilevato dalla strategia di verifica | R12.4, §17 |
| H-09 | Regressione introdotta senza change impact analysis | R13.5, §16 |

---

## Appendice D — Glossario

**Componente** — uno dei tre workspace Plenora.

**Bordo** — componente che scambia dati con il mondo esterno: IO-tools verso i
formati file, database-tools verso i database. I bordi hanno vincoli non
negoziabili, imposti dai sistemi esterni.

**Centro** — il componente di trasformazione, data-tools. I suoi vincoli sono
scelte di design e quindi negoziabili.

**Confine** — il punto in cui un `RecordBatch` e il suo contratto passano da un
componente a un altro.

**Contratto** — l'insieme dello schema Arrow e dei metadati canonici §2 che
descrivono un flusso di dati.

**Fail-closed** — rifiutare l'operazione quando non se ne può garantire la
correttezza, invece di procedere in modo approssimato.

**Deroga** — dichiarazione esplicita che un componente non rispetta una regola,
con motivo e condizione di rientro (§16).

**CIA** — change impact analysis: l'analisi che accompagna ogni modifica secondo
il profilo di assurance.

**Baseline** — lo stato versionato e citabile di codice, dipendenze, toolchain e
documenti normativi a cui una CIA si riferisce.

---

## Appendice E — Matrice minima di verifica

Questa matrice definisce l'evidenza minima comune richiesta da R0. Non sostituisce
i piani di verifica dei componenti e non trasforma una regola `proposta` in una
regola vincolante.

Il corpus di `conformance/` scarica **in parte** le righe R2, R3, R4 e R5: copre
il trasporto e la propagazione delle chiavi attraverso i tre componenti, non il
fuzzing dei decoder né la matrice completa degli ordini d'asse. Una riga resta
scoperta finché la sua evidenza minima non è tutta prodotta: il corpus riduce il
lavoro residuo, non lo chiude.

| Regole | Metodo minimo | Evidenza minima |
|---|---|---|
| R0 | analisi di tracciabilità e revisione indipendente | matrice requisito–hazard–test senza collegamenti mancanti; autore e revisore identificati |
| R1 | analisi automatica dei manifest e build | versioni esatte coincidenti; `cargo ... --locked` riuscito sui tre workspace |
| R2 | test di contratto e property test | round-trip dei metadata; conflitto fra rappresentazioni; casi di lineage identity, derived e multi-source |
| R3 | test tabellari, property test e fuzzing dei decoder | sedici tipi, cinque dimensioni, quattro stati di dichiarazione; input non supportato e malformato |
| R4 | test tabellari e negativi | tre stati CRS, sei ordini d'asse, rappresentazioni discordanti ed EWKB SRID incoerente |
| R5 | test differenziali e sui limiti | perdita rifiutata o nel `LossReport`; confronti su estremi numerici e cast non rappresentabili |
| R6 | analisi statica, fuzzing, boundary test e audit | gate §6, corpus e seed riproducibili, overflow in release, elenco delle API panicking e relativa mitigazione |
| R7 | property test, test concorrenti e fault injection | nessuna allocazione prima del limite; lease restituiti; overflow rifiutato; limiti di espansione, decompressione, CPU e spill |
| R8 | analisi automatica del grafo e test d'API | nomi package unici, un solo tipo per concetto di confine, stabilità di `FieldId` attraverso le rinomine |
| R9 | test tabellari e fault injection | combinazioni dei quattro assi; commit perso, timeout per fase, effetto ignoto e decisione di retry senza inferenze dal messaggio |
| R10 | test di conformità delle capability | ogni capability dichiarata ha un test positivo; ogni assenza ha un test di rifiuto fail-closed |
| R11 | test concorrenti e temporali con clock controllato | `cancel()` idempotente, wake senza polling, deadline, motivo, propagazione padre–figlio e cancellazione durante I/O bloccante |
| R12 | ripetizione con scheduling e spill differenti | confronto semantico, d'ordine e byte-for-byte secondo il livello dichiarato; snapshot e collation registrati |
| R13 | build riproducibile e analisi delle dipendenze | toolchain esatta, lockfile invariato, assenza di caret, CIA associata a ogni variazione |
| R14 | fault injection in ogni fase di pubblicazione | no-clobber concorrente, crash prima/durante/dopo commit, durabilità verificata, classificazione `partial`/`unknown` e recovery provata |
| R15 | verifica crittografica e test d'integrazione | firma del tag valida, commit coincidente col lockfile, build `--locked`, API pubblica del crate conforme all'ICD |
| R16 | ispezione del registro delle deroghe | regola, hazard, motivo, owner, condizione di rientro e stato presenti per ogni deroga |
| R17 | generazione del report di conformità | risultato per ogni regola ratificata, commit e ambiente; nessun `✅` derivato dalla sola assenza di evidenza contraria |

Ogni esecuzione **DOVREBBE** produrre un artefatto machine-readable conservato
dalla CI. Un risultato scaduto perché riferito a una revisione precedente resta
storico, ma non dimostra la revisione corrente.

---

*Documento redatto come revisione tecnica. Lo stato normativo di
ogni sezione è quello, e soltanto quello, del registro di ratifica in testa al
documento: nessuna affermazione altrove sostituisce quel registro. Gli stati di
conformità in Appendice A sono rilevati per ispezione del codice, non per
esecuzione dei test, e sono ancorati alle revisioni dichiarate in Appendice A.
Ogni fotografia successiva deve dichiarare le proprie: conteggi e riferimenti a
numeri di riga non ancorati a un commit sono obsoleti nel momento in cui vengono
scritti, e non vanno estesi per inferenza ad altre revisioni.*
