# Trasformazioni

Cosa succede al contratto quando il dato viene davvero trasformato.

## Perché serviva

`run_roundtrip.py` e `run_chain.py` usano un piano che è un **filtro identità**:
su 147 operazioni ne esercitano una, scelta apposta per non trasformare niente.
Verificano che il contratto sopravviva al **transito**, che è metà del problema.

L'altra metà è più difficile e non era mai stata guardata. Dopo una riproiezione
`crs_id` deve cambiare: chi lo riscrive? Dopo un centroide i poligoni diventano
punti: `types` segue? R2.4 distingue lineage `identity`, `derived` e
`multi_source`, e finora la catena non aveva mai prodotto un dato derivato —
quelle regole non erano mai state esercitate da nessuno.

## Non giudica, scopre

Per diversi casi il contratto atteso **non è deciso**, e inventarlo qui
significherebbe imporre come regola un'opinione. Lo strumento esegue, osserva e
riporta: dove esiste un'attesa dichiarata la verifica, dove non esiste scrive
`da_decidere` e mostra cosa è successo. Le voci `da_decidere` non sono difetti:
sono domande che l'ICD non risponde.

```
python conformance/transforms/run_transforms.py --checkouts .. --report t.json
```

Richiede `--features full-backends`: `proj` per la riproiezione, `geos` per le
operazioni topologiche.

## Cosa ha trovato la prima passata

Su `plenora-data-tools`, revisione corrente, sette trasformazioni.

### Un centroide lascia il contratto che dichiara il tipo sbagliato

```
ingresso  byte=Polygon   types='polygon'  declaration='exact'
uscita    byte=Point     types='polygon'  declaration='exact'
```

`geo.centroid` sostituisce ogni poligono con il proprio centroide. I byte
diventano `Point`; il contratto continua a dichiarare `types: polygon` con
`types_declaration: exact`.

È **H-01 nella forma «reinterpretazione»**, che l'ICD definisce così in §3: non
perdita di dati, ma un metadato che contraddice i byte che accompagna. Un
consumatore che decide sul tipo dichiarato riceve un'informazione falsa — e qui
la dichiarazione è per giunta `exact`, cioè la più forte possibile.

`geo.buffer` lascia anch'esso il contratto invariato, ma lì il tipo resta
davvero `polygon`: la domanda aperta è solo se `types_declaration: exact` sia
ancora appropriata su una geometria derivata.

### La riproiezione non può eseguire

```
contract violation: campo geometria `geometry`: chiave `plenora.geometry.crs_id`
già presente con un valore diverso da quello del contratto
(R2.6: il componente fallisce, non sovrascrive)
```

`geo.reproject` è l'unica operazione che **deve** cambiare il CRS — la
documentazione dei kernel lo dice: «unico step che modifica il CRS». Il guard di
R2.6 glielo impedisce.

Vale la pena rileggere R2.6: parla di chiavi definite da standard esterni che
**coesistono** con quelle canoniche, e impone il fallimento quando le due
descrizioni dello stesso fatto **divergono**. Una riproiezione non è una
divergenza fra due descrizioni: è un fatto che cambia. Applicare lì R2.6
confonde «due fonti non concordano» con «il valore viene aggiornato».

Se questa lettura è giusta il difetto è nell'ampiezza del guard, non nella
regola. La decisione è dell'owner.

### Quello che invece funziona

`geo.simplify` e `geo.make_valid` lasciano il contratto invariato, ed è
corretto: tolgono vertici o riparano una geometria senza cambiare tipo né
sistema di riferimento.

E il rifiuto dimensionale funziona come `ADR-0008` di data-tools decide: un
kernel geo su `dimensions != xy` rifiuta **in analisi del piano**, non a metà
esecuzione, citando operazione e dimensionalità e mai i dati. Era la mia
preoccupazione iniziale — «un buffer su XYZ appiattisce e il contratto continua
a dichiarare xyz?» — e la risposta è che l'operazione non parte proprio. Nessuna
menzogna possibile.

`geo.dissolve` non è nel dispatch v1 dell'executor: limite di ambito dichiarato,
non difetto.

## Due disallineamenti fra ICD e implementazione

**I kernel geo pretendono l'estensione GeoArrow.** La discovery di data-tools
riconosce una colonna geometrica dalle sole chiavi canoniche — il commento in
`discover_input_contract` lo dichiara esplicitamente — ma l'esecuzione richiede
anche `ARROW:extension:name`. Un dataset conforme a §2 e privo dell'estensione
supera la discovery e fallisce a esecuzione.

§2 non rende obbligatoria l'estensione; R2.6 la dichiara «ammessa ed esente».
Ammessa non è lo stesso che richiesta.

**E il rifiuto arriva a esecuzione, non in analisi.** `ADR-0008` stabilisce che
i rifiuti avvengano in fase di analisi del piano, «mai a metà esecuzione». Il
rifiuto dimensionale rispetta quel principio; quello sull'estensione GeoArrow no
— porta un identificativo di esecuzione. Il caso è deciso prima di leggere una
riga: potrebbe esserlo anche il rifiuto.

Il caso `polygon_xy_projected` del corpus porta l'estensione apposta, così le
trasformazioni si esercitano invece di fermarsi sul disallineamento. Il
disallineamento resta una domanda.
