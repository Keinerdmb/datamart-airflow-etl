# Pipeline ETL con Apache Airflow y Data Warehouse - DataMart S.A.S.

Solución integral de ingeniería de datos para la ingesta, limpieza, enriquecimiento y carga analítica de transacciones de comercio electrónico en PostgreSQL orquestada con Apache Airflow y Docker.

---

## 🚀 Arquitectura del Sistema

- **Apache Airflow 2.8.1 (LocalExecutor):** Orquesta el flujo diario de extracción, transformación, enriquecimiento, carga y validación.
- **PostgreSQL Metadatos (puerto 5432):** Base de datos dedicada para el funcionamiento interno de Airflow.
- **PostgreSQL Data Warehouse (puerto 5433):** Repositorio analítico destino (`datamart_dw`) con esquema estrella inicializado al arrancar (`sql/init_dw.sql`).
- **FastAPI (puerto 8000):** Microservicio REST que expone el catálogo legado de productos (`/products` y `/products/{codigo}`).

---

## 📁 Estructura del Repositorio

```text
├── .env.example              # Plantilla de variables de entorno
├── .gitignore                # Exclusiones de Git (seguridad y temporales)
├── docker-compose.yml        # Orquestación de contenedores
├── api/
│   ├── main.py               # Microservicio FastAPI (catálogo legado)
│   └── Dockerfile            # Imagen del microservicio
├── dags/
│   └── datamart_etl_dag.py   # DAG de Airflow con dependencias explícitas
├── scripts/
│   └── etl_process.py        # Extracción, transformación y carga idempotente
├── sql/
│   ├── init_dw.sql           # DDL de creación de tablas en el Data Warehouse
│   └── queries_negocio.sql   # Consultas que responden las 7 preguntas de negocio
├── data/
│   ├── raw/                  # Datos crudos de Kaggle (data.csv y Sales Transaction)
│   └── processed/            # Almacenamiento intermedio de datos limpios
└── docs/
    ├── DECISIONES.md         # Justificación de diseño, ambigüedades e idempotencia
    └── modelo_datos.md       # Diagrama y descripción del modelo entidad-relación
```

---

## ⚡ Guía de Inicio Rápido (< 3 Minutos)

### 1. Clonar el repositorio
```bash
git clone https://github.com/Keinerdmb/datamart-airflow-etl.git
cd datamart-airflow-etl
```

### 2. Configurar variables de entorno
```bash
cp .env.example .env
```

### 3. Levantar los servicios con Docker Compose
```bash
docker compose up -d
```
*Al ejecutar este comando, Airflow, las dos bases de datos PostgreSQL y la API de productos se inician automáticamente.*

---

## 🌐 Accesos y Credenciales

| Servicio | URL | Credenciales | Descripción |
| :--- | :--- | :--- | :--- |
| **Airflow Webserver** | [http://localhost:8080](http://localhost:8080) | `admin` / `admin` | Monitoreo y ejecución de DAGs |
| **Data Warehouse (PostgreSQL)** | `localhost:5433` | User: `dw_admin` / Pass: `dw_secret_pass` / DB: `datamart_dw` | Base analítica |
| **API de Productos (FastAPI)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Sin autenticación | Swagger / Endpoints catálogo |

---

## 🔍 Validación del Pipeline y Consultas de Negocio

### Ejecutar el pipeline desde Airflow CLI
```bash
docker exec -i datamart-airflow-webserver airflow dags trigger datamart_ecommerce_pipeline
```

### Ejecutar las 7 consultas de negocio contra el Data Warehouse
```bash
docker exec -i datamart-postgres-dw psql -U dw_admin -d datamart_dw -f /docker-entrypoint-initdb.d/../sql/queries_negocio.sql
```
O en PowerShell:
```powershell
Get-Content "sql/queries_negocio.sql" | docker exec -i datamart-postgres-dw psql -U dw_admin -d datamart_dw
```
