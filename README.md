# plenora-contracts

Baseline dei contratti trasversali fra i tre componenti Plenora:
`plenora-IO-tools`, `plenora-data-tools`, `plenora-database-tools`.

## Contenuto

- [`docs/PLENORA-CONTRATTI-TRASVERSALI.md`](docs/PLENORA-CONTRATTI-TRASVERSALI.md)
  — documento normativo di interfaccia (ICD). È la fonte autorevole: in caso di
  conflitto prevale sulla documentazione dei singoli repository.
- `src/` — il crate `plenora-contracts` con i tipi di confine. **Non ancora
  creato**: la sua estrazione è il passo 2 di §15 dell'ICD ed è sospesa in
  attesa della versione 2.0 del documento.

## Stato

Il registro di ratifica in testa all'ICD è l'unica fonte sullo stato normativo
di ciascuna sezione. Nessuna affermazione altrove lo sostituisce.

Owner: Marco Bonamente.

## Come citarlo

Ogni change impact analysis nei tre repository **deve** riferirsi a un tag di
questo repository, non al contenuto del file in un dato momento. I tag sono
immutabili per convenzione; le dipendenze future dal crate useranno il revision
esatto registrato nel `Cargo.lock`, non il solo tag.

## Come proporre una modifica

Secondo §16 dell'ICD: indicare regole toccate, impatto sui tre componenti, piano
di migrazione e retrocompatibilità. La modifica entra in vigore quando i tre team
l'hanno recepita; fino ad allora resta vincolante la versione precedente.
