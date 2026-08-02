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
# Il default e' la campagna 1.0 qualificata. MANIFEST resta sovrascrivibile per
# esecuzioni esplorative, che non devono essere confuse con questa evidence.
MANIFEST=${MANIFEST:-"${CONTRACTS}/conformance/campaigns/v1.0.0/execution.json"}
PINNED="${ROOT}/pinned"
REPORT=${REPORT:-${CONTRACTS}/conformance/roundtrip.json}
CASES=${CASES:-${CONTRACTS}/conformance/cases}

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
root_real=$(realpath -m -- "${ROOT}")
contracts_real=$(realpath -m -- "${CONTRACTS}")
cases_real=$(realpath -m -- "${CASES}")
case "${cases_real}" in
    "${root_real}/cases"|"${root_real}"/cases-*|\
    "${contracts_real}/conformance/cases"|"${contracts_real}/conformance"/cases-*)
        ;;
    *)
        echo "directory corpus non sicura: ${CASES}" >&2
        exit 2
        ;;
esac
rm -rf -- "${cases_real}"
mkdir -p "${cases_real}"
CASES=${cases_real}
python3 "${CONTRACTS}/conformance/corpus/generate.py" \
        --out "${CASES}" | tail -3

echo
echo "== qualifica =========================================================="
set +e
python3 "${CONTRACTS}/conformance/run_roundtrip.py" \
        --cases "${CASES}" \
        --components "${MANIFEST}" \
        --checkouts "${PINNED}" \
        --report "${REPORT}"
outcome=$?
set -e

echo
echo "== catena ============================================================="
# Il roundtrip verifica ogni componente da solo; la catena verifica la
# composizione, con il bordo di scrittura come giudice terminale. Sono due
# domande diverse e la seconda non segue dalla prima per verifica, solo per
# ragionamento.
set +e
python3 "${CONTRACTS}/conformance/run_chain.py" \
        --cases "${CASES}" \
        --components "${MANIFEST}" \
        --checkouts "${PINNED}" \
        --report "${REPORT%.json}-chain.json"
chain=$?
set -e

echo
echo "== pairwise bidirezionale ============================================="
set +e
python3 "${CONTRACTS}/conformance/run_pairwise.py" \
        --cases "${CASES}" \
        --components "${MANIFEST}" \
        --checkouts "${PINNED}" \
        --report "${REPORT%.json}-pairwise.json"
pairwise=$?
set -e

echo
echo "rapporto roundtrip: ${REPORT}"
echo "rapporto catena:    ${REPORT%.json}-chain.json"
echo "rapporto pairwise:  ${REPORT%.json}-pairwise.json"
# Un roundtrip non eseguito non e' un successo: run_roundtrip.py restituisce
# gia' 1 in quel caso, e qui non lo si addolcisce.
if [ ${outcome} -ne 0 ] || [ ${chain} -ne 0 ] || [ ${pairwise} -ne 0 ]; then
    exit 1
fi
exit 0
