# Fase 0 — la stessa pipeline sui due stack

Non serve a integrare. Serve a misurare l'attrito prima che qualcuno riscriva
ottomila righe contro un'ipotesi.

Pipeline: shapefile catastale `EPSG:3003` → filtro sugli attributi →
riproiezione a `EPSG:4326`. Stack di riferimento: GeoPandas/Shapely, che è
quello che Plenora usa oggi. Stack nuovo: i tre componenti.

## Cosa è emerso alla prima esecuzione

**3.000 particelle, 12 aspetti divergenti su 14.**

### Gli identificativi catastali si perdono, e oggi non si perdono

```
GeoPandas   ID_PARTICE  int64     3000 identificativi distinti
i tre       ID_PARTICE  double    1501
```

GDAL mappa un campo DBF `N` con zero decimali e larghezza ≥ 10 su `Integer64`;
`plenora-IO-tools` lo mappa su `f64` sempre. Oltre 2⁵³ due interi distinti
diventano lo stesso `f64`, e metà delle particelle perde identità.

La perdita è **dichiarata** — `read_loss` riporta 3.000 occorrenze e la fedeltà
complessiva è `approximating` — ed è la correzione giusta fatta il 31 luglio. Ma
dichiarare una perdita non compensa il fatto che oggi quell'informazione non si
perde. **È la prima regressione misurata della migrazione, ed è sui dati
patrimoniali.**

### La riproiezione viene rifiutata su dati veri

```
CRS error: la colonna dichiara un'incoerenza CRS non risolta
(`declared_unresolved`); la risoluzione richiede una decisione
esplicita nel piano (R4.6.3)
```

GeoPandas riproietta senza fiatare. I tre rifiutano, perché il `.prj` prodotto
dal generatore dichiara un CRS che il resolver non risolve in modo affidabile, e
R4.6.3 vieta al centro di decidere senza una decisione nel piano.

È il comportamento corretto — riproiettare su un CRS non risolto sarebbe
sceglierne uno per conto dell'utente — ed è **anche una pipeline che oggi
funziona e domani si ferma**. La decisione esplicita nel piano esiste; nessuno
la scrive oggi perché non serviva.

### Le colonne omonime

Il DBF tronca `denominazione_catastale` e `denominazione_storica` sullo stesso
nome. GeoPandas conserva **entrambe** le colonne; i tre ne tengono una. Nove
colonne contro otto.

## Prestazioni

Misurate invocando i binari **release** direttamente, migliore di tre
esecuzioni. Il primo tentativo, via `cargo run`, dava numeri fino a 2000 volte
peggiori: era l'overhead di cargo, non il codice.

```
                       i tre        GeoPandas     rapporto
lettura shapefile      0.8117 s     0.0685 s      12x
filtro                 0.0658 s     0.0008 s      82x
```

**Il filtro non è un confronto onesto**: GeoPandas filtra un DataFrame già in
memoria, i tre avviano un processo, leggono un file Arrow, filtrano e ne
riscrivono uno. Quasi tutto è confine, non filtro — costo architetturale
dell'integrazione a sottoprocessi, che binding PyO3 con l'Arrow C Data Interface
eliminerebbero quasi del tutto.

**La lettura invece è confrontabile**, e dodici volte è un divario da spiegare.
Parte è lavoro in più che IO-tools fa davvero: valida ogni WKB, costruisce il
contratto, calcola il rapporto di perdita. Parte è scrivere 670 KB su disco. Su
3.000 righe pesa poco in assoluto; su tre milioni conta.

## Cosa questo non misura

Un dataset solo, 3.000 righe, una pipeline. Non dice nulla su volumi reali,
streaming, memoria, o sulle altre trentanove operazioni.

E non dice se il risultato è **geograficamente** corretto: una particella
spostata di quaranta metri ha coordinate valide, tipo valido e CRS dichiarato.
Serve qualcuno che la guardi su una mappa.
