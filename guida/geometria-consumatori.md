# Geometria: adattamento nei consumatori

Questa guida è **non normativa**. Il contratto del motore è
[Geometry Operations 1.0](../specs/data/GEOMETRY-OPERATIONS-1.0.md): primitive
OGC/DE-9IM, modelli geodetici, trasformazioni, editing dichiarato e coordinate
standard. Un FeatureServer/GeometryServer compatibile Esri possiede e verifica
la traduzione delle proprie API, i default e gli errori. La compatibilità del
servizio non è un requisito di qualifica del motore.

## Relazioni

La tabella illustra una traduzione possibile delle definizioni storiche delle
relazioni, con operandi ordinati A,B. Non promette equivalenza universale tra
SOAP, ArcObjects e ogni versione REST. Il consumatore deve fissare la propria
semantica pubblica, inclusi vuoti e boundary delle linee, prima di applicarla.
Le definizioni storiche sono descritte in
[IGeometryServer](https://developers.arcgis.com/enterprise-sdk/api-reference/net/IGeometryServer/);
[Relation REST](https://developers.arcgis.com/rest/services-reference/enterprise/relation/)
definisce invece il confine del servizio, compresa la semplificazione preliminare.
Queste fonti servono al consumatore e non sono oracoli del motore.
I pattern sono passati al kernel come nove caratteri; alternative si combinano
con OR nel consumatore. II, IB, BI e BB indicano intersezioni di interni/bordi.

| Nome del servizio dopo `esriGeometryRelation` | Traduzione candidata | Dominio / responsabilità del consumatore |
|---|---|---|
| Disjoint | `FF*FF****` | Nessuna intersezione tra i due insiemi. |
| Intersection | OR di `T********`, `*T*******`, `***T*****`, `****T****` | Intersezione non vuota degli insiemi. |
| Touch | OR di `FT*******`, `F**T*****`, `F***T****` | Interni disgiunti e almeno un contatto; verificare il dominio dimensionale del servizio. |
| In | `T*F**F***` | OGC Within, dove la definizione di servizio coincide. |
| Within | `**F**F***`, con controllo di non-vuoto | Covered-by: nessun punto di A nell'esterno di B; non confondere con OGC Within. |
| InteriorIntersection | `T********` | Intersezione non vuota degli interni. |
| LineCoincidence | `****1****` | Superficie/superficie con boundary OGC. Sulle linee BB non può avere dimensione 1: una semantica sul supporto richiede una traduzione distinta. |
| LineTouch | `F***1****` | Superficie/superficie, interni disgiunti e bordo condiviso lineare. Non estendere automaticamente alle linee. |
| PointTouch | II=F e massimo di IB, BI, BB pari a 0 | Controllo della matrice: IB/BI/BB solo F o 0, almeno uno 0. |
| Relation | matrice/pattern DE-9IM esplicito | Parsing di `relationParam`, SCL, quoting, ordine G1/G2 e composizione booleana interamente nel consumatore. |

PointTouch si ricava dalle quattro celle della matrice, senza attribuire al
kernel un nuovo nome di relazione. Le convenzioni su input vuoti e coppie dimensionali
rifiutate dal servizio si applicano prima o dopo la chiamata al motore.

## Altre operazioni del servizio

| API o convenzione | Primitive e adattamento del consumatore |
|---|---|
| Union / Intersect / Difference | Booleane generali; `output_dimension` esplicito se il servizio elimina componenti inferiori. Validare separatamente restrizioni di tipo, cardinalità, vuoti e ordine richiesti dal servizio. |
| Project | Risoluzione strutturale CRS e trasformazione esplicita; selezione della trasformazione, parametri pubblici e serializzazione dello spatial reference appartengono al servizio. Nessun clamp o extrapolazione impliciti. |
| Buffer / Densify / Distance / Areas and Lengths / Lengths | Selezionare modello, unità, datum e tolleranza; adattare array e ordine dei risultati. Un nome di API non decide il modello matematico. |
| Offset / Trim-Extend / Reshape / Auto Complete | Mappare solo i casi semanticamente equivalenti alle costruzioni GOP-016–020. Tradurre bit flag in opzioni esplicite; unchanged-to-empty, selezione delle regioni e repair del servizio non sono default del motore. |
| To / From GeoCoordinateString | Scegliere formato, precisione, datum e rappresentante della cella; implementare nel servizio dialetti, default, parsing permissivo e comportamento per elemento. Non presentare una conversione diversa come `standard_v1`. |
| Esri JSON | Convertire punti/paths/rings, shell/holes, chiusura, orientamento e vuoti al confine del servizio; conservare l'ordine degli assi dichiarato. Rifiutare Z/M/curve se la primitiva scelta è XY. |

Se la semantica del servizio non è esprimibile con le primitive disponibili,
il consumatore la implementa separatamente oppure dichiara il limite. Eventuali
prove di compatibilità ArcGIS appartengono al suo corpus e al suo ciclo di
rilascio; non modificano gli oracoli offline o le regole del motore.
