"""
Script de demostracion automatizada para la prueba de DataMart S.A.S.
Funciona en Windows, Linux y macOS. Ejecutable con doble clic o con 'python run_demo.py'.
"""

import os
import shutil
import subprocess
import sys
import time

def main():
    print("=" * 60)
    print(" DEMOSTRACION AUTOMATICA - DATAMART S.A.S.")
    print("=" * 60)

    # 1. Variables de entorno
    print("\n[1/3] Verificando variables de entorno...")
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            shutil.copy(".env.example", ".env")
            print(" -> Archivo .env creado exitosamente desde .env.example")
        else:
            print(" -> Advertencia: No se encontro .env.example, continuando...")
    else:
        print(" -> Archivo .env verificado.")

    # 2. Docker Compose
    print("\n[2/3] Levantando servicios con Docker Compose...")
    try:
        subprocess.run(["docker", "compose", "up", "-d"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error al iniciar contenedores Docker: {e}")
        input("\nPresiona Enter para salir...")
        sys.exit(1)

    print(" -> Esperando 10 segundos a que los servicios esten listos...")
    time.sleep(10)

    # 3. Disparar el DAG en Airflow
    print("\n[3/3] Disparando el DAG 'datamart_ecommerce_pipeline' en Airflow...")
    try:
        subprocess.run(
            ["docker", "exec", "-i", "datamart-airflow-webserver", "airflow", "dags", "trigger", "datamart_ecommerce_pipeline"],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error al disparar el DAG: {e}")
        input("\nPresiona Enter para salir...")
        sys.exit(1)

    print(" -> Esperando 20 segundos a que finalice la ejecucion del pipeline...")
    time.sleep(20)

    # 4. Mostrar resultados de negocio
    print("\n" + "=" * 60)
    print(" RESULTADOS DE LAS 7 CONSULTAS DE NEGOCIO (POSTGRESQL DW)")
    print("=" * 60 + "\n")

    queries_path = os.path.join("sql", "queries_negocio.sql")
    if os.path.exists(queries_path):
        with open(queries_path, "r", encoding="utf-8") as f:
            subprocess.run(
                ["docker", "exec", "-i", "datamart-postgres-dw", "psql", "-U", "dw_admin", "-d", "datamart_dw"],
                stdin=f
            )
    else:
        print("No se encontro el archivo sql/queries_negocio.sql")

    print("\n" + "=" * 60)
    print(" DEMOSTRACION COMPLETADA CON EXITO")
    print("=" * 60)
    print(" * Airflow UI: http://localhost:8080 (admin / admin)")
    print(" * FastAPI:    http://localhost:8000/docs")
    print("=" * 60)
    
    # Mantiene la ventana abierta si se ejecuta con doble clic
    input("\nPresiona Enter para cerrar esta ventana...")

if __name__ == "__main__":
    main()
