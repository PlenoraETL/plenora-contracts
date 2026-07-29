#!/usr/bin/env python3
"""Verifica un manifesto di rilascio contro i criteri di PLENORA-CRITERI-RC.md.

Copre C1 (forma del manifesto), C2.2 (la revisione citata esiste), C3.1 (un RC
di componente non implica un RC di sistema), C4.2 (il claim e' dichiarato) e
C4.4 (nessuna conformita' avionica).

NON copre C2.1, C2.3, C3.2, C4.3, C5.1 e C5.2: richiedono un giudizio che
nessun controllo automatico puo' dare. Sono dichiarati non automatizzati nel
documento, e qui non esiste un controllo che finga di coprirli.

Pensato per la CI di ciascun componente sul proprio manifesto, non per la CI di
plenora-contracts, che non ha accesso ai repository dei componenti.

Uso:
    python check_release_manifest.py release/contract-provenance.json
    python check_release_manifest.py --repo .. release/rc3-development.json
    python check_release_manifest.py --json-out esito.json <manifesto>

Esce 0 se il manifesto e' conforme, 1 altrimenti. Solo la standard library.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

CRITERIA_DOCUMENT = "PLENORA-CRITERI-RC.md"
REVISION = re.compile(r"^[0-9a-f]{40}$")
CLAIM_KEYS = ("component_rc", "system_rc", "avionic_certification")
VERIFICATION_CLAIMS = ("verified_internally", "verified_independently")
COMPONENT_PREFIX = "plenora-"

# Chiavi sotto cui i manifesti dei tre componenti dichiarano la revisione
# oggetto del manifesto. Piu' di una perche' i nomi divergono e imporne uno
# solo non e' fra i criteri.
REVISION_KEYS = ("revision", "candidate_revision", "target_revision",
                 "library_baseline_revision")


def find_revisions(document: object, component: str | None,
                   path: str = "", foreign: bool = False) -> list[tuple[str, str, bool]]:
    """Ogni revisione dichiarata, con il percorso e se appartiene ad altri.

    Un manifesto cita anche revisioni di altri repository — quella dell'ICD,
    quelle degli altri componenti. Verificarle nella storia locale produce un
    falso positivo, quindi vanno riconosciute e riportate come estranee: la
    forma si controlla, l'esistenza no.
    """
    found: list[tuple[str, str, bool]] = []
    if isinstance(document, dict):
        # Un oggetto che nomina un repository diverso dal proprio componente
        # delimita un sottoalbero estraneo. `name` conta solo se nomina davvero
        # un componente: dentro `release_tag` e' il nome del tag, non un
        # repository, e trattarlo come tale marcherebbe estranea la revisione
        # del proprio tag di rilascio.
        named = document.get("component") or document.get("repository")
        if named is None and isinstance(document.get("name"), str) \
                and document["name"].startswith(COMPONENT_PREFIX):
            named = document["name"]
        here_foreign = foreign or (
            isinstance(named, str) and component is not None and named != component
        )
        for key, value in document.items():
            here = f"{path}.{key}" if path else key
            key_foreign = here_foreign or key in ("icd", "external", "upstream")
            if key in REVISION_KEYS and isinstance(value, str):
                found.append((here, value, key_foreign))
            else:
                found.extend(find_revisions(value, component, here, key_foreign))
    elif isinstance(document, list):
        for index, value in enumerate(document):
            found.extend(find_revisions(value, component, f"{path}[{index}]", foreign))
    return found


def revision_exists(repository: Path, revision: str) -> bool | None:
    """True/False se git risponde, None se non e' interrogabile."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), "cat-file", "-e", f"{revision}^{{commit}}"],
            capture_output=True, text=True, check=False, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.returncode == 0


