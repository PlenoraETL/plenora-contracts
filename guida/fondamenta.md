# Fondamenta comuni

Tutte le CLI e tutti gli SDK della famiglia condividono la stessa grammatica
esterna. Quello che impari qui vale per ogni libreria.

## La busta CLI (v2)

Ogni invocazione con `--format json` risponde su stdout con **una** busta
JSON (`plenora-cli-envelope-v2`): o un successo col risultato dentro, o un
errore strutturato. Niente testo libero mescolato al risultato; la
diagnostica umana va su stderr.

```json
{"status": "ok", "component": "...", "operation": "...", "version": 1,
 "result": { ... }}
```

```json
{"status": "error", "error": {"category": "invalid_plan", "phase": "validate",
 "message": "...", "retry": {"kind": "never"}}}
```

- **`category`** è il vocabolario chiuso di `error-v1`: fra le altre
  `invalid_plan` (il documento d'ingresso non soddisfa il contratto),
  `unsupported` (la richiesta è valida ma fuori dalle capacità dichiarate),
  `io`, `auth`, `conflict`, `resource_limit`, `cancelled`, `deadline`.
- **`message`** è testo fisso: non cita mai valori, righe o colonne del
  documento. Ciò che serve per capire sta nella categoria, nella fase e
  negli assi strutturati, non nel testo.
- **`retry`** dice se ritentare ha senso (`never`, `safe`, `after_backoff`)
  e, sulle scritture, **`remote_effect`** dice che cosa è successo dall'altra
  parte (`none`, `committed`, `unknown`): un esito sconosciuto non è mai un
  successo.

## Gli exit code

Gli exit code sono tipizzati e stabili: 0 è il successo, e ogni categoria
d'errore ha il suo codice (la proiezione esatta sta nel contratto CLI del
componente; `invalid_plan` e `unsupported` sono distinti apposta: il primo
dice «documento malformato», il secondo «capacità assente»). Uno script può
decidere dal codice senza leggere la busta.

## Scoprire le capacità

Ogni CLI espone `capabilities` (busta `capabilities-v2`): versione del
componente, operazioni con le versioni, e le capacità osservabili (formati,
backend, limiti). È il modo giusto di chiedersi «questa installazione sa
fare X?» — interrogare, non supporre. I cataloghi pubblici di questo
repository (`catalogs/*.json`) sono il contratto corrispondente lato
famiglia: ogni operazione con ingressi, uscite, side effect e controlli
(`cancellation`, `deadline`, `idempotency_key`).

## Gli SDK Python

Ogni libreria pubblica una wheel (`plenora_io`, `plenora_data`,
`plenora_database`, `plenora_storage`, `plenora_rest`) che espone le stesse
operazioni del catalogo con oggetti Python: `pyarrow.Table` dove la CLI usa
file IPC, eccezioni tipizzate dove la CLI usa exit code. La corrispondenza è
contrattuale (binding `python-sdk-v1`): stessa operazione, stesso esito,
stessa categoria d'errore. Le eccezioni portano gli assi dell'errore come
attributi (categoria, fase, retry), mai i dati del documento.

## Annullamento e scadenze

Le operazioni che dichiarano `cancellation`/`deadline` nel catalogo accettano
una scadenza e si interrompono pulite: l'esito è `cancelled`/`deadline`, mai
un risultato parziale spacciato per intero.
