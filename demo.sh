#!/bin/bash
# ==========================================================
# Script de demostración rápida para el evaluador (Linux/Mac)
# ==========================================================

echo "[1/3] Verificando variables de entorno..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Archivo .env creado desde .env.example"
fi

echo "[2/3] Levantando entorno con Docker Compose..."
docker compose up -d

echo "Esperando 10 segundos a que los servicios estén listos..."
sleep 10

echo "[3/3] Ejecutando el DAG en Airflow..."
docker exec -i datamart-airflow-webserver airflow dags trigger datamart_ecommerce_pipeline

echo "Esperando 20 segundos a que finalice la carga de datos..."
sleep 20

echo "=========================================================="
echo "RESULTADOS DE LAS CONSULTAS DE NEGOCIO (POSTGRESQL DW)"
echo "=========================================================="
docker exec -i datamart-postgres-dw psql -U dw_admin -d datamart_dw -c "SELECT TO_CHAR(fecha_transaccion, 'YYYY-MM') AS mes, SUM(revenue_neto) AS revenue_neto, COUNT(DISTINCT nro_transaccion) AS ordenes FROM fact_ventas GROUP BY TO_CHAR(fecha_transaccion, 'YYYY-MM') ORDER BY mes;"

echo ""
echo "Demostración completada con éxito."
echo "Airflow UI: http://localhost:8080 (admin / admin)"
echo "FastAPI:    http://localhost:8000/docs"
