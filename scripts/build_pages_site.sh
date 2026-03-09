#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE_DIR="${1:-${ROOT_DIR}/site}"
DOCS_SRC_DIR="$(mktemp -d "${TMPDIR:-/tmp}/alien-evolution-pages-src.XXXXXX")"
WEB_BUILD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/alien-evolution-pages-web.XXXXXX")"

cleanup() {
    rm -rf "${DOCS_SRC_DIR}"
    rm -rf "${WEB_BUILD_DIR}"
}
trap cleanup EXIT

cd "${ROOT_DIR}"

./scripts/build_pyxapp.sh alien-evolution "${WEB_BUILD_DIR}"
rm -rf "${SITE_DIR}"

mkdir -p "${DOCS_SRC_DIR}" "${DOCS_SRC_DIR}/figs"
cp "${ROOT_DIR}/pages/index.md" "${DOCS_SRC_DIR}/index.md"
cp "${ROOT_DIR}/README.md" "${DOCS_SRC_DIR}/project-overview.md"
cp "${ROOT_DIR}/GAME_INFO.md" "${DOCS_SRC_DIR}/GAME_INFO.md"
cp "${ROOT_DIR}/RESEARCH.md" "${DOCS_SRC_DIR}/RESEARCH.md"
cp "${ROOT_DIR}/PORTING_GUIDE.md" "${DOCS_SRC_DIR}/PORTING_GUIDE.md"
cp "${ROOT_DIR}/CLI_UTILITIES.md" "${DOCS_SRC_DIR}/CLI_UTILITIES.md"
cp "${ROOT_DIR}/AI.md" "${DOCS_SRC_DIR}/AI.md"
cp "${ROOT_DIR}/DEVELOPMENT.md" "${DOCS_SRC_DIR}/DEVELOPMENT.md"
cp "${ROOT_DIR}/OPEN_ISSUES.md" "${DOCS_SRC_DIR}/OPEN_ISSUES.md"
cp -r "${ROOT_DIR}/figs/." "${DOCS_SRC_DIR}/figs/"

PAGES_DOCS_DIR="${DOCS_SRC_DIR}" uv run --with mkdocs mkdocs build --strict --site-dir "${SITE_DIR}"

mkdir -p "${SITE_DIR}/play"
cp "${WEB_BUILD_DIR}/alien-evolution.html" "${SITE_DIR}/play/index.html"
touch "${SITE_DIR}/.nojekyll"
