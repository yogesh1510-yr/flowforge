"""Build the FlowForge dbt models on a regular schedule."""

from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.operators.bash import BashOperator


with DAG(
    dag_id="flowforge_analytics",
    description="Build and test the FlowForge analytics models with dbt",
    start_date=datetime(2026, 10, 18, tzinfo=timezone.utc),
    schedule="@hourly",
    catchup=False,
    default_args={
        "owner": "flowforge",
        "retries": 1,
        "retry_delay": timedelta(minutes=2),
    },
    tags=["flowforge", "dbt"],
) as dag:
    check_source_freshness = BashOperator(
        task_id="dbt_source_freshness",
        bash_command=(
            "/home/airflow/dbt-venv/bin/dbt source freshness "
            "--project-dir /opt/airflow/flowforge_analytics "
            "--profiles-dir /opt/airflow/flowforge_analytics"
        ),
    )
    build_and_test_models = BashOperator(
        task_id="dbt_build",
        bash_command=(
            "/home/airflow/dbt-venv/bin/dbt build "
            "--project-dir /opt/airflow/flowforge_analytics "
            "--profiles-dir /opt/airflow/flowforge_analytics"
        ),
    )
    check_source_freshness >> build_and_test_models
