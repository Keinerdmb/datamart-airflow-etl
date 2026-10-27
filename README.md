# ETL Pipeline with Apache Airflow and Data Warehouse - DataMart S.A.S.

End-to-end data engineering solution for ingestion, cleansing, enrichment, and analytical loading of e-commerce transactions into PostgreSQL, orchestrated with Apache Airflow and Docker.

---

## 🚀 System Architecture

- **Apache Airflow 2.8.1 (LocalExecutor):** Orchestrates the daily pipeline stages: extraction, transformation, enrichment, idempotent loading, and quality validation.
- **PostgreSQL Airflow Metadata (Port 5432):** Dedicated internal database for Airflow scheduler and webserver state.
- **PostgreSQL Analytical Data Warehouse (Port 5433):** Star schema analytical repository (`datamart_dw`) initialized automatically on startup (`sql/init_dw.sql`).
- **FastAPI Product Catalog API (Port 8000):** Lightweight REST microservice serving the legacy product catalog (`/products` and `/products/{code}`).

---

## 📁 Repository Structure

```text
├── .env.example              # Environment variables template
├── .gitignore                # Git exclusion rules (credentials and temporary files)
├── docker-compose.yml        # Multi-container orchestration definition
├── api/
│   ├── main.py               # FastAPI microservice (legacy product catalog)
│   └── Dockerfile            # Container image build instructions
├── dags/
│   └── datamart_etl_dag.py   # Airflow DAG definition with explicit task dependencies
├── scripts/
│   └── etl_process.py        # Core ETL logic (extraction, cleaning, business rules, loading)
├── sql/
│   ├── init_dw.sql           # Data Warehouse DDL schema definition
│   └── queries_negocio.sql   # SQL analytical queries answering business questions
├── data/
│   ├── raw/                  # Raw input datasets (data.csv and Sales Transaction)
│   └── processed/            # Staging directory for intermediate cleaned datasets
└── docs/
    ├── DECISIONES.md         # Technical decisions, ambiguity resolution, and idempotency
    └── modelo_datos.md       # Data model entity-relationship diagram and documentation
```

---

## ⚡ Quick Start Guide (< 3 Minutes)

### 1. Clone the repository
```bash
git clone https://github.com/Keinerdmb/datamart-airflow-etl.git
cd datamart-airflow-etl
```

### 2. Configure environment variables
```bash
cp .env.example .env
```

### 3. Start all services with Docker Compose
```bash
docker compose up -d
```
*All services (Airflow Webserver, Scheduler, both PostgreSQL databases, and the FastAPI service) start and configure automatically without manual intervention.*

---

## 🌐 Endpoints & Credentials

| Service | Access URL | Credentials | Purpose |
| :--- | :--- | :--- | :--- |
| **Airflow UI** | [http://localhost:8080](http://localhost:8080) | `admin` / `admin` | DAG orchestration and monitoring |
| **Data Warehouse (PostgreSQL)** | `localhost:5433` | User: `dw_admin` / Pass: `dw_secret_pass` / DB: `datamart_dw` | Analytical database |
| **Products API (FastAPI)** | [http://localhost:8000/docs](http://localhost:8000/docs) | None (Public) | Interactive Swagger API docs |

---

## 🔍 Pipeline Verification & Business Analytics

### Trigger DAG via Airflow CLI
```bash
docker exec -i datamart-airflow-webserver airflow dags trigger datamart_ecommerce_pipeline
```

### Execute the 7 analytical business queries against the Data Warehouse
```bash
# In Linux/macOS bash:
docker exec -i datamart-postgres-dw psql -U dw_admin -d datamart_dw -f /docker-entrypoint-initdb.d/../sql/queries_negocio.sql

# In Windows PowerShell:
Get-Content "sql/queries_negocio.sql" | docker exec -i datamart-postgres-dw psql -U dw_admin -d datamart_dw
```
