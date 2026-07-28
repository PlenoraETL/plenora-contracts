# plenora-contracts

Baseline dei contratti trasversali fra i tre componenti Plenora:
`plenora-IO-tools`, `plenora-data-tools`, `plenora-database-tools`.

## Contenuto

- [`docs/PLENORA-CONTRATTI-TRASVERSALI.md`](docs/PLENORA-CONTRATTI-TRASVERSALI.md)
  — documento normativo di interfaccia (ICD). È la fonte autorevole: in caso di
  conflitto prevale sulla documentazione dei singoli repository.
- `src/` — il futuro crate `plenora-contracts` con i tipi di confine. **Non
  ancora creato**: la sua estrazione è il passo 2 di §15 dell'ICD ed è in
  attesa della ratifica di §15.3.

## Stato

Il registro di ratifica in testa all'ICD è l'unica fonte sullo stato normativo
di ciascuna sezione. Nessuna affermazione altrove lo sostituisce.

Owner: Marco Bonamente.

## Come citarlo

La proposta §15.2 della 2.0-rc4 richiede che ogni change impact analysis nei tre
repository si riferisca a un tag annotato e firmato e alla revisione esatta
corrispondente, non al contenuto del file in un dato momento. Dopo la ratifica,
le dipendenze dal crate useranno la revisione registrata nel `Cargo.lock` e la CI
userà `--locked`.

## Come proporre una modifica

La proposta §16 della 2.0-rc4 richiede di indicare regole e hazard toccati,
impatto sui tre componenti, piano di migrazione e retrocompatibilità. I tre team
registrano la propria posizione tecnica; l'owner ratifica solo in assenza di
rilievi bloccanti e dopo la revisione indipendente richiesta. La ratifica rende
il requisito vincolante; l'adozione nei componenti è un atto successivo e
verificabile.
