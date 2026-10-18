FROM apache/airflow:2.10.5-python3.12

ARG AIRFLOW_VERSION=2.10.5
ARG PYTHON_VERSION=3.12
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow
RUN python -m venv /home/airflow/dbt-venv \
    && /home/airflow/dbt-venv/bin/pip install --no-cache-dir \
        "dbt-core>=1.8,<1.10" \
        "dbt-postgres>=1.8,<1.10"