def check(manifests: dict[str, dict], repository: Path) -> tuple[list[str], list[str]]:
    """C1.1 chiede *almeno un* manifesto: i criteri di C1 valgono sull'unione.

    Un componente distribuisce lo stato su piu' file — provenienza, gate di
    congelamento, sviluppo in corso. Pretendere ogni campo in ogni file
    sarebbe piu' severo del criterio scritto.
    """
    errors: list[str] = []
    warnings: list[str] = []

    def lookup(field: str):
        for name, document in manifests.items():
            if field in document:
                return document[field], name
        return None, None

    # ---- C1.2 campi obbligatori, sull'unione dei manifesti
    for field in ("manifest_version", "component", "component_version"):
        value, _ = lookup(field)
        if value is None:
            errors.append(f"C1.2: campo obbligatorio assente da tutti i "
                          f"manifesti: {field!r}")
    version, source = lookup("manifest_version")
    if version is not None and not isinstance(version, bool) \
            and not isinstance(version, int):
        errors.append(f"C1.2: manifest_version in {source} deve essere un intero")

    component, _ = lookup("component")
    component = component if isinstance(component, str) else None

    revisions: list[tuple[str, str, bool]] = []
    for name, document in manifests.items():
        revisions += [(f"{name}:{where}", value, foreign)
                      for where, value, foreign in find_revisions(document, component)]

    own = [entry for entry in revisions if not entry[2]]
    if not own:
        errors.append("C1.2: nessuna revisione propria dichiarata "
                      f"(attese sotto una di {', '.join(REVISION_KEYS)})")
    for where, value, foreign in revisions:
        if not REVISION.fullmatch(value):
            errors.append(f"C1.2: {where} non e' una revisione di 40 cifre "
                          f"esadecimali: {value!r}")

    # ---- C1.3 claims espliciti
    claims, claims_source = lookup("claims")
    if claims is None:
        errors.append("C1.3: oggetto 'claims' assente da tutti i manifesti")
    elif not isinstance(claims, dict):
        errors.append("C1.3: 'claims' deve essere un oggetto")
    else:
        for key in CLAIM_KEYS:
            if key not in claims:
                errors.append(f"C1.3: claims.{key} assente — l'assenza non vale 'false'")
            elif not isinstance(claims[key], bool):
                errors.append(f"C1.3: claims.{key} deve essere booleano, "
                              f"non {type(claims[key]).__name__}")

        # ---- C3.1 un RC di componente non implica un RC di sistema
        if claims.get("system_rc") is True:
            errors.append("C3.1: system_rc non e' dichiarabile da un componente: "
                          "la qualifica di sistema e' posseduta da "
                          "plenora-contracts/conformance")

        # ---- C4.4 nessuna conformita' avionica
        if claims.get("avionic_certification") is True:
            errors.append("C4.4: avionic_certification deve valere false — "
                          "R0.5 dell'ICD lo vieta")

    # ---- C4.2 il claim di verifica e' dichiarato
    claim, _ = lookup("verification_claim")
    independent, _ = lookup("independent_review")
    attributes, _ = lookup("assurance_attributes")
    if isinstance(attributes, dict):
        claim = attributes.get("verification_claim", claim)
        independent = attributes.get("independent_review", independent)

    if claim is None:
        errors.append("C4.2: verification_claim non dichiarato da nessun manifesto")
    elif claim not in VERIFICATION_CLAIMS:
        errors.append(f"C4.2: verification_claim {claim!r} fuori dai valori ammessi "
                      f"({', '.join(VERIFICATION_CLAIMS)})")
    elif claim == "verified_independently" and independent is not True:
        errors.append("C4.2: claim 'verified_independently' senza "
                      "independent_review true")
    if claim is not None and independent is None:
        warnings.append("C4.2: independent_review non dichiarato accanto al claim")

    # ---- C2.2 la revisione propria esiste nella storia locale
    for where, value, foreign in revisions:
        if not REVISION.fullmatch(value):
            continue
        if foreign:
            warnings.append(f"C2.2: {where} appartiene a un altro repository, "
                            "esistenza non verificabile da qui")
            continue
        outcome = revision_exists(repository, value)
        if outcome is None:
            warnings.append(f"C2.2: git non interrogabile in {repository}, "
                            f"{where} non verificata")
        elif outcome is False:
            errors.append(f"C2.2: {where} = {value} non esiste nella storia di "
                          f"{repository}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, nargs="+",
                        help="uno o piu' manifesti: C1 vale sulla loro unione")
    parser.add_argument("--repo", type=Path,
                        help="repository in cui verificare le revisioni "
                             "(default: la directory del manifesto risalendo a un .git)")
    parser.add_argument("--json-out", type=Path)
    arguments = parser.parse_args()

    manifests: dict[str, dict] = {}
    for path in arguments.manifest:
        if not path.is_file():
            print(f"manifesto non trovato: {path}", file=sys.stderr)
            return 1
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            print(f"C1.1: {path} non e' JSON valido: {error}", file=sys.stderr)
            return 1
        if not isinstance(document, dict):
            print(f"C1.1: {path} deve essere un oggetto JSON", file=sys.stderr)
            return 1
        manifests[path.name] = document

    repository = arguments.repo
    if repository is None:
        repository = arguments.manifest[0].resolve().parent
        while not (repository / ".git").exists() and repository != repository.parent:
            repository = repository.parent

    errors, warnings = check(manifests, repository)
    status = "pass" if not errors else "fail"

    for warning in warnings:
        print(f"avviso   {warning}")
    for error in errors:
        print(f"ERRORE   {error}")
    print(f"\n{', '.join(manifests)}: {status} "
          f"({len(errors)} errori, {len(warnings)} avvisi) — {CRITERIA_DOCUMENT}")
    print("non automatizzati: C2.1, C2.3, C3.2, C4.3, C5.1, C5.2")

    if arguments.json_out:
        arguments.json_out.parent.mkdir(parents=True, exist_ok=True)
        arguments.json_out.write_text(
            json.dumps({"criteria_document": CRITERIA_DOCUMENT,
                        "manifests": [str(path) for path in arguments.manifest],
                        "status": status, "errors": errors, "warnings": warnings,
                        "not_automated": ["C2.1", "C2.3", "C3.2",
                                          "C4.3", "C5.1", "C5.2"]},
                       indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
