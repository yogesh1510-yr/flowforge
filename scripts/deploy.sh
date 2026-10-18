#!/usr/bin/env bash
set -euo pipefail

environment="${1:-}"
case "$environment" in
  dev|non-prod|prod) ;;
  *)
    echo "Usage: $0 {dev|non-prod|prod}" >&2
    exit 2
    ;;
esac

if [[ ! -f .env ]]; then
  echo "A host-managed .env file is required beside compose.yml." >&2
  exit 1
fi

python3 - "$environment" <<'PY'
from pathlib import Path
import sys

selected_environment = sys.argv[1]
values = {}
for raw_line in Path(".env").read_text().splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    values[key.strip()] = value.strip().strip("\"'")

if values.get("FLOWFORGE_ENV") != selected_environment:
    raise SystemExit(
        f".env FLOWFORGE_ENV must be set to {selected_environment!r} "
        "to match the selected GitHub Environment."
    )

for name in ("POSTGRES_PASSWORD", "AIRFLOW_ADMIN_PASSWORD"):
    value = values.get(name, "")
    if len(value) < 24 or value in {"flowforge_dev_only", "flowforge_admin_only"}:
        raise SystemExit(
            f"Set {name} in the host-managed .env to a unique value "
            "of at least 24 characters."
        )
PY

compose=(docker compose --env-file .env --project-name "flowforge-$environment" -f compose.yml)
FLOWFORGE_ENV="$environment" "${compose[@]}" up -d --build --remove-orphans

for attempt in $(seq 1 60); do
  if "${compose[@]}" exec -T api python -c \
    'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/ready", timeout=3)' \
    >/dev/null 2>&1; then
    echo "FlowForge is ready in $environment."
    exit 0
  fi
  sleep 5
done

"${compose[@]}" ps
echo "FlowForge did not become ready within five minutes." >&2
exit 1
