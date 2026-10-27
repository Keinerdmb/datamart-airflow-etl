"""
DAG: datamart_ecommerce_pipeline
Orquestador diario del pipeline ETL para DataMart S.A.S.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from airflow.hooks.base import BaseHook

# Rutas leídas de variables de Airflow
RAW_DATA_PATH = Variable.get("RAW_DATA_PATH", default_var="/opt/airflow/data/raw")
PROCESSED_DATA_PATH = Variable.get("PROCESSED_DATA_PATH", default_var="/opt/airflow/data/processed")

# Configuración con reintentos automáticos
default_args = {
    "owner": "datamart",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,                           # Reintentos automáticos si alguna tarea falla
    "retry_delay": timedelta(minutes=1),   # 1 minuto de espera entre intentos
}


def _extraer_diario(**context):
    """Extrae las transacciones de ventas diarias y guarda en processed."""
    from scripts.etl_process import extraer_fuente_diaria
    df = extraer_fuente_diaria(ruta_base=RAW_DATA_PATH, limite_filas=25000)
    print(f"Extracción diaria: {len(df)} filas leídas.")


def _extraer_historico(**context):
    """Extrae el historial de transacciones extendido y guarda en processed."""
    from scripts.etl_process import extraer_fuente_historica
    df = extraer_fuente_historica(ruta_base=RAW_DATA_PATH, limite_filas=25000)
    print(f"Extracción histórica: {len(df)} filas leídas.")


def _transformar(**context):
    """Aplica la limpieza y las reglas de negocio sobre las extracciones."""
    from scripts.etl_process import transformar_datos
    transformar_datos()
    print("Transformación completada.")


def _cargar_dw(**context):
    """Carga los datos limpios en PostgreSQL de manera idempotente."""
    from scripts.etl_process import cargar_a_postgres
    
    # Toma la conexión registrada en Airflow (postgres_dw)
    try:
        conn = BaseHook.get_connection("postgres_dw")
        conn_uri = conn.get_uri()
    except Exception:
        import os
        conn_uri = os.getenv("AIRFLOW_CONN_POSTGRES_DW", "postgresql://dw_admin:dw_secret_pass@postgres-dw:5432/datamart_dw")
    
    cargar_a_postgres(connection_url=conn_uri)


def _validar_calidad(**context):
    """Verifica que la carga no haya quedado vacía."""
    from sqlalchemy import create_engine, text
    import os
    try:
        conn = BaseHook.get_connection("postgres_dw")
        conn_uri = conn.get_uri()
    except Exception:
        conn_uri = os.getenv("AIRFLOW_CONN_POSTGRES_DW", "postgresql://dw_admin:dw_secret_pass@postgres-dw:5432/datamart_dw")
    
    if conn_uri.startswith("postgres://"):
        conn_uri = conn_uri.replace("postgres://", "postgresql+psycopg2://", 1)
    elif conn_uri.startswith("postgresql://") and "+psycopg2" not in conn_uri:
        conn_uri = conn_uri.replace("postgresql://", "postgresql+psycopg2://", 1)
        
    engine = create_engine(conn_uri)
    with engine.connect() as connection:
        total_ventas = connection.execute(text("SELECT COUNT(*) FROM fact_ventas;")).scalar()
        
    print(f"Total ventas cargadas: {total_ventas}")
    if total_ventas == 0:
        raise ValueError("Error: fact_ventas no tiene registros.")


with DAG(
    dag_id="datamart_ecommerce_pipeline",
    default_args=default_args,
    description="Pipeline ETL diario de transacciones para DataMart S.A.S.",
    schedule_interval="@daily",
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=["datamart", "etl", "ecommerce"],
) as dag:

    tarea_extraer_diario = PythonOperator(
        task_id="extraer_ventas_diarias",
        python_callable=_extraer_diario,
    )

    tarea_extraer_historico = PythonOperator(
        task_id="extraer_historial_transacciones",
        python_callable=_extraer_historico,
    )

    tarea_transformar = PythonOperator(
        task_id="transformar_y_limpiar_datos",
        python_callable=_transformar,
    )

    tarea_cargar_dw = PythonOperator(
        task_id="cargar_repositorio_analitico",
        python_callable=_cargar_dw,
    )

    tarea_validar_calidad = PythonOperator(
        task_id="validar_calidad_datos",
        python_callable=_validar_calidad,
    )

    # Orden de ejecución de las tareas
    [tarea_extraer_diario, tarea_extraer_historico] >> tarea_transformar >> tarea_cargar_dw >> tarea_validar_calidad
