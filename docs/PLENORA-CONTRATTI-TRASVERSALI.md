# Plenora — Contratti trasversali

**Documento normativo di interfaccia (ICD) · versione 2.0-rc1 · 27 luglio 2026**

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
> Stati: `proposta` (non vincolante: mai ratificata, oppure emendata dopo una
> sospensione e in attesa di nuova ratifica) · `ratificata` (vincolante) ·
> `sospesa` (ratificata, poi sospesa dall'owner a seguito di un rilievo
> bloccante accolto: **non** vincolante finché l'emendamento non la sostituisce)
> · `superata` (rimpiazzata da una versione ratificata successiva).
>
> Al 27 luglio nessuna sezione è `sospesa`: la 2.0 ha emendato tutte quelle che
> lo erano, riportandole a `proposta` in attesa di ratifica.
>
> **Clausola di chiusura.** Ogni regola o sezione non elencata in questa tabella
> ha stato `proposta`. La tabella è esaustiva per costruzione: se una regola
> compare nel corpo ma non qui, non è vincolante.
>
> **Effetto della 2.0.** Gli emendamenti chiudono i rilievi che avevano portato
> alla sospensione, ma **entrano come `proposta`**: una sezione emendata non
> torna vincolante da sé. La ratifica degli emendamenti è l'atto che manca.
> Le undici sezioni ratificate il 27 luglio restano tali sul testo che coprivano;
> le clausole aggiunte dalla 2.0 dentro quelle sezioni sono elencate a parte.
>
> | Sezione | Oggetto | Stato | Dal | Emendamento previsto | Posizioni dei team |
> |---|---|---|---|---|---|
> | §1 R1 | Versione Arrow unica e pinnata | **ratificata** | 27 lug | — | conforme in tutti e tre |
> | §2 | Chiavi metadata canoniche, versione del protocollo (R2.5), deroga Arrow/GeoArrow (R2.6), lineage (R2.4) | proposta *(emendata 2.0)* | — | — | rilievi db chiusi; da ratificare |
> | §3.1 | Sedici tipi geometrici, forma `linestring` | **ratificata** | 27 lug | — | IO ✔ · data ✔ · db ✔ |
> | §3.2 | Rifiuto esplicito dei tipi non supportati | **ratificata** | 27 lug | — | data ✔ |
> | §3.3 | Cinque dimensioni rappresentabili e propagabili | **ratificata** | 27 lug | — | ambito: rappresentare e propagare, **non** elaborare (vedi clausola) |
> | §3.4 | `unknown` non degradabile; tre stati di dichiarazione dei tipi (R3.4.1) | proposta *(emendata 2.0)* | — | — | rilievo db chiuso; da ratificare |
> | §3.5 | Encoding come enumerazione chiusa | **ratificata** | 27 lug | — | db: `String` da convertire |
> | §4.1–§4.4 | CRS a tre stati, axis order non canonicalizzato, definizione preservata, nessun default | **ratificata** | 27 lug | — | IO ✔ · data ✔ · db ⚠ (emendamenti su formato della definizione e precedenza) |
> | §4.5 | Riproiezione decisa dal centro, eseguibile dal bordo come pushdown capability-gated | proposta *(emendata 2.0)* | — | — | rilievo db chiuso; da ratificare |
> | §5 R5 | Perdita di informazione mai silenziosa | **ratificata** | 27 lug | — | data ✔ (R5.3 implementata) |
> | §6 R6 | Nessun panic nei crate `lib` | **ratificata** | 27 lug | — | IO ✔ · data ✔ (`07f6823`) · db ✘ |
> | §7 R7 | Limiti pre-allocazione; budget che attraversa la catena con lease (R7.5–R7.7) | proposta *(emendata 2.0)* | — | — | rilievo db chiuso; da ratificare |
> | §8 R8 | Identità di crate e colonne | **ratificata** | 27 lug | — | R8.1 e R8.4 violate da IO e data (`plenora-core`, `PlenoraError`) |
> | §9 | Errore a quattro assi: causa, fase, effetto remoto (R9.6), disposizione di ritentativo (R9.7) | proposta *(emendata 2.0)* | — | — | rilievi db chiusi; da ratificare |
> | §10 R10 | Capability dichiarative interrogabili | proposta | — | — | forma definita in §15.3; da ratificare |
> | §11.1–§11.4 | Cancellazione cooperativa; garanzia sui residui condizionata alla piattaforma (R11.3) | proposta *(emendata 2.0)* | — | — | rilievo db chiuso; da ratificare |
> | §11.5 | `CancellationToken` con attesa asincrona, deadline, motivo e token figli (R11.6–R11.8) | proposta *(emendata 2.0)* | — | — | rilievo db chiuso; da ratificare |
> | §12 R12 | Determinismo su quattro livelli; sorgenti remote e collation esclusi (R12.5–R12.6) | proposta *(emendata 2.0)* | — | — | rilievo db chiuso; data ✔ (R12.4) |
> | §13 R13 | Toolchain e baseline | **ratificata** | 27 lug | — | data ✔ (`a1f4130`) · IO: toolchain da fissare |
> | §14 R14 | Esiti di scrittura; ripristino dichiarabile solo se verificato (R14.4) | proposta *(emendata 2.0)* | — | — | rilievo db chiuso; da ratificare |
> | §15.1 | Repository autonomo `plenora-contracts` come fonte autorevole, e suo nome | **ratificata** | 27 lug | — | IO ✔ · data ✔ · db ✔ |
> | §4.3.1–§4.3.3 | *(nuove 2.0, dentro una sezione ratificata)* formato della definizione CRS, precedenza fra rappresentazioni, coerenza con l'SRID EWKB, ordini d'asse estesi | proposta | — | — | rilievo db chiuso; da ratificare |
> | §6 R6.6–R6.7 | *(nuove 2.0, dentro una sezione ratificata)* il gate Clippy è minimo e non dimostra R6.1: servono fuzzing, boundary test, overflow-checks e audit delle API panicking | proposta | — | — | rilievo db chiuso; da ratificare |
> | §15.2 | Distribuzione: tag firmato **e** revisione nel lockfile, citati entrambi nelle CIA | proposta *(emendata 2.0)* | — | — | rilievo db chiuso; da ratificare |
> | §15.3 | Contenuto e API del crate, ora completo su sei aree | proposta *(emendata 2.0)* | — | — | rilievo db chiuso; da ratificare |
>
> La colonna **Emendamento previsto** indica dove il rilievo sarà risolto: non
> significa che la regola sia già stata sostituita. Una sezione diventa `superata`
> soltanto quando la versione che la sostituisce è a sua volta ratificata.
>
> **Effetto pratico degli stati.** Una sezione `sospesa` non fonda nuovo
> lavoro: chi ha già iniziato non disfa, chi non ha iniziato attende la 2.0. Una
> sezione `proposta` non è vincolante per nessuno — il che non impedisce a un
> componente di applicarla per propria scelta o per una regola interna.
>
> Restano in vigore, indipendentemente da questa tabella, le regole che ciascun
> componente si è dato internamente: la correzione di
> `plenora-io-core/src/driver.rs:347` è dovuta per PLN-ASR-007 e H-01 **a
> prescindere** dallo stato di §3.4 (vedi §16-bis).
>
> **Cronologia.** §9 e §11 recepiscono i rilievi del team IO-tools; §5, §9 e §12
> la fotografia del team data-tools; l'Appendice A §R13.3 corregge un dato errato
> della 1.0. La 2.0 emenda le sei sezioni che erano `sospesa` e le sei `proposta`
> con rilievi aperti: nessuna sezione risulta più sospesa, tutte attendono
> ratifica.

Governa i confini fra i tre componenti Plenora sviluppati separatamente. Le regole
qui contenute prevalgono sulla documentazione locale dei singoli repository.

| Componente | Ruolo nella catena | Repository |
|---|---|---|
| **plenora-IO-tools** | Bordo verso i formati file | `plenora-IO-tools` |
| **plenora-data-tools** | Motore di trasformazione (centro) | `plenora-data-tools` |
| **plenora-database-tools** | Bordo verso i database | `plenora-database-tools` |

---

## Indice

- §0 Come si usa questo documento
- §1 R1 — Versione Arrow
- §2 R2 — Chiavi dei metadati Arrow
- §3 R3 — Modello geometrico
- §4 R4 — Sistema di riferimento (CRS)
- §5 R5 — Perdita di informazione
- §6 R6 — Fallimento invece di panic
- §7 R7 — Limiti di risorsa
- §8 R8 — Identità dei crate e delle colonne
- §9 R9 — Modello di errore attraverso i confini
- §10 R10 — Capability e negoziazione
- §11 R11 — Cancellazione
- §12 R12 — Determinismo e riproducibilità dei risultati
- §13 R13 — Toolchain e baseline
- §14 R14 — Esiti di scrittura e pubblicazione
- §15 Crate condiviso e migrazione (§15.1 autorità · §15.2 distribuzione · §15.3 contenuto · §15.4 piano)
- §16 Deroghe e modifiche
- §17 Definizione di componente conforme
- Appendice A — Riepilogo di conformità
- Appendice B — Hazard di riferimento
- Appendice C — Tabelle di rinomina
- Appendice D — Glossario

---

## §0 Come si usa questo documento

**Stato normativo.** Le regole usano `DEVE` / `NON DEVE` / `DOVREBBE` con il
significato consueto: `DEVE` è vincolante e la sua violazione blocca il merge;
`DOVREBBE` ammette deroga motivata secondo §16.

**Autorità.** In caso di conflitto fra questo documento e la documentazione di un
singolo repository (`Architetture.md`, ADR, `IMPLEMENTATION_STATUS.md`), prevale
questo documento. Gli ADR locali possono restringere una regola, mai allargarla.

**Verificabilità.** Ogni regola dichiara come si verifica. Una regola che non si
può verificare meccanicamente è marcata `[ispezione]` e richiede evidenza scritta
nella change impact analysis.

**Aggancio all'assurance.** Le regole sono collegate agli hazard definiti in
`plenora-IO-tools/docs/assurance/TRACEABILITY.md` (H-01…H-09). Un componente che
viola una regola ha un hazard non controllato, non solo un difetto di stile.

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

**Stato oggi: conforme in tutti e tre.**

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
| `plenora.geometry.types` | lista separata da `,` di tipi canonici (§3) | no |
| `plenora.geometry.srid` | intero decimale senza segno | no |
| `plenora.geometry.crs_id` | identificatore d'autorità, es. `EPSG:4326` | no |
| `plenora.geometry.crs_resolution` | `resolved` \| `declared_unresolved` \| `missing` | sì |
| `plenora.geometry.crs_definition` | WKT o PROJJSON, testuale | no |
| `plenora.geometry.axis_order` | `lon_lat` \| `lat_lon` \| `easting_northing` \| `unknown` | sì se `crs_id` presente |
| `plenora.geometry.spatial_semantics` | `geometry` \| `geography` | no |
| `plenora.geometry.precision` | `float64` \| `float32` \| `native` | no |
| `plenora.field_id` | intero decimale senza segno | no |
| `plenora.contract.version` | intero decimale; oggi `1`. **Vive in `Schema::metadata`**, non nel campo | sì se sono presenti chiavi canoniche |
| `plenora.geometry.crs_definition_format` | `wkt` \| `wkt2` \| `projjson` | sì se `crs_definition` è presente |
| `plenora.geometry.types_declaration` | `exact` \| `mixed` \| `unresolved` | sì per colonne geometriche; indipendente dalla presenza di `types` |

**Perché R2.2.** Un blob unico è opaco: un componente che non sa deserializzarlo
perde tutte le proprietà insieme, e la perdita è silenziosa (H-01).

**Perché R2.4.** Il componente centrale non conosce le estensioni dei due bordi.
Se le elimina, un round-trip file → trasformazione → file perde i metadati nativi
che il driver aveva preservato con cura.

**Verifica.** `grep -rhoE '"plenora\.[a-z_.]+"' crates/ | sort -u` confrontato con
la tabella; test di round-trip dei metadati attraverso il componente centrale.

**Stato oggi: nessuno dei tre conforme.** Vedi Appendice C per le rinomine.

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
> `types_declaration` è **indipendente** dalla presenza di `plenora.geometry.types`:
> `mixed` e `unresolved` sono dichiarazioni sensate proprio quando l'elenco dei
> tipi non c'è. Solo `exact` richiede che l'elenco sia presente. L'assenza di
> entrambe le chiavi significa «proprietà non dichiarata», che è un quarto stato.
> Un componente **NON DEVE** convertire `mixed` in `unresolved` né viceversa.
>
> **R3.5** L'encoding canonico è `wkb` o `ewkb`, come enumerazione chiusa. **NON
> DEVE** essere modellato come stringa libera.

**Perché la forma senza separatore (R3.1).** I valori serializzati vengono
confrontati con i tipi dichiarati dai sistemi esterni — PostGIS, GeoPackage, OGC
WKT — che usano tutti `LINESTRING`, `MULTIPOLYGON`. La forma `line_string`
richiederebbe una traduzione a ogni confine, e ogni traduzione è un punto in cui
si perde informazione.

**Perché R3.3 è la regola più costosa.** Oggi `data-tools` ammette solo `xy`. La
regola non impone di *calcolare* in 3D: impone di non distruggere e di non
descrivere in modo errato ciò che non si elabora.

Il comportamento attuale di data-tools va descritto con precisione, perché non è
una perdita silenziosa e la versione 1.0 di questo documento lo diceva a torto:

1. **Operazioni geometriche su Z/M: rifiuto esplicito.** `geometry_from_wkb`
   respinge con `Unsupported` ogni WKB che porti Z, M o SRID — «non preservabili
   nel protocollo 2D» — e c'è un test dedicato anche al caso annidato in una
   `GeometryCollection`. È fail-closed, quindi conforme a R5.1 e R3.2.
2. **Operazioni tabellari su dati Z/M: i byte transitano.** I kernel tabellari
   non decodificano la colonna geometrica, che resta un buffer opaco. Un filtro,
   un join o un ordinamento su attributi non attivano il rifiuto.
3. **Ma il contratto emesso dichiara comunque `xy`**, perché è l'unica variante
   rappresentabile.

Il punto 3 è il difetto reale, ed è di natura diversa da quella ipotizzata: non
è perdita di dati, è un **metadato che contraddice i byte che accompagna**. Un
consumatore a valle — per esempio database-tools, che decide su
`plenora.geometry.dimensions` come dichiarare la colonna PostGIS — riceve dati
XYZM etichettati come XY. È H-01 nella forma «reinterpretazione», non in quella
«perdita».

**Verifica.** `[ispezione]` sulle definizioni dei tipi; test di round-trip
end-to-end XYZM attraverso i tre componenti; grep di assegnazioni che portano a
`Xy` un valore letto dai metadati.

**Stato oggi:**

| | Tipi | Dimensioni | Encoding |
|---|---|---|---|
| IO-tools | 7, `snake_case` | 5 ✅ | enum ✅ |
| database-tools | 16 ✅, forma ✅ | 4 (manca `unknown`) | `String` ❌ |
| data-tools | assenti ❌ | 1 (`xy`) ❌ | assente ❌ |

**Violazione nota di R3.4** — `plenora-io-core/src/driver.rs:347`. Segnalata dal
team IO-tools e confermata:

```rust
read_geometry_contract_metadata(field, &mut geometry);
if geometry.dimensions == CoordinateDimensions::Unknown {
    geometry.dimensions = CoordinateDimensions::Xy;
}
```

L'intento documentato è il default per i contratti v1 privi di metadati
geometrici, ed è legittimo. Il difetto è la posizione: la conversione avviene
**dopo** la lettura dei metadati, quindi sovrascrive anche un `unknown`
dichiarato esplicitamente. La correzione non è rimuovere il default ma spostarlo
nel ramo in cui i metadati sono assenti, così che i due casi — «nessuna
informazione, si applica il default storico» e «informazione presente, dice
`unknown`» — restino distinti.

Questa correzione **non dipende dalla ratifica del presente documento**: è già
dovuta per PLN-ASR-007 e H-01 nel profilo di assurance di IO-tools.

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

**Perché.** L'inversione lat/lon è il fallimento geospaziale più costoso e più
silenzioso che esista: produce coordinate plausibili in un punto sbagliato del
pianeta, senza alcun errore (H-06).

**Verifica.** `[ispezione]` più matrice di test axis-order per componente.

**Stato oggi:** IO-tools conforme nel modello; `driver-shp` proietta però
`crs.id.unwrap_or("unknown")` nei metadati, collassando *assente* e *irrisolto*
(violazione R4.1 nel dato che esce). database-tools rappresenta il CRS come
`srid: Option<u32>` + `crs: Option<String>`: non può esprimere né i tre stati né
l'axis order. data-tools ha `ResolvedCrs` allineato al modello.

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

**Stato oggi:** IO-tools ha 95 `unwrap_or*` nei crate `lib`, censiti ma non ancora classificati uno per uno.
data-tools ha corretto R5.3 con `compare_cells_typed`, committato in `14a0a29`;
resta il censimento di `unwrap_or*` e dei cast troncanti (R5.4), che è cosa
distinta dal gate anti-panic e non viene intercettata da esso.
database-tools non ha un report di perdita uniforme.

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

**Stato oggi:** IO-tools **0** occorrenze, gate attivo. data-tools **~121** nei
crate libreria, nessun gate. database-tools **26**, nessuna CI.

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

**Stato oggi:** IO-tools dichiara R7 «Parziale» (PLN-ASR-004). database-tools
applica profondità e nodi all'AST tramite `validate_query_operation`, iterativa e
quindi conforme a R7.3. data-tools valida il framing IPC prima di delegare ad
arrow-rs.

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

**Stato oggi: violazioni aperte.** `plenora-IO-tools/crates/plenora-core` e
`plenora-data-tools/crates/plenora-core` sono due pacchetti distinti con lo stesso
nome (R8.1), e definiscono entrambi un `PlenoraError` con varianti diverse (R8.4).
Il crate condiviso previsto da R8.3 non esiste.

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

### Mappatura dai modelli attuali

| Oggi | Categoria canonica |
|---|---|
| IO `Contract`, data `Contract` | `InvalidPlan` |
| IO `Schema`, data `Schema` | `Schema` |
| IO `Crs`, data `Crs` | `Crs` |
| IO `Wkb` | `DataMapping` |
| IO `LimitExceeded` | `ResourceLimit` |
| IO `OutputExists` | `Conflict` |
| IO/data `Unsupported`, data `UnsupportedPublishTarget` | `Unsupported` |
| IO/data `Io` | `Io` |
| IO/data `Json`, data `Arrow` | `DataMapping` |
| data `Step` | `Execution` |
| data `Cancelled` | `Cancelled` |

**Stato oggi: tre modelli distinti e incompatibili.**

| Componente | Tipo | Categoria | Fase | Ritentabilità | Esito ignoto |
|---|---|---|---|---|---|
| IO-tools | `PlenoraError` enum | implicita nella variante | ❌ | ❌ | solo nel publish |
| data-tools | `PlenoraError` enum + `ErrorCategory` (11) | ✅ | ❌ | ✅ `retryable()` | ❌ |
| database-tools | `DatabaseError` struct | ✅ (15) | ✅ (10) | ✅ | ✅ |

Le categorie di data-tools e database-tools condividono oggi soltanto
`Unsupported` e `Cancelled`.

data-tools soddisfa R9.2 dalla milestone M1: `PlenoraError::retryable()` è una
funzione esplicita con test dedicato, e `execution_id` è portato dalle varianti
`Step` e `Cancelled`. Restano da aggiungere la fase (R9.1) e l'esito ignoto
(R9.3).

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

**Stato oggi:** IO-tools ha `FormatWriteCapabilities` e `CapabilityReason`
tipizzato, con validatore statico prima della creazione. database-tools ha
`ProviderCapabilities` (read, write, transaction, spatial, limits). I due modelli
sono paralleli ma non condividono nulla. data-tools, come componente centrale,
non espone capability: **DOVREBBE** dichiarare almeno quali tipi e dimensioni
geometriche è in grado di propagare, per rendere verificabile R3.3.

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
> `Sync` e `Clone`; l'osservazione **DEVE** costare quanto una lettura atomica,
> perché va controllata fra un batch e il successivo.
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
> cancelled() -> Future           attesa asincrona, si risolve alla cancellazione
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
> **NON DEVE** dipendere né da `futures-core` né da un runtime.
>
> **R11.10** *(nuova 2.0)* La deadline è **dichiarativa**: il token la espone e
> `is_cancelled()` la valuta al momento della chiamata. Il risveglio *automatico*
> alla scadenza richiede un timer, che il crate non ha e non deve avere: è il
> chiamante a combinare `cancelled()` con il proprio meccanismo temporale, oppure
> a iniettare un clock. Un token che promettesse di svegliarsi da solo starebbe
> nascondendo una dipendenza da runtime.

**Perché un token concreto e non un trait (R11.5).** Un trait per componente è
esattamente la situazione attuale: data-tools e database-tools ne hanno uno
ciascuno e non sono interoperabili, quindi un'operazione che attraversa i tre
richiede due adattatori. L'obiettivo del contratto è che un token creato dalla CLI
attraversi i tre componenti invariato. La flessibilità del trait serve a chi deve
astrarre *implementazioni* diverse; qui l'implementazione è una sola e la
flessibilità che serve davvero — collegare una sorgente esterna di segnale — la
dà R11.6.

**Stato oggi: due modelli e un'assenza.** data-tools ha un modulo `cancellation`
con token cooperativo; database-tools ha un trait `Cancellation` e sa cancellare
il backend remoto. IO-tools non ha un modello di cancellazione, e lo dichiara
apertamente in `IMPLEMENTATION_STATUS.md` («restano da uniformare cancellazione e
streaming dei parser che materializzano»). Un'operazione lunga che parte da un
driver non è oggi interrompibile.

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

**Stato oggi:** normato solo in data-tools, che ha test di determinismo canonico
IPC, catalogo canonico e — da `14a0a29` — l'oracolo memoria-contro-spill per
tutti e tre gli operatori spillabili (`spilled_sort_matches_in_memory`,
`spilled_distinct_matches_in_memory`, `spilled_aggregate_matches_in_memory`) più
un property test sul contratto d'insieme. R12.4 è quindi soddisfatta, non
parzialmente ma per l'intera superficie di spill. Gli altri due componenti non
hanno test equivalenti: IO-tools e database-tools non verificano oggi che
percorso parallelo e sequenziale coincidano.

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

**Stato oggi:** tutti e tre dichiarano `edition = 2021` e `rust-version = 1.92`,
quindi R13.4 è soddisfatta. Ma soltanto **database-tools** ha un
`rust-toolchain.toml` che fissa il canale a `1.92.0`: gli altri due compilano con
lo stable corrente, in violazione di R13.1.

Su R13.3 la versione 1.0 di questo documento riportava «due dipendenze caret» in
IO-tools: la fotografia era errata, perché contava solo
`plenora-io-core/Cargo.toml` senza il manifest di workspace. Il conteggio reale è
il seguente, e la segnalazione del team IO-tools è corretta:

| Componente | Dipendenze non pinnate |
|---|---|
| IO-tools | `geo-types "0.7"`, `shapefile "0.6"`, `kml "0.8"`, `calamine "0.26"`, `rust_xlsxwriter "0.79"`, `gdal "0.17"`, `serde "1"`, `serde_json "1"`, `sha2 "0.10"`, `tempfile "3"` (workspace) · `rustix "1"`, `atomicwrites "0.4.4"` (crate, anche fuori da `[workspace.dependencies]`) · `libc "0.2"` |
| data-tools | nessuna |
| database-tools | nessuna |

Le due dichiarate nel crate anziché nel workspace violano R13.3 due volte: per il
caret e per la collocazione. Le altre solo per il caret. Anche questa correzione
**non dipende dalla ratifica del presente documento**: la regola 6 del profilo
`AERONAUTICAL_PROFILE.md` di IO-tools chiede già change impact analysis per ogni
variazione di dipendenza, e un caret la rende impossibile.

---

## §14 R14 — Esiti di scrittura e pubblicazione

> **R14.1** Un output **NON DEVE** sovrascrivere una destinazione esistente, salvo
> richiesta esplicita del chiamante. Il controllo **DEVE** essere atomico, non
> una verifica seguita da una scrittura.
>
> **R14.2** Un output **DEVE** diventare visibile solo quando è completo. Nessun
> consumatore deve poter osservare uno stato intermedio.
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

**Stato oggi:** IO-tools è il riferimento — rename no-clobber autorevole,
sequenza durable con esito tipizzato, staging ripulito con guardia RAII — ma solo
su Linux e Windows: sulle altre piattaforme `publish_dir_atomic` fallisce sempre,
e i test sono gated, quindi la CI non lo rileva. database-tools soddisfa R14.3 e
R14.4 in transazione, con `OutcomeUnknown` sul commit incerto. data-tools ha un
`TempStore` con scavenging degli orfani.

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

**Perché non `docs/` di uno dei tre.** Un contratto che vincola tre team non può
essere ospitato da uno di essi: chi lo ospita ne controlla di fatto il merge, e
§15.4 assegna già a IO-tools il ruolo di riferimento per i tipi. Concentrare
anche la sede del documento sbilancerebbe la governance.

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
| Vincoli di dipendenza | `serde`, `arrow-schema` e `futures-core` per `cancelled()`. **Nessun runtime asincrono.** Nessun `unsafe`, nessuna primitiva di panic |

**Stato.** L'elenco è ora completo: la 2.0 recepisce il rilievo che aveva portato
alla sospensione. Il crate può essere creato quando §15.3 torna `ratificata`.

### §15.4 — Piano di migrazione

La convergenza avviene in quattro passi, in quest'ordine. Ogni passo è
verificabile e non richiede il successivo per essere utile.

**Passo 1 — Chiavi metadata (§2).** Non dipende da nessun refactoring: sono
costanti stringa. Ogni componente allinea i propri nomi alla tabella §2, con un
periodo di doppia lettura (accettare vecchio e nuovo, emettere solo il vecchio)
se serve compatibilità all'indietro. Vedi Appendice C. Finché l'emendamento di §2
non è ratificato, è consentita la sola doppia lettura, non l'emissione canonica.

**Passo 2 — Estrazione a semantica zero.** Nasce il crate condiviso, come pura
estrazione dei tipi di confine oggi in `plenora-IO-tools/crates/plenora-core`.
IO-tools ci dipende e re-esporta; nessun cambiamento di comportamento, nessuno
stato di tracciabilità si muove. Subordinato a §15.3.

**Passo 3 — Adozione.** data-tools e database-tools adottano il crate condiviso,
uno per volta, ciascuno con la propria change impact analysis.

**Passo 4 — Allargamento del modello.** Solo quando i tre dipendono dallo stesso
crate si estende il modello geometrico (curve, XYZM ovunque) con una CIA che
copre i tre insieme.

**Perché IO-tools è il punto di partenza del passo 2.** Non per maturità, ma
perché i suoi vincoli non sono negoziabili: i formati file esistono e dettano
cosa deve essere rappresentabile. Gli stati `unknown`, `declared_unresolved` e
l'axis order non canonicalizzato sono scoperte fatte contro dati reali, non
scelte di design che si possano rifare a tavolino. I sedici tipi geometrici di
database-tools, al contrario, si aggiungono in un pomeriggio. L'eccezione è il
modello d'errore (§9), dove il punto di partenza è database-tools.

---

## §16 Deroghe e modifiche

**Deroga.** Un componente che non può rispettare una regola **DEVE** dichiararlo
esplicitamente: regola, motivo, impatto sugli hazard, condizione di rientro. Una
deroga dichiarata è un gap noto; una regola aggirata in silenzio è un difetto.

**Registro.** Le deroghe attive **DEVONO** essere elencate in un punto solo per
componente, così che si possano contare. Una deroga senza condizione di rientro
è permanente: va scritto.

**Modifica del documento.** Una proposta di modifica **DEVE** indicare: regole
toccate, impatto sui tre componenti, piano di migrazione, retrocompatibilità. La
modifica entra in vigore quando i tre team l'hanno recepita — fino ad allora la
versione precedente resta vincolante.

**Versionamento.** Questo documento **DEVE** essere versionato in un repository,
non distribuito come file sciolto: senza storia non esiste baseline, i team non
sanno a quale versione si stanno conformando e nessuna change impact analysis è
possibile. La versione è dichiarata in testa al documento e citata nelle CIA.

**Proprietà.** Questo documento **DEVE** avere un owner nominato. Un contratto
trasversale senza proprietario diventa tre interpretazioni divergenti: è già
successo con i due `plenora-core`, ricopiati consapevolmente e poi lasciati
derivare fino a definire due `PlenoraError` incompatibili.

---

## §16-bis Lavoro non subordinato alla ratifica

La ratifica è necessaria per tutto ciò che tocca **tipi condivisi, nomi di chiavi
metadata e firme pubbliche**: cambiarli prima significa produrre un terzo modello
da rifare. Non è invece necessaria per ciò che ciascun componente già deve alle
proprie regole interne, oggi in vigore.

**Eseguibile subito, senza attendere:**

| Intervento | Perché non dipende da questo documento |
|---|---|
| Correzione di `driver.rs:347` (`unknown` → `xy`) | Violazione di PLN-ASR-007 e H-01, già ratificati in `AERONAUTICAL_PROFILE.md` |
| Pin esatto delle 13 dipendenze caret | Regola 6 del profilo: un caret rende impossibile la CIA che il profilo richiede |
| `rust-toolchain.toml` in IO-tools e data-tools | PLN-ASR-010 è già dichiarato «Parziale» per questo motivo |
| Censimento dei 95 `unwrap_or*` nei crate `lib` | H-01: il gate anti-panic non li intercetta, sono l'altra metà della stessa regola |
| Gate anti-panic `--lib` su data-tools e database-tools | Replica di un gate già in produzione, nessuna decisione di contratto |
| Doppia **lettura** delle chiavi metadata (accettare canoniche e legacy, emettere solo legacy) | Retrocompatibile e reversibile; dimezza il lavoro del passo 1 senza anticiparne le scelte |

**Subordinato al registro:** rinomina delle chiavi in emissione (§2), enumerazioni
d'errore condivise (§9), token di cancellazione comune (§11.5), contenuto del
crate (§15.3), budget condiviso (§7), determinismo dichiarato (§12), esiti di
scrittura (§14). Tutte emendate dalla 2.0 e in attesa di ratifica.

La forma dei valori dei tipi geometrici (§3.1) e il modello CRS (§4.1–§4.4) sono
invece **ratificati**: si possono adottare subito. Anche l'istituzione del
repository `plenora-contracts` (§15.1) è ratificata; restano `proposta`, non
ancora ratificate, la sola
distribuzione (§15.2) e il contenuto (§15.3).

---

## §17 Definizione di componente conforme

La conformità si misura su **tre grandezze distinte**, che non vanno confuse:

| Grandezza | Definizione | Vincolante |
|---|---|---|
| **Conformità corrente** | Rispetto delle sole sezioni `ratificata` nel registro al momento della verifica: oggi §1, §3.1, §3.2, §3.3, §3.5, §4.1–§4.4, §5, §6, §8, §13, §15.1 | sì |
| **Gap verso il traguardo** | Distanza dall'elenco completo qui sotto, che include sezioni `proposta` | no |
| **Deroghe attive** | Scostamenti dichiarati secondo §16, con motivo e condizione di rientro | registrate |

L'elenco che segue è il **traguardo completo**, non il criterio corrente, e la
sua versione definitiva dipende dagli emendamenti 2.0. Le voci che riguardano
sezioni non ratificate sono fotografia, non obbligo:

1. Arrow pinnato alla versione di baseline (R1).
2. Emette e accetta le chiavi canoniche, dichiara `plenora.contract.version`, e
   propaga le chiavi non interpretate **secondo la lineage del campo**: copia per
   le trasformazioni identity-preserving, ricostruzione per i campi derivati,
   errore sui conflitti (R2.4–R2.7).
3. Rappresenta e propaga le cinque dimensioni e i sedici tipi, distingue `exact`
   da `mixed` e `unresolved`, rifiuta esplicitamente ciò che non supporta (R3).
4. Distingue i tre stati del CRS, dichiara il formato della definizione, rispetta
   la precedenza fra rappresentazioni e la coerenza con l'SRID EWKB (R4).
5. Non perde dati in silenzio: fail-closed o report esplicito (R5).
6. Gate anti-panic attivo sui `--lib` con zero occorrenze, **più** l'evidenza
   complementare che il gate non fornisce: fuzzing, boundary test,
   `overflow-checks`, audit delle API panicking (R6.6–R6.7).
7. Applica limiti prima dell'allocazione e **cede** il budget lungo la catena
   invece di replicarlo, con aritmetica controllata (R7.5–R7.7).
8. Nessuna collisione di nomi; dipende dal crate condiviso (R8).
9. Errori a **quattro assi**: causa, fase, effetto remoto, disposizione di
   ritentativo (R9.1, R9.6–R9.8).
10. Capability dichiarative interrogabili prima dell'esecuzione (R10).
11. Cancellazione cooperativa; nessun residuo **dove la piattaforma lo consente**,
    altrimenti effetto dichiarato e recovery disponibile (R11.3, R11.7–R11.10).
12. Determinismo **dichiarato sul livello che si garantisce** — semantico,
    dell'ordine, byte-for-byte o non ordinato — con le esclusioni note (R12).
13. Toolchain fissata, `--locked` in CI, dipendenze pinnate (R13).
14. Output atomico dove la piattaforma lo consente, no-clobber, durabilità ed
    effetto dichiarati solo se verificati (R14.3–R14.5).

**Rispetto al traguardo completo, nessuno dei tre componenti è oggi conforme.**
Sulla conformità corrente — undici sezioni ratificate al 27 luglio — la
verifica non è ancora stata eseguita da nessun team. Il più vicino è
IO-tools (R1, R3.3, R6, R14 su Linux, Windows e macOS); il più distante è database-tools,
che non ha CI e quindi non può dimostrare alcuna regola in modo automatico.

---

## Appendice A — Riepilogo di conformità

Rilevato per ispezione del codice al 27 luglio 2026. `—` = nozione non modellata.

| Regola | IO-tools | data-tools | database-tools |
|---|---|---|---|
| R1 Arrow pinnato `=59.1.0` | ✅ | ✅ | ✅ |
| R2 Chiavi canoniche | parziale | ❌ blob | ❌ namespace |
| R3.1 Tipi geometrici | 7/16 | — | 16/16, forma ✅ |
| R3.3 Dimensioni propagabili | ✅ 5/5 | ❌ solo `xy` | 4/5 |
| R3.4 `unknown` non degradato | ❌ `driver.rs:347` | n/a | n/a |
| R3.5 Encoding come enum | ✅ | — | ❌ `String` |
| R4 Modello CRS | ✅ (shp corretto in `8bb65dd`) | ✅ | ❌ piatto |
| R5 Perdita non silenziosa | ⚠ 95 `unwrap_or*` censiti | ✅ R5.3, censimento aperto | parziale |
| R6 Nessun panic nei `lib` | ✅ 0, gate attivo | ✅ 0, gate attivo (`07f6823`) | ❌ 26, nessuna CI |
| R7 Limiti pre-allocazione | parziale | parziale | ✅ AST |
| R8.1 Nomi crate unici | ❌ collisione | ❌ collisione | ✅ |
| R8.3 Crate condiviso | ❌ non esiste | ❌ | ❌ |
| R8.4 Tipi omonimi | ❌ `PlenoraError` | ❌ `PlenoraError` | ✅ |
| R9 Modello d'errore (2.0) | ❌ no fase, effetto, disposizione | ⚠ ha categoria e `retryable()`; mancano fase ed effetto | ⚠ base del modello, ma senza `RemoteEffect` né `RetryDisposition` |
| R10 Capability dichiarative | ✅ | ❌ assenti | ✅ |
| R11 Cancellazione (2.0) | ❌ assente | ⚠ token interno: conforme R11.1–R11.4, non al token condiviso | ⚠ trait proprio; senza deadline, motivo e token figli |
| R12 Determinismo | ❌ non testato | ✅ | ❌ non testato |
| R13.1 Toolchain fissata | ❌ stable | ✅ `a1f4130` | ✅ 1.92.0 |
| R13.3 Dipendenze pinnate | ❌ 8 caret (rustix e atomicwrites pinnate) | ✅ | ✅ |
| R14 Output atomico | ✅ Linux/Win/macOS (`target_vendor = "apple"`) | n/a | ✅ transazione |

---

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

## Appendice C — Tabelle di rinomina

Migrazione delle chiavi metadata al namespace canonico (§2, passo 1 di §15).

### plenora-IO-tools

| Attuale | Canonica | Nota |
|---|---|---|
| `plenora.geometry.dimensions` | invariata | ✅ |
| `plenora.geometry.srid` | invariata | ✅ |
| `plenora.geometry.encoding` | invariata | ✅ |
| `plenora.geometry.types` | invariata | valori da riformattare (R3.1) |
| `plenora.geometry.spatial_semantics` | invariata | ✅ |
| `plenora.geometry.precision` | invariata | ✅ |
| `plenora.geometry.native.*` | `plenora.<formato>.*` | sotto-namespace per formato (R2.3) |
| `plenora.filegdb.*` | invariata | ✅ conforme a R2.3 |
| — | `plenora.geometry.crs_id` | da aggiungere |
| — | `plenora.geometry.crs_resolution` | da aggiungere |
| — | `plenora.geometry.crs_definition` | da aggiungere |
| — | `plenora.geometry.axis_order` | da aggiungere |

### plenora-database-tools

| Attuale | Canonica |
|---|---|
| `plenora.dimensions` | `plenora.geometry.dimensions` |
| `plenora.srid` | `plenora.geometry.srid` |
| `plenora.geometry_type` | `plenora.geometry.types` |
| `plenora.spatial_semantics` | `plenora.geometry.spatial_semantics` |
| `plenora.native_type` | `plenora.postgres.native_type` |
| `plenora.native_declaration` | `plenora.postgres.native_declaration` |
| `plenora.postgres_type_kind` | `plenora.postgres.type_kind` |
| — | `plenora.geometry.encoding` (oggi `String` interna) |
| — | `plenora.geometry.crs_resolution`, `crs_id`, `axis_order` |

### plenora-data-tools

| Attuale | Canonica |
|---|---|
| `plenora.contract` (blob unico) | esplodere nelle chiavi §2, una per proprietà |

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

*Documento redatto come revisione tecnica indipendente. Lo stato normativo di
ogni sezione è quello, e soltanto quello, del registro di ratifica in testa al
documento: nessuna affermazione altrove sostituisce quel registro. Gli stati di
conformità in Appendice A sono rilevati per ispezione del codice, non per
esecuzione dei test, e sono ancorati ai commit `00f293e` (IO-tools), `a1f4130`
(data-tools) e `058aebf` (database-tools). Ogni fotografia successiva deve
dichiarare i propri: conteggi e riferimenti a numeri di riga non ancorati a un
commit sono obsoleti nel momento in cui vengono scritti.*

*Le fotografie in Appendice A precedono i lavori in corso dei team e non li
riflettono: `8bb65dd` e `03b6590` in IO-tools, `8fd8f79` e `a1f4130` in
data-tools chiudono già alcune righe della tabella.*
