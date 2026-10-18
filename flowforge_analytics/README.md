# FlowForge analytics

This dbt project reads the CDC projection maintained by Spark and builds
analytics models in PostgreSQL.

## Data lineage

```text
public.orders
  -> Debezium -> Kafka flowforge.public.orders
  -> Spark Structured Streaming
  -> analytics.order_state
  -> stg_order_intelligence (view)
  -> fct_orders (incremental table)
  -> agg_orders_by_status (table)
```

The `analytics.order_state` table is created by Alembic migration
`35a4c91f72de`. The Spark projection writer, order-intelligence API, and dbt
source all use this table. `is_deleted` is retained in the fact table so a
soft-delete event can be represented; the aggregate excludes deleted records.

## Run locally

Install the PostgreSQL adapter from the repository root and make sure PostgreSQL
is running with migrations applied:

```bash
python -m pip install -e ".[analytics]"
dbt source freshness --project-dir flowforge_analytics --profiles-dir flowforge_analytics
dbt build --project-dir flowforge_analytics --profiles-dir flowforge_analytics
```

The profile defaults to the local Compose PostgreSQL port and development
credentials. Override `DBT_HOST`, `DBT_PORT`, `DBT_USER`, `DBT_PASSWORD`, and
`DBT_DATABASE` for another environment. The Airflow DAG runs freshness checks and
`dbt build` on an hourly schedule and can also be triggered from the UI.

The freshness threshold warns after 30 minutes and errors after two hours. The
projection reconciliation data test allows five minutes for CDC propagation,
then reports missing, extra, stale, or value-mismatched order rows.
