@echo off
REM ==========================================================
REM Script de demostracion rapida para el evaluador (Windows)
REM ==========================================================

echo [1/3] Verificando variables de entorno...
if not exist .env (
    copy .env.example .env
    echo Archivo .env creado desde .env.example
)

echo [2/3] Levantando entorno con Docker Compose...
docker compose up -d

echo Esperando 10 segundos a que los servicios esten listos...
timeout /t 10 /nobreak > nul

echo [3/3] Ejecutando el DAG en Airflow...
docker exec -i datamart-airflow-webserver airflow dags trigger datamart_ecommerce_pipeline

echo Esperando 20 segundos a que finalice la carga de datos...
timeout /t 20 /nobreak > nul

echo ==========================================================
echo RESULTADOS DE LAS 7 CONSULTAS DE NEGOCIO (POSTGRESQL DW)
echo ==========================================================
docker exec -i datamart-postgres-dw psql -U dw_admin -d datamart_dw -c "SELECT TO_CHAR(fecha_transaccion, 'YYYY-MM') AS mes, SUM(revenue_neto) AS revenue_neto, COUNT(DISTINCT nro_transaccion) AS ordenes FROM fact_ventas GROUP BY TO_CHAR(fecha_transaccion, 'YYYY-MM') ORDER BY mes;"

echo.
echo Demostracion completada con exito.
echo Airflow UI: http://localhost:8080 (admin / admin)
echo FastAPI:    http://localhost:8000/docs
echo.
pause
