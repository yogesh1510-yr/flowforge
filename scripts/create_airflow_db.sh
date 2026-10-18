#!/bin/sh
set -eu

if psql -h postgres -U "$POSTGRES_USER" -d postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname = 'flowforge_airflow'" | grep -q 1; then
  echo "Airflow metadata database already exists."
else
  createdb -h postgres -U "$POSTGRES_USER" flowforge_airflow
  echo "Created Airflow metadata database."
fi
