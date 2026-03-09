#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_BASENAME="${1:-alien-evolution}"
OUTPUT_DIR="${2:-${ROOT_DIR}/build/web}"

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/alien-evolution-pyxapp.XXXXXX")"
APP_DIR="${TMP_ROOT}/${OUTPUT_BASENAME}"

cleanup() {
    rm -rf "${TMP_ROOT}"
}
trap cleanup EXIT

mkdir -p "${APP_DIR}"
cp -r "${ROOT_DIR}/src" "${APP_DIR}/"
cp "${ROOT_DIR}/startup.py" "${APP_DIR}/"

mkdir -p "${OUTPUT_DIR}"
cd "${OUTPUT_DIR}"
uv run --project "${ROOT_DIR}" pyxel package "${APP_DIR}" "${APP_DIR}/startup.py"
uv run --project "${ROOT_DIR}" pyxel app2html "${OUTPUT_BASENAME}.pyxapp"

printf 'Created: %s/%s.pyxapp\n' "${OUTPUT_DIR}" "${OUTPUT_BASENAME}"
printf 'Created: %s/%s.html\n' "${OUTPUT_DIR}" "${OUTPUT_BASENAME}"
