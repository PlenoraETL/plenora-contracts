# plenora-contracts

Baseline dei contratti trasversali fra i tre componenti Plenora:
`plenora-IO-tools`, `plenora-data-tools`, `plenora-database-tools`.

## Contenuto

- [`docs/PLENORA-CONTRATTI-TRASVERSALI.md`](docs/PLENORA-CONTRATTI-TRASVERSALI.md)
  — documento normativo di interfaccia (ICD). È la fonte autorevole: in caso di
  conflitto prevale sulla documentazione dei singoli repository.
- [`docs/PIANO-INTEGRAZIONE.md`](docs/PIANO-INTEGRAZIONE.md) — come i tre
  componenti entrano nel backend di Plenora, in che ordine e chi fa cosa. Non è
  normativo: cambia quando i fatti lo smentiscono.
- [`docs/PIANO-DI-LAVORO.md`](docs/PIANO-DI-LAVORO.md) — coordinamento fra i tre
  team: chi fa cosa, in che ordine, e cosa sblocca cosa. Istantanea datata e non
  normativa; lo stato autorevole sta nelle fonti citate in Appendice A dell'ICD.
- [`docs/RATIFICA-DECISIONI-APERTE.md`](docs/RATIFICA-DECISIONI-APERTE.md) — le
  quindici voci del registro ancora `proposta`, con l'adozione già in atto nei tre
  componenti e cosa comporta ratificare ciascuna. Serve a decidere voce per voce
  senza rileggere l'ICD; non è normativo, prevale il registro.
- [`docs/PLENORA-CRITERI-RC.md`](docs/PLENORA-CRITERI-RC.md) — criteri di release
  candidate. Documento di **processo**, non di interfaccia: fissa solo ciò che
  deve essere confrontabile fra i tre componenti, non quali test eseguire. Non
  emenda l'ICD e non ha voce in capitolo sul contratto dati. Verificato da
  `scripts/check_release_manifest.py`, che a sua volta è verificato da
  `scripts/test_check_release_manifest.py`.
- [`docs/PLENORA-INTEGRAZIONE-TRE-LIBRERIE.pdf`](docs/PLENORA-INTEGRAZIONE-TRE-LIBRERIE.pdf)
  — documento divulgativo su come i tre componenti si dividono il lavoro e cosa
  mettono a disposizione. Non è normativo: in caso di conflitto prevale l'ICD.
  Si rigenera con `python scripts/build_integration_pdf.py`; conteggi e tabelle
  vanno rilevati dal codice, non copiati dalla documentazione dei componenti.
- `conformance/` — corpus neutro e runner che verificano il contratto sui tre
  componenti. Perimetro della qualifica di sistema `plenora-system-contract-roundtrip-v1`,
  di cui questo repository è proprietario. Vedi
  [`conformance/README.md`](conformance/README.md).
- `src/` — il futuro crate `plenora-contracts` con i tipi di confine. **Non
  ancora creato**: la sua estrazione è il passo 2 di §15 dell'ICD ed è in
  attesa della ratifica di §15.3.

## Stato

Il registro di ratifica in testa all'ICD è l'unica fonte sullo stato normativo
di ciascuna sezione. Nessuna affermazione altrove lo sostituisce.

Owner: Marco Bonamente.

Baseline ICD corrente: **2.0-rc17**. L'emendamento R4.3.2 e la diagnostica
row-scoped R9.9–R9.14 restano `proposta` finché l'owner non ne registra la
ratifica nella tabella normativa.

## Come citarlo

La proposta §15.2 della 2.0-rc15 richiede che ogni change impact analysis nei tre
repository si riferisca a un tag annotato e firmato e alla revisione esatta
corrispondente, non al contenuto del file in un dato momento. Dopo la ratifica,
le dipendenze dal crate useranno la revisione registrata nel `Cargo.lock` e la CI
userà `--locked`.

## Come proporre una modifica

La proposta §16 della 2.0-rc15 richiede di indicare regole e hazard toccati,
impatto sui tre componenti, piano di migrazione e retrocompatibilità. I tre team
registrano la propria posizione tecnica; l'owner ratifica solo in assenza di
rilievi bloccanti e dopo la revisione indipendente richiesta. La ratifica rende
il requisito vincolante; l'adozione nei componenti è un atto successivo e
verificabile.
