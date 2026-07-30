#!/usr/bin/env bash
# Esegue la qualifica di sistema sulle revisioni fissate in components.json.
#
# Presuppone i quattro repository montati sotto /work. Non li modifica: il
# checkout alle revisioni fissate avviene in cloni separati sotto /work/pinned,
# cosi' l'albero di lavoro di chi esegue resta intatto e la qualifica gira
# davvero sulle revisioni dichiarate e non su cio' che era aperto sulla
# macchina.
set -euo pipefail

ROOT=${ROOT:-/work}
CONTRACTS="${ROOT}/plenora-contracts"
# Il manifesto e' sovrascrivibile perche' servono due esecuzioni diverse: la
# qualifica, che gira su revisioni fissate e immutabili ed e' evidenza, e la
# verifica esplorativa, che gira sul codice corrente e dice se una correzione
# funziona. Confonderle produce un numero che non descrive ne' l'una ne' l'altra.
MANIFEST=${MANIFEST:-"${CONTRACTS}/conformance/components.json"}
PINNED="${ROOT}/pinned"
REPORT=${REPORT:-${CONTRACTS}/conformance/roundtrip.json}

test -f "${MANIFEST}" || { echo "manifesto non trovato: ${MANIFEST}" >&2; exit 2; }

echo "== revisioni fissate =================================================="
python3 - "${MANIFEST}" <<'PY'
import json, sys
manifest = json.load(open(sys.argv[1], encoding="utf-8"))
for component in manifest["components"]:
    tag = f"  tag {component['tag']}" if component.get("tag") else ""
    print(f"  {component['name']:<24} {component['revision'][:12]}{tag}")
PY

echo
echo "== checkout alle revisioni fissate ===================================="
mkdir -p "${PINNED}"
python3 - "${MANIFEST}" <<'PY' > /tmp/pins.txt
import json, sys
manifest = json.load(open(sys.argv[1], encoding="utf-8"))
for component in manifest["components"]:
    print(f"{component['name']}\t{component['revision']}")
PY

while IFS=$'\t' read -r name revision; do
    source="${ROOT}/${name}"
    target="${PINNED}/${name}"
    test -d "${source}/.git" || { echo "checkout assente: ${source}" >&2; exit 2; }
    if [ ! -d "${target}/.git" ]; then
        git clone --quiet --shared "${source}" "${target}"
    fi
    git -C "${target}" fetch --quiet origin 2>/dev/null || true
    # `git -C <src> cat-file` verifica che la revisione esista davvero prima di
    # provare a estrarla: un pin sbagliato deve dirlo, non fallire oscuramente.
    git -C "${source}" cat-file -e "${revision}^{commit}" \
        || { echo "revisione ${revision} assente in ${source}" >&2; exit 2; }
    git -C "${target}" fetch --quiet "${source}" "${revision}" 2>/dev/null || true
    git -C "${target}" checkout --quiet --detach "${revision}"
    git -C "${target}" reset --quiet --hard "${revision}"
    git -C "${target}" clean -qfdx -e target
    echo "  ${name} -> $(git -C "${target}" rev-parse --short HEAD)"
done < /tmp/pins.txt

echo
echo "== generazione del corpus ============================================="
python3 "${CONTRACTS}/conformance/corpus/generate.py" \
        --out "${CONTRACTS}/conformance/cases" | tail -3

echo
echo "== qualifica =========================================================="
set +e
python3 "${CONTRACTS}/conformance/run_roundtrip.py" \
        --cases "${CONTRACTS}/conformance/cases" \
        --components "${MANIFEST}" \
        --checkouts "${PINNED}" \
        --report "${REPORT}"
outcome=$?
set -e

echo
echo "rapporto: ${REPORT}"
# Un roundtrip non eseguito non e' un successo: run_roundtrip.py restituisce
# gia' 1 in quel caso, e qui non lo si addolcisce.
exit ${outcome}
