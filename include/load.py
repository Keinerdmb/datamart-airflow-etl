"""
Módulo de Carga - DataMart S.A.S.
Inserción de datos transformados en el Data Warehouse PostgreSQL garantizando idempotencia.
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text

PROCESSED_PATH = os.getenv("AIRFLOW_VAR_PROCESSED_DATA_PATH", "data/processed")
DATABASE_URL = os.getenv(
    "AIRFLOW_CONN_POSTGRES_DW",
    "postgresql://dw_admin:dw_secret_pass@localhost:5433/datamart_dw"
)


def cargar_a_postgres(datos_transformados=None, connection_url=DATABASE_URL):
    """Carga los datos en el Data Warehouse de manera idempotente."""
    # Corrige dialecto para compatibilidad con SQLAlchemy
    if connection_url.startswith("postgres://"):
        connection_url = connection_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif connection_url.startswith("postgresql://") and "+psycopg2" not in connection_url:
        connection_url = connection_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    print(f"[Carga] Sincronizando con Data Warehouse: {connection_url.split('@')[-1]}")
    
    if datos_transformados is None:
        datos_transformados = {
            "dim_producto": pd.read_csv(os.path.join(PROCESSED_PATH, "dim_producto.csv")),
            "dim_cliente": pd.read_csv(os.path.join(PROCESSED_PATH, "dim_cliente.csv")),
            "fact_ventas": pd.read_csv(os.path.join(PROCESSED_PATH, "fact_ventas.csv")),
            "fact_devoluciones": pd.read_csv(os.path.join(PROCESSED_PATH, "fact_devoluciones.csv")),
            "log_rechazos": pd.read_csv(os.path.join(PROCESSED_PATH, "log_rechazos.csv")),
        }
        
    engine = create_engine(connection_url)
    
    with engine.begin() as conn:
        # Upsert de dimensiones (evita duplicar productos y clientes)
        datos_transformados["dim_producto"].to_sql("temp_dim_producto", conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT INTO dim_producto (codigo_producto, nombre_canonico, categoria)
            SELECT codigo_producto, nombre_canonico, categoria FROM temp_dim_producto
            ON CONFLICT (codigo_producto) DO UPDATE
            SET nombre_canonico = EXCLUDED.nombre_canonico,
                categoria = EXCLUDED.categoria;
            DROP TABLE IF EXISTS temp_dim_producto;
        """))

        datos_transformados["dim_cliente"].to_sql("temp_dim_cliente", conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT INTO dim_cliente (id_cliente, es_registrado, pais)
            SELECT id_cliente, es_registrado, pais FROM temp_dim_cliente
            ON CONFLICT (id_cliente) DO UPDATE
            SET es_registrado = EXCLUDED.es_registrado,
                pais = EXCLUDED.pais;
            DROP TABLE IF EXISTS temp_dim_cliente;
        """))

        # Idempotencia: limpia los hechos antes de insertar para no duplicar si corre 2 veces
        conn.execute(text("TRUNCATE TABLE fact_ventas, fact_devoluciones, log_rechazos RESTART IDENTITY CASCADE;"))
        
        # Inserción por lotes para que cargue rápido
        cols_ventas = [
            "nro_transaccion", "fecha_transaccion", "codigo_producto", "descripcion_original",
            "id_cliente", "pais", "cantidad", "precio_unitario", "revenue_bruto", "revenue_neto", "fuente_origen"
        ]
        datos_transformados["fact_ventas"][cols_ventas].to_sql(
            "fact_ventas", conn, if_exists="append", index=False, chunksize=10000, method="multi"
        )

        cols_dev = [
            "nro_transaccion", "fecha_transaccion", "codigo_producto", "descripcion_original",
            "id_cliente", "pais", "cantidad", "precio_unitario", "monto_devolucion", "motivo_ajuste", "fuente_origen"
        ]
        datos_transformados["fact_devoluciones"][cols_dev].to_sql(
            "fact_devoluciones", conn, if_exists="append", index=False, chunksize=10000, method="multi"
        )

        cols_rechazos = [
            "nro_transaccion", "codigo_producto", "precio_unitario", "cantidad",
            "motivo_rechazo", "fuente_origen"
        ]
        datos_transformados["log_rechazos"][cols_rechazos].to_sql(
            "log_rechazos", conn, if_exists="append", index=False, chunksize=10000, method="multi"
        )

    print("✓ [Carga] Datos sincronizados exitosamente en PostgreSQL.")
