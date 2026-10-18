#!/usr/bin/env bash
set -euo pipefail

airflow db migrate

if airflow users list --output json | python3 -c \
  'import json, os, sys; users=json.load(sys.stdin); sys.exit(0 if any(user.get("username") == os.environ["AIRFLOW_ADMIN_USERNAME"] for user in users) else 1)'
then
  echo "Airflow administrator already exists."
else
  airflow users create \
    --role Admin \
    --username "$AIRFLOW_ADMIN_USERNAME" \
    --password "$AIRFLOW_ADMIN_PASSWORD" \
    --firstname FlowForge \
    --lastname Admin \
    --email "$AIRFLOW_ADMIN_EMAIL"
fi
