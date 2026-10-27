"""
Pipeline ETL - DataMart S.A.S.
Extracción, transformación con reglas de negocio y carga en PostgreSQL Data Warehouse.
"""

import os
import time
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

# Variables de entorno operativas
RAW_PATH = os.getenv("AIRFLOW_VAR_RAW_DATA_PATH", "data/raw")
PROCESSED_PATH = os.getenv("AIRFLOW_VAR_PROCESSED_DATA_PATH", "data/processed")
DATABASE_URL = os.getenv(
    "AIRFLOW_CONN_POSTGRES_DW",
    "postgresql://dw_admin:dw_secret_pass@localhost:5433/datamart_dw"
)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def extraer_fuente_diaria(ruta_base=RAW_PATH, limite_filas=25000):
    """Extrae la Fuente 1 (data.csv) y estandariza los nombres de columna."""
    archivo = os.path.join(ruta_base, "data.csv")
    print(f"[Extracción] Leyendo Fuente Diaria: {archivo}")
    df = pd.read_csv(archivo, encoding="ISO-8859-1", nrows=limite_filas)
    
    # Homologa columnas al español estándar del proyecto
    df = df.rename(columns={
        "InvoiceNo": "nro_transaccion",
        "StockCode": "codigo_producto",
        "Description": "descripcion_original",
        "Quantity": "cantidad",
        "InvoiceDate": "fecha_transaccion",
        "UnitPrice": "precio_unitario",
        "CustomerID": "id_cliente",
        "Country": "pais"
    })
    df["fuente_origen"] = "VENTAS_DIARIAS"
    
    # Guarda extracción temporal en processed
    os.makedirs(PROCESSED_PATH, exist_ok=True)
    df.to_csv(os.path.join(PROCESSED_PATH, "extraer_diario.csv"), index=False)
    return df


def extraer_fuente_historica(ruta_base=RAW_PATH, limite_filas=25000):
    """Extrae la Fuente 2 (Sales Transaction v.4a.csv) homologando columnas."""
    archivo = os.path.join(ruta_base, "Sales Transaction v.4a.csv")
    print(f"[Extracción] Leyendo Fuente Histórica: {archivo}")
    df = pd.read_csv(archivo, encoding="ISO-8859-1", nrows=limite_filas)
    
    # Estandariza con los mismos nombres de la fuente diaria
    df = df.rename(columns={
        "TransactionNo": "nro_transaccion",
        "ProductNo": "codigo_producto",
        "ProductName": "descripcion_original",
        "Quantity": "cantidad",
        "Date": "fecha_transaccion",
        "Price": "precio_unitario",
        "CustomerNo": "id_cliente",
        "Country": "pais"
    })
    df["fuente_origen"] = "HISTORICO"
    
    # Guarda extracción temporal en processed
    os.makedirs(PROCESSED_PATH, exist_ok=True)
    df.to_csv(os.path.join(PROCESSED_PATH, "extraer_historico.csv"), index=False)
    return df


def consultar_api_producto(codigo):
    """Consulta la categoría en la API REST legacy; si falla, devuelve None."""
    try:
        import urllib.request, json
        api_host = os.getenv("PRODUCTS_API_HOST", "products-api")
        url = f"http://{api_host}:8000/products/{codigo}"
        req = urllib.request.Request(url, headers={"User-Agent": "Airflow-ETL"})
        with urllib.request.urlopen(req, timeout=0.3) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return data.get("categoria")
    except Exception:
        pass
    return None


