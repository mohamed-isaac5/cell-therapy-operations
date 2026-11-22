#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f gtm.db ] && [ ! -f crm-simulation.db ] && [ ! -f replies-simulation.db ] && [ ! -f operations-local.db ]; then
  python3 bootstrap_demo.py
elif [ ! -f gtm.db ] || [ ! -f crm-simulation.db ] || [ ! -f replies-simulation.db ] || [ ! -f operations-local.db ]; then
  echo 'Partial runtime data found. Stop and inspect the local folder; nothing will be overwritten.' >&2
  exit 1
fi
exec python3 app.py --port "${CGT_PORT:-8080}"
