# FlowForge — Real-Time Order Intelligence Platform

FlowForge is an engineering project for building a real-time order intelligence platform that combines operational order management, inventory control, fulfillment workflows, event tracking, change data capture (CDC), streaming, and analytics.

The project is being developed incrementally, starting with a containerized FastAPI and PostgreSQL foundation before expanding toward an event-driven data platform using Kafka, Debezium, Python, Spark, and Airflow.

The primary goal is to demonstrate how a backend operational system can evolve into a reliable, observable, and analytics-ready data platform.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Project Goals](#project-goals)
- [Current Features](#current-features)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [Database Setup](#database-setup)
- [Seed Demo Data](#seed-demo-data)
- [API Reference](#api-reference)
- [Order Lifecycle](#order-lifecycle)
- [Inventory and Fulfillment](#inventory-and-fulfillment)
- [Observability and Health Checks](#observability-and-health-checks)
- [Testing](#testing)
- [Database Migrations](#database-migrations)
- [Configuration and Security](#configuration-and-security)
- [Roadmap](#roadmap)
- [Architecture Documentation](#architecture-documentation)
- [Engineering Principles](#engineering-principles)

---

## Project Overview

Order management systems must coordinate customers, products, warehouses, inventory, reservations, orders, and fulfillment while preserving data consistency.

As transaction volumes grow, operational applications also need reliable mechanisms to capture changes, publish events, and make business data available for analytical processing.

FlowForge explores these challenges through a progressive implementation.

The initial operational platform provides:

- REST APIs for core business entities.
- PostgreSQL-backed persistence.
- Transactional order and inventory workflows.
- Inventory reservation and fulfillment management.
- Order lifecycle events and inventory movement history.
- Dashboard endpoints for operational visibility.
- Docker-based local development.
- Automated tests, request logging, and health checks.

Kafka, Debezium, Spark, and Airflow are planned extensions. They are part of the target architecture, not prerequisites for running the current API.

## Project Goals

### Operational platform

- Build a containerized backend using Docker Compose.
- Develop REST APIs using FastAPI.
- Model operational entities using SQLAlchemy.
- Manage database schema changes using Alembic.
- Maintain consistent order, reservation, and inventory state.
- Track order lifecycle events and stock movements.

### Event-driven architecture

- Introduce change data capture using Debezium.
- Stream database changes through Apache Kafka.
- Design event consumers and processing workflows.
- Explore event delivery, idempotency, ordering, and failure recovery.

### Data engineering and analytics

- Process operational events using Python and Apache Spark.
- Build analytical data models and reporting datasets.
- Orchestrate scheduled workflows using Apache Airflow.
- Develop operational and business intelligence metrics.

### Engineering and operations

- Containerize services.
- Implement automated tests and database migrations.
- Add structured logging, health checks, and configuration validation.
- Document deployment, troubleshooting, and operational procedures.

---

## Current Features

| Area | Capabilities |
|---|---|
| Customers | Customer creation, retrieval, listing, and email validation |
| Product catalog | Products, categories, SKU validation, and pricing |
| Warehouses | Warehouse creation, retrieval, and listing |
| Inventory | Stock receipts, adjustments, transfers, and movement history |
| Reservations | Stock reservation, release, consumption, and expiration processing |
| Orders | Order creation, item snapshots, calculated totals, and status transitions |
| Fulfillment | Order confirmation, cancellation, and shipment workflows |
| Order events | Persisted events for order creation and lifecycle transitions |
| Dashboard | Order summaries, low-stock inventory, and recent stock movements |
| Observability | Request IDs, structured HTTP logs, and request duration |
| Health checks | API liveness and database readiness endpoints |
| Database | PostgreSQL, SQLAlchemy, and Alembic migrations |
| Development | Docker Compose, seed data, and automated tests |

The current platform is an operational backend with event-recording capabilities. A distributed streaming pipeline and analytical processing layer remain planned development work.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application and data engineering language |
| FastAPI | REST API framework |
| Pydantic | Request validation and response schemas |
| SQLAlchemy | ORM and database access |
| PostgreSQL | Operational relational database |
| Alembic | Database schema migrations |
| Docker | Containerized application runtime |
| Docker Compose | Local multi-service orchestration |
| Pytest | Automated testing |
| Apache Kafka | Planned event streaming |
| Debezium | Planned database change data capture |
| Apache Spark | Planned large-scale data processing |
| Apache Airflow | Planned workflow orchestration |

---

## System Architecture

### Current architecture

```text
                    API Clients
                         |
                         v
                +------------------+
                |   FastAPI API    |
                |------------------|
                | Customers        |
                | Catalog          |
                | Warehouses       |
                | Inventory        |
                | Reservations     |
                | Orders           |
                | Fulfillment      |
                | Dashboard        |
                +------------------+
                         |
                         v
                +------------------+
                |   PostgreSQL     |
                |------------------|
                | Customers        |
                | Products         |
                | Warehouses       |
                | Inventory        |
                | Reservations     |
                | Orders           |
                | Order Events     |
                | Stock Movements  |
                +------------------+
```

The API contains separate schema, repository, and service layers. The service layer coordinates business rules and database transactions, while repositories handle persistence operations.

### Target event-driven architecture

```text
        Operational API
               |
               v
          PostgreSQL
               |
               v
       Debezium CDC Connector
               |
               v
        Apache Kafka Topics
               |
          +----+-----+
          |          |
          v          v
     Event Consumers  Data Processing
          |          |
          |          v
          |      Apache Spark
          |          |
          +----+-----+
               |
               v
       Analytical Data Layer
               |
               v
        Reporting and BI

        Apache Airflow
        orchestrates scheduled
        analytical workflows
```

The target architecture will be introduced incrementally. The diagram represents the intended direction rather than a claim that all components are currently deployed.

---

## Repository Structure

```text
flowforge/
├── compose.yml
├── .dockerignore
├── .gitignore
├── pyproject.toml
├── README.md
├── infra/
│   └── docker/
│       └── api.Dockerfile
├── docs/
│   └── database-architecture-plan.pdf
├── migrations/
│   ├── env.py
│   └── versions/
├── scripts/
│   └── seed.py
├── src/
│   └── flowforge/
│       ├── main.py
│       ├── api/
│       │   ├── schemas/
│       │   ├── customers.py
│       │   ├── products.py
│       │   ├── categories.py
│       │   ├── warehouses.py
│       │   ├── inventory.py
│       │   ├── reservations.py
│       │   ├── orders.py
│       │   ├── fulfillment.py
│       │   └── dashboard.py
│       ├── core/
│       │   ├── config.py
│       │   ├── enums.py
│       │   └── observability.py
│       ├── db/
│       │   ├── base.py
│       │   ├── engine.py
│       │   └── session.py
│       ├── models/
│       ├── repositories/
│       └── services/
└── tests/
```

The repository separates API routing, validation schemas, business logic, persistence, and infrastructure concerns.

---

## Getting Started

### Prerequisites

Install the following tools:

- Git
- Python 3.12 or newer
- Docker Engine
- Docker Compose

The Docker API image uses Python 3.12, while local development may use a newer compatible Python version.

### 1. Clone the repository

```bash
git clone https://github.com/yogesh1510-yr/flowforge.git
cd flowforge
```

### 2. Create a Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Upgrade pip and install the project with development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 3. Configure environment variables

Create a local `.env` file in the repository root:

```dotenv
POSTGRES_DB=flowforge
POSTGRES_USER=flowforge
POSTGRES_PASSWORD=flowforge_dev_only
```

These values are for local development only. Use strong, externally managed secrets in deployed environments.

The `.env` file is excluded from Git.

### 4. Start the services

```bash
docker compose up -d --build
```

Check service status:

```bash
docker compose ps
```

The Compose configuration starts PostgreSQL and the API. PostgreSQL has a health check, and API startup waits for the database to become healthy.

The local ports are:

- API: `http://localhost:8000`
- PostgreSQL: `127.0.0.1:5434`

The PostgreSQL container uses a named Docker volume so that ordinary container recreation does not remove persisted data.

### 5. Verify the API

```bash
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
```

Expected responses:

```json
{
  "status": "ok",
  "service": "flowforge-api"
}
```

```json
{
  "status": "ready",
  "database": "connected"
}
```

### 6. Open the API documentation

FastAPI generates interactive API documentation automatically.

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

Use Swagger UI to inspect endpoints, view schemas, and send requests to the running application.

---

## Database Setup

FlowForge uses Alembic to manage database schema changes.

The local PostgreSQL port is `5434`, while services inside the Compose network communicate with PostgreSQL on port `5432`.

Set the database URL in your current shell before running host-side migration commands:

```bash
export DATABASE_URL="postgresql+psycopg://flowforge:flowforge_dev_only@127.0.0.1:5434/flowforge"
```

Apply migrations:

```bash
alembic upgrade head
```

Check whether model definitions and migration metadata are consistent:

```bash
alembic check
```

Inspect the current migration revision:

```bash
alembic current
```

The API container and host-side commands use different database hostnames because they run in different network environments.

---

## Seed Demo Data

The project includes `scripts/seed.py` to populate the database with representative customers, catalog entries, warehouses, inventory, and demo orders.

With PostgreSQL running and `DATABASE_URL` configured in your shell, run:

```bash
python scripts/seed.py
```

The seed script is intended to support repeatable local demonstrations. Review the script before running it against any non-development database.

After seeding, inspect the generated records using the API endpoints and dashboard.

---

## API Reference

The interactive OpenAPI documentation at `/docs` is the authoritative reference for request fields, response schemas, validation rules, and status codes.

### Customers

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/customers` | Create a customer |
| `GET` | `/customers` | List customers |
| `GET` | `/customers/{customer_id}` | Retrieve a customer |

### Product catalog and categories

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/products` | Create a product |
| `GET` | `/products` | List products |
| `GET` | `/products/{product_id}` | Retrieve a product |
| `POST` | `/categories` | Create a category |
| `GET` | `/categories` | List categories |
| `GET` | `/categories/{category_id}` | Retrieve a category |

### Warehouses

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/warehouses` | Create a warehouse |
| `GET` | `/warehouses` | List warehouses |
| `GET` | `/warehouses/{warehouse_id}` | Retrieve a warehouse |

### Inventory

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/inventory` | List inventory |
| `POST` | `/inventory/receipts` | Receive stock |
| `POST` | `/inventory/adjustments` | Adjust stock |
| `POST` | `/inventory/transfers` | Transfer stock |
| `GET` | `/inventory/movements` | Inspect stock movement history |

### Reservations

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/reservations` | Reserve stock |
| `GET` | `/reservations` | List reservations |
| `POST` | `/reservations/{reservation_id}/release` | Release a reservation |
| `POST` | `/reservations/{reservation_id}/consume` | Consume reserved stock |

### Orders and fulfillment

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/orders` | Create an order |
| `GET` | `/orders` | List orders |
| `GET` | `/orders/{order_id}` | Retrieve an order |
| `PATCH` | `/orders/{order_id}/status` | Update an allowed order status |
| `GET` | `/orders/{order_id}/events` | Retrieve order events |
| `POST` | `/fulfillment/{order_id}/confirm` | Confirm an order and reserve stock |
| `POST` | `/fulfillment/{order_id}/cancel` | Cancel an eligible order |
| `POST` | `/fulfillment/{order_id}/ship` | Ship an order and consume reservations |

### Dashboard

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/dashboard/summary` | Order counts and value summaries |
| `GET` | `/dashboard/low-stock` | Inventory with low available quantities |
| `GET` | `/dashboard/recent-movements` | Recent inventory movements |

### Health and diagnostics

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | API liveness |
| `GET` | `/ready` | Database readiness |
| `GET` | `/db-check` | Diagnostic database query |

Check `/docs` for supported query parameters, filters, pagination limits, and request schemas.

---

## Order Lifecycle

A typical order workflow is:

```text
Create Order
     |
     v
   PENDING
     |
     | Confirm order
     v
  CONFIRMED
     |
     | Move to processing
     v
  PROCESSING
     |
     | Ship order
     v
   SHIPPED
     |
     | Mark delivered
     v
  DELIVERED
```

Cancellation is supported for eligible orders before shipment. Confirmation reserves inventory, and shipping consumes the associated reservations and records stock movements.

The service layer enforces allowed transitions rather than relying exclusively on clients to send valid status changes.

---

## Inventory and Fulfillment

Inventory is tracked by product and warehouse.

The system distinguishes:

- **On-hand quantity:** the physical quantity recorded at a warehouse.
- **Reserved quantity:** stock allocated to orders but not yet shipped.
- **Available quantity:** on-hand quantity minus reserved quantity.

The fundamental relationship is:

`available_quantity = on_hand_quantity - reserved_quantity`

Inventory operations maintain stock movement records so that receipts, adjustments, transfers, and dispatches have an associated history.

Order confirmation checks available inventory and creates reservations. Cancellation releases eligible reservations, while shipment consumes reserved quantities and records dispatch movements.

These workflows use database transactions and row-level locking to help preserve consistency when multiple operations compete for stock.

---

## Observability and Health Checks

### Request logging

HTTP requests are logged with structured context, including:

- Request ID
- HTTP method
- Request path
- Response status
- Request duration

The `X-Request-ID` response header helps correlate a client request with application logs.

### Health checks

`/health` reports whether the API is responding.

`/ready` verifies that PostgreSQL can be reached and is used by the Docker health check.

A successful liveness check does not guarantee database availability; readiness provides the additional dependency check.

### Docker logs

Inspect API logs:

```bash
docker compose logs --tail=100 api
```

Follow logs continuously:

```bash
docker compose logs -f api
```

Inspect service health:

```bash
docker compose ps
```

---

## Testing

Run the complete automated test suite:

```bash
python -m pytest -q
```

Run a focused test module:

```bash
python -m pytest tests/test_observability.py -q
```

Check for whitespace errors in tracked changes:

```bash
git diff --check
```

Validate the Compose configuration:

```bash
docker compose config -q
```

Check migration consistency:

```bash
alembic check
```

The test suite covers API behavior, schemas, service logic, database repositories, configuration validation, health checks, request logging, and lifecycle behavior.

Tests that require a real database should be clearly separated from isolated unit tests and run in a deliberately configured integration environment.

---

## Database Migrations

Schema changes should be managed through version-controlled Alembic migrations.

When model changes require a database migration:

1. Update the SQLAlchemy model.
2. Generate a migration for review.
3. Inspect the generated migration operations.
4. Test the migration against a development database.
5. Apply the migration in the intended deployment environment.
6. Verify that the application and database schema agree.

Generate a candidate migration with:

```bash
alembic revision --autogenerate -m "describe schema change"
```

Review the generated file before applying it.

Apply migrations with:

```bash
alembic upgrade head
```

Never assume autogenerated migrations are correct without reviewing their operations and data implications.

---

## Configuration and Security

- Keep `.env` out of version control.
- Never commit passwords, access tokens, or production credentials.
- Use environment-specific secrets for deployed environments.
- Keep `.dockerignore` updated to exclude local environments, Git history, caches, and secrets from the build context.
- Validate configuration before using it to initialize database connections.
- Use explicit database transactions for multi-step business operations.
- Avoid destructive Docker commands that remove persistent volumes unless data deletion is intentional.
- Review dependency upgrades and compatibility warnings before changing the runtime environment.

The credentials shown in local development examples are not suitable for production.

---

## Roadmap

### Phase 1 — Operational foundation

- [x] Containerized FastAPI and PostgreSQL services
- [x] Core customer, catalog, and warehouse APIs
- [x] Inventory and reservation workflows
- [x] Order lifecycle and fulfillment workflows
- [x] Order events and inventory movement history
- [x] Dashboard endpoints
- [x] Automated tests and health checks
- [x] Structured request logging
- [x] Configuration and migration validation

### Phase 2 — Event streaming and CDC

- [ ] Introduce Kafka into the development environment
- [ ] Configure Debezium connectors for PostgreSQL
- [ ] Define event topics and message contracts
- [ ] Validate change capture and event delivery
- [ ] Explore duplicate delivery, ordering, and recovery behavior

### Phase 3 — Stream processing and analytics

- [ ] Build Python event consumers
- [ ] Introduce analytical data models
- [ ] Add Spark processing workflows
- [ ] Develop operational and business metrics
- [ ] Validate data quality and reconciliation

### Phase 4 — Orchestration and production hardening

- [ ] Introduce Airflow orchestration
- [ ] Add scheduled data quality checks
- [ ] Improve metrics, tracing, and alerting
- [ ] Define backup and recovery procedures
- [ ] Add deployment automation and integration environments
- [ ] Document operational service-level objectives

The roadmap describes intended work. Individual milestones should be marked complete only after their implementation and verification.

---

## Architecture Documentation

- [Database Architecture Plan](docs/database-architecture-plan.pdf) — Target database schema, table relationships, architectural decisions, implementation roadmap, and migration checklist.

---

## Engineering Principles

FlowForge is being developed around the following principles:

1. **Correctness before scale:** preserve business invariants and transactional consistency before introducing distributed infrastructure.
2. **Clear separation of concerns:** keep API routing, validation, business logic, persistence, and infrastructure responsibilities distinct.
3. **Observable behavior:** make failures diagnosable through logs, health checks, and request correlation.
4. **Reproducible environments:** use containers, configuration, migrations, and automated tests to make development repeatable.
5. **Explicit data contracts:** define schemas and event contracts before connecting independent services.
6. **Incremental architecture:** introduce streaming and analytical components only when their responsibilities and data flows are well defined.

---

## Project Status

FlowForge currently provides an operational order and inventory API backed by PostgreSQL, with containerized local development, tests, order event records, inventory movement history, and operational dashboard endpoints.

The next architectural step is to connect the operational database to a change-data-capture and event-streaming pipeline, then build analytical processing and orchestration around those events.
