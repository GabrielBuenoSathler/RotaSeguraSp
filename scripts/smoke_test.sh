#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:3000}"
BASE_URL="${BASE_URL%/}"

require_status() {
  local path="$1"
  local expected="$2"
  local status
  status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    --max-time 10 "${BASE_URL}${path}")"
  if [[ "$status" != "$expected" ]]; then
    echo "Falha: ${path} retornou HTTP ${status}; esperado ${expected}." >&2
    exit 1
  fi
  echo "OK ${status} ${path}"
}

require_status / 200
require_status /api/health 200
require_status /api/features 200

features="$(curl --silent --show-error --fail --max-time 10 "${BASE_URL}/api/features")"
if [[ "$features" != *'"route_alternatives"'* || "$features" != *'"geocoding"'* ]]; then
  echo "Falha: resposta inesperada em /api/features: ${features}" >&2
  exit 1
fi

echo "Smoke test concluído: ${BASE_URL}"
