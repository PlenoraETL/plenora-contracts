# Mappatura: `manipola` di Plenora contro il catalogo di data-tools

Misurata il 31 luglio 2026 eseguendo ogni operazione contro l'executor reale,
non confrontando elenchi. Serve a convertire «non sappiamo quanto costa la
migrazione» in un numero.

## Esito

`manipola` espone **40 operazioni**. Il catalogo di data-tools ne ha **147**.

| Esito | Quante | Significato |
|---|---|---|
| Raggiungibili | 35 | L'operazione esiste ed è nel dispatch. Il fallimento nel test è del test: config assente o input insufficienti |
| Fuori dispatch v1 | 1 | `geo.dissolve` — Fase 2B/2C dell'executor |
| Nome diverso | 2 | `op_union` e `op_md5_hash` esistono con altro nome e semantica da verificare |
| Inconcludenti | 3 | Falliti per la fixture usata, non per l'operazione |

**Trentacinque su quaranta sono già raggiungibili.** La corrispondenza fra i due
cataloghi non è casuale: data-tools è stata disegnata contro questa superficie, e
`op_geo_buffer` → `geo.buffer`, `op_filter` → `table.filter` valgono per la
grande maggioranza.

## I casi che non corrispondono

**`geo.dissolve` è fuori dal dispatch v1.** L'executor lo dichiara: *«coperte le
trasformazioni geo 1:1 in place, le misure, le estensioni v1.1-v1.3 e i binari
del perimetro ADR-0014 M1; il resto è Fase 2B/2C»*. `dissolve` è ManyToOne, non
1:1. È una priorità del secondo cantiere, non un elemento di catalogo fra tanti:
Plenora lo usa.

**`op_union` non è `table.union`**, che non esiste. Plenora concatena verticalmente
più DataFrame; data-tools ha `table.concat`, `table.concat_by_name` e
`table.union_distinct`. Tre operazioni per un concetto che in Plenora è uno solo,
e la scelta fra loro cambia il risultato: `union_distinct` deduplica.

**`op_md5_hash` non ha omonimo.** Esiste `table.stable_fingerprint`, che risolve
un problema simile. Un'impronta stabile non è un MD5: se una pipeline confronta
hash storici, la differenza si vede.

## Cosa questo non misura

**La semantica.** Un omonimo non è un equivalente. Le differenze già note dai
reperti di questa settimana:

- i kernel geo rifiutano `dimensions != xy`, mentre GeoPandas appiattisce;
- `geo.reproject` è passato per una fase in cui non poteva eseguire affatto;
- l'export verso GeoJSON e KML rifiuta un CRS diverso da WGS84 invece di
  riproiettare in silenzio.

Ognuna è la scelta giusta, e ognuna è una regressione dal punto di vista di un
utente che oggi fa quella cosa. Il costo della migrazione sta lì, non nel numero
di operazioni mancanti.

## Due difetti della misura, dichiarati

Il primo giro è stato buttato: dopo il primo successo il file di uscita esisteva
e data-tools rifiuta di sovrascriverlo — no-clobber di R14. Trentatré risultati
su trentanove dicevano solo quello.

E tre operazioni restano inconcludenti perché la fixture usata ha una colonna
geometrica: `table.fill_na` non supporta il tipo `Binary`, `geo.from_coords`
rifiuta un input che ha già una geometria. Vanno rimisurate con una tabella
senza geometria.
