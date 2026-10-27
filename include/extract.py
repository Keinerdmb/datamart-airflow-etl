"""
Módulo de Extracción - DataMart S.A.S.
Lectura y estandarización de columnas para las dos fuentes de datos.
"""

import os
import pandas as pd

RAW_PATH = os.getenv("AIRFLOW_VAR_RAW_DATA_PATH", "data/raw")
PROCESSED_PATH = os.getenv("AIRFLOW_VAR_PROCESSED_DATA_PATH", "data/processed")


def extraer_fuente_diaria(ruta_base=RAW_PATH, limite_filas=25000):
    """Lee Fuente 1 (data.csv) y estandariza nombres de columna."""
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
    """Lee Fuente 2 (Sales Transaction v.4a.csv) homologando nombres de columna."""
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