def asignar_categoria(texto):
    """Clasifica en una de las 5 categorías oficiales de DataMart por palabras clave."""
    if not isinstance(texto, str):
        return "Otros"
    t = texto.upper()
    if any(k in t for k in ["LIGHT", "CANDLE", "HEART", "BOX", "BUSH", "BOTTLE", "CUP", "MUG", "CLOCK", "BOWL", "PLATE", "DOOR"]):
        return "Hogar"
    if any(k in t for k in ["PHONE", "USB", "CABLE", "CAMERA", "BATTERY", "LED", "ALARM"]):
        return "Electrónica"
    if any(k in t for k in ["SHIRT", "COAT", "DRESS", "SCARF", "BAG", "JACKET", "GLOVES", "SOCKS", "T-SHIRT"]):
        return "Ropa"
    if any(k in t for k in ["BALL", "SPORT", "YOGA", "FITNESS", "BIKE", "MAT", "GYM"]):
        return "Deportes"
    if any(k in t for k in ["PEN", "NOTEBOOK", "PAPER", "CARD", "STICKER", "PENCIL", "BOOK"]):
        return "Papelería"
    return "Hogar" # Categoría por defecto al ser tienda de regalos y hogar


def transformar_datos(df_diario=None, df_historico=None):
    """Limpia datos y aplica las reglas de negocio del caso."""
    print("[Transformación] Aplicando reglas de negocio...")
    
    # Si no se pasan los DataFrames, los lee desde la carpeta processed
    if df_diario is None:
        df_diario = pd.read_csv(os.path.join(PROCESSED_PATH, "extraer_diario.csv"))
    if df_historico is None:
        df_historico = pd.read_csv(os.path.join(PROCESSED_PATH, "extraer_historico.csv"))
    
    # Unir ambas fuentes en un único DataFrame
    df = pd.concat([df_diario, df_historico], ignore_index=True)
    
    # Códigos en mayúsculas y sin espacios
    df["codigo_producto"] = df["codigo_producto"].astype(str).str.strip().str.upper()
    
    # Fechas en UTC para sincronizar los diferentes países
    df["fecha_transaccion"] = pd.to_datetime(df["fecha_transaccion"], format="mixed", errors="coerce", utc=True)
    df["fecha_transaccion"] = df["fecha_transaccion"].fillna(pd.Timestamp.now(tz="UTC"))
    
    # Duplicados: da prioridad a la fuente diaria si coincide nro, producto y fecha
    df = df.drop_duplicates(subset=["nro_transaccion", "codigo_producto", "fecha_transaccion"], keep="first")
    
    # Clientes nulos marcados como 'GUEST' para no perder ventas en el balance
    df["id_cliente"] = df["id_cliente"].fillna("GUEST").astype(str).str.replace(".0", "", regex=False).str.strip()
    df.loc[df["id_cliente"].isin(["", "nan", "None", "NULL"]), "id_cliente"] = "GUEST"
    
    # Descripción original limpia para conservar trazabilidad
    df["descripcion_original"] = df["descripcion_original"].fillna("SIN DESCRIPCION").astype(str).str.strip()
    
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0).astype(int)
    df["precio_unitario"] = pd.to_numeric(df["precio_unitario"], errors="coerce").fillna(0.0).astype(float)
    df["pais"] = df["pais"].fillna("Desconocido").astype(str).str.strip()
    
    # Precios <= 0 se mandan al log de rechazos
    mascara_rechazo = (df["precio_unitario"] <= 0)
    df_rechazados = df[mascara_rechazo].copy()
    df_rechazados["motivo_rechazo"] = "PRECIO_UNITARIO_MENOR_O_IGUAL_A_CERO"
    
    df_validos = df[~mascara_rechazo].copy()
    
    # Cantidad <= 0 se separa como devolución
    mascara_devolucion = (df_validos["cantidad"] <= 0)
    
    # Devoluciones (se guarda la cantidad en positivo para cálculo de montos)
    df_devoluciones = df_validos[mascara_devolucion].copy()
    df_devoluciones["cantidad"] = df_devoluciones["cantidad"].abs()
    df_devoluciones.loc[df_devoluciones["cantidad"] == 0, "cantidad"] = 1
    df_devoluciones["monto_devolucion"] = (df_devoluciones["cantidad"] * df_devoluciones["precio_unitario"]).round(2)
    df_devoluciones["motivo_ajuste"] = "DEVOLUCION_O_AJUSTE"
    
    # Ventas válidas normales
    df_ventas = df_validos[~mascara_devolucion].copy()
    df_ventas["revenue_bruto"] = (df_ventas["cantidad"] * df_ventas["precio_unitario"]).round(2)
    
    # Revenue neto: descuenta devoluciones del mismo producto en la misma fecha diaria
    df_ventas["fecha_dia"] = df_ventas["fecha_transaccion"].dt.date
    df_devoluciones["fecha_dia"] = df_devoluciones["fecha_transaccion"].dt.date
    
    dev_dia = df_devoluciones.groupby(["codigo_producto", "fecha_dia"])["monto_devolucion"].sum().reset_index()
    dev_dia = dev_dia.rename(columns={"monto_devolucion": "total_dev_dia"})
    
    df_ventas = df_ventas.merge(dev_dia, on=["codigo_producto", "fecha_dia"], how="left")
    df_ventas["total_dev_dia"] = df_ventas["total_dev_dia"].fillna(0.0)
    df_ventas["revenue_neto"] = np.maximum(0.0, df_ventas["revenue_bruto"] - df_ventas["total_dev_dia"]).round(2)
    
    df_ventas = df_ventas.drop(columns=["fecha_dia", "total_dev_dia"])
    df_devoluciones = df_devoluciones.drop(columns=["fecha_dia"])
    
    # Nombre canónico: toma la descripción más repetida en mayúsculas
    nombres_canonicos = (
        df.groupby("codigo_producto")["descripcion_original"]
        .agg(lambda s: s.str.upper().mode().iloc[0] if not s.empty else "PRODUCTO GENERAL")
        .reset_index()
        .rename(columns={"descripcion_original": "nombre_canonico"})
    )
    # Enriquecimiento: primero intenta consultar la API legacy, si no responde usa palabras clave
    def clasificar_con_api(row):
        cat = consultar_api_producto(row["codigo_producto"])
        return cat if cat else asignar_categoria(row["nombre_canonico"])

    nombres_canonicos["categoria"] = nombres_canonicos.apply(clasificar_con_api, axis=1)
    df_dim_producto = nombres_canonicos
    
    # Dimensión cliente: marca si es usuario registrado o GUEST
    df_dim_cliente = df.groupby("id_cliente").agg({"pais": "first"}).reset_index()
    df_dim_cliente["es_registrado"] = df_dim_cliente["id_cliente"] != "GUEST"
    
    # Guarda datasets limpios en processed para la tarea de carga
    df_dim_producto.to_csv(os.path.join(PROCESSED_PATH, "dim_producto.csv"), index=False)
    df_dim_cliente.to_csv(os.path.join(PROCESSED_PATH, "dim_cliente.csv"), index=False)
    df_ventas.to_csv(os.path.join(PROCESSED_PATH, "fact_ventas.csv"), index=False)
    df_devoluciones.to_csv(os.path.join(PROCESSED_PATH, "fact_devoluciones.csv"), index=False)
    df_rechazados.to_csv(os.path.join(PROCESSED_PATH, "log_rechazos.csv"), index=False)
    
    return {
        "dim_producto": df_dim_producto,
        "dim_cliente": df_dim_cliente,
        "fact_ventas": df_ventas,
        "fact_devoluciones": df_devoluciones,
        "log_rechazos": df_rechazados
    }


def cargar_a_postgres(datos_transformados=None, connection_url=DATABASE_URL):
    """Carga los datos en el Data Warehouse de manera idempotente."""
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


def ejecutar_pipeline_completo(limite_demo=25000):
    """Ejecuta el flujo completo. Con 25,000 filas corre en ~15 segundos."""
    t0 = time.time()
    df_diario = extraer_fuente_diaria(limite_filas=limite_demo)
    df_hist = extraer_fuente_historica(limite_filas=limite_demo)
    datos = transformar_datos(df_diario, df_hist)
    cargar_a_postgres(datos)
    print(f"Pipeline completado en {time.time() - t0:.2f} segundos.")


if __name__ == "__main__":
    ejecutar_pipeline_completo(limite_demo=25000)
