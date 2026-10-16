#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENVIRONMENT="${1:-}"
ACTION="${2:-}"
case "$ENVIRONMENT" in
dev | homolog | prod) ;;
*)
  echo 'Uso: scripts/env.sh {dev|homolog|prod} {init|config|build|up|down|logs|ps|migrate|db-access|deps} [argumentos]' >&2
  exit 1
  ;;
esac
export ENV_FILE="$ROOT/deploy/.env.$ENVIRONMENT"
if [[ "$ACTION" == init ]]; then
  if [[ -e "$ENV_FILE" ]]; then
    echo "Arquivo já existe: $ENV_FILE" >&2
    exit 1
  fi
  umask 077
  python3 - "$ENV_FILE.example" "$ENV_FILE" "$ENVIRONMENT" <<'PYTHON'
import secrets
import sys
from pathlib import Path
source, target, environment = sys.argv[1:]
content = Path(source).read_text().replace(
    f"defina-uma-senha-exclusiva-{environment}", secrets.token_urlsafe(32)
)
content = content.replace(f"defina-uma-senha-admin-{environment}", secrets.token_urlsafe(32))
with open(target, "x") as output:
    output.write(content)
PYTHON
  echo "Criado $ENV_FILE. Senha gerada. Ajuste os serviços externos antes de iniciar."
  exit 0
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Execute scripts/env.sh $ENVIRONMENT init primeiro." >&2
  exit 1
fi
if [[ -f "$ROOT/.releases/$ENVIRONMENT.json" ]] && [[ "$ACTION" == up || "$ACTION" == migrate || "$ACTION" == build ]]; then
  echo 'Este ambiente usa imagens versionadas. Use scripts/release.py para deploy e migrações.' >&2
  exit 1
fi
COMPOSE=(docker compose --project-name "rotasegura-$ENVIRONMENT" --env-file "$ENV_FILE" -f "$ROOT/deploy/compose.yaml")
if [[ "$ENVIRONMENT" == dev ]]; then
  COMPOSE+=(-f "$ROOT/deploy/compose.dev.yaml")
fi
shift 2 || true
case "$ACTION" in
up) "${COMPOSE[@]}" up -d --build "$@" ;;
deps)
  [[ "$ENVIRONMENT" == dev ]] || {
    echo "deps disponível apenas em dev." >&2
    exit 1
  }
  "${COMPOSE[@]}" run --rm --no-deps frontend npm ci "$@"
  ;;
migrate)
  "${COMPOSE[@]}" run --build --rm migrate "$@"
  "${COMPOSE[@]}" exec -T db sh -s <"$ROOT/scripts/provision-db.sh"
  ;;
db-access) "${COMPOSE[@]}" exec -T db sh -s <"$ROOT/scripts/provision-db.sh" ;;
config | build | down | logs | ps) "${COMPOSE[@]}" "$ACTION" "$@" ;;
*)
  echo 'Ação inválida: use init, config, build, up, down, logs, ps, migrate ou deps.' >&2
  exit 1
  ;;
esac
