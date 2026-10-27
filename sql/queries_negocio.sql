-- ==========================================================
-- CONSULTAS DE NEGOCIO - DATAMART S.A.S.
-- ==========================================================

-- 1. Evolución mensual: ventas netas (bruto menos devoluciones del mes)
SELECT 
    TO_CHAR(fecha_transaccion, 'YYYY-MM') AS mes,
    SUM(revenue_bruto) AS revenue_bruto,
    SUM(revenue_neto) AS revenue_neto,
    COUNT(DISTINCT nro_transaccion) AS total_ordenes
FROM fact_ventas
GROUP BY TO_CHAR(fecha_transaccion, 'YYYY-MM')
ORDER BY mes ASC;


-- 2. Categorías: compara revenue bruto y porcentaje de devoluciones
WITH ventas_cat AS (
    SELECT 
        p.categoria,
        SUM(v.revenue_bruto) AS revenue_bruto
    FROM fact_ventas v
    JOIN dim_producto p ON v.codigo_producto = p.codigo_producto
    GROUP BY p.categoria
),
devoluciones_cat AS (
    SELECT 
        p.categoria,
        SUM(d.monto_devolucion) AS monto_devuelto
    FROM fact_devoluciones d
    JOIN dim_producto p ON d.codigo_producto = p.codigo_producto
    GROUP BY p.categoria
)
SELECT 
    vc.categoria,
    ROUND(vc.revenue_bruto, 2) AS revenue_bruto,
    COALESCE(ROUND(dc.monto_devuelto, 2), 0) AS monto_devoluciones,
    ROUND((COALESCE(dc.monto_devuelto, 0) / NULLIF(vc.revenue_bruto, 0)) * 100, 2) AS pct_devolucion
FROM ventas_cat vc
LEFT JOIN devoluciones_cat dc ON vc.categoria = dc.categoria
ORDER BY revenue_bruto DESC;


-- 3. Top 10 productos: por revenue neto y por tasa de devolución
-- Top 10 mayor revenue neto
SELECT 
    p.codigo_producto,
    p.nombre_canonico,
    SUM(v.revenue_neto) AS revenue_neto
FROM fact_ventas v
JOIN dim_producto p ON v.codigo_producto = p.codigo_producto
GROUP BY p.codigo_producto, p.nombre_canonico
ORDER BY revenue_neto DESC
LIMIT 10;

-- Top 10 mayor tasa de devolución (% unidades devueltas vs vendidas)
WITH prod_ventas AS (
    SELECT codigo_producto, SUM(cantidad) AS unidades_vendidas
    FROM fact_ventas
    GROUP BY codigo_producto
),
prod_dev AS (
    SELECT codigo_producto, SUM(cantidad) AS unidades_devueltas
    FROM fact_devoluciones
    GROUP BY codigo_producto
)
SELECT 
    p.codigo_producto,
    p.nombre_canonico,
    pv.unidades_vendidas,
    COALESCE(pd.unidades_devueltas, 0) AS unidades_devueltas,
    ROUND((COALESCE(pd.unidades_devueltas, 0)::numeric / NULLIF(pv.unidades_vendidas, 0)) * 100, 2) AS tasa_devolucion_pct
FROM prod_ventas pv
JOIN dim_producto p ON pv.codigo_producto = p.codigo_producto
LEFT JOIN prod_dev pd ON pv.codigo_producto = pd.codigo_producto
WHERE pv.unidades_vendidas >= 50 -- Filtro de volumen mínimo
ORDER BY tasa_devolucion_pct DESC
LIMIT 10;


-- 4. Países: volumen de órdenes y ticket promedio por país
SELECT 
    pais,
    COUNT(DISTINCT nro_transaccion) AS total_transacciones,
    ROUND(SUM(revenue_bruto), 2) AS total_ventas,
    ROUND(SUM(revenue_bruto) / COUNT(DISTINCT nro_transaccion), 2) AS ticket_promedio
FROM fact_ventas
GROUP BY pais
ORDER BY total_transacciones DESC
LIMIT 10;


-- 5. Clientes: comportamiento entre identificados vs compras anónimas (GUEST)
SELECT 
    c.es_registrado,
    CASE WHEN c.es_registrado THEN 'Registrado' ELSE 'Invitado (GUEST)' END AS tipo_cliente,
    COUNT(DISTINCT v.nro_transaccion) AS ordenes,
    ROUND(SUM(v.revenue_bruto), 2) AS total_revenue,
    ROUND(SUM(v.revenue_bruto) / COUNT(DISTINCT v.nro_transaccion), 2) AS ticket_promedio
FROM fact_ventas v
JOIN dim_cliente c ON v.id_cliente = c.id_cliente
GROUP BY c.es_registrado;


-- 6. Inconsistencias: productos con más de una variante de nombre
-- Conteo de productos únicos en el catálogo
SELECT COUNT(DISTINCT codigo_producto) AS total_productos_unicos FROM dim_producto;

-- Productos con múltiples descripciones en las transacciones
SELECT 
    codigo_producto,
    COUNT(DISTINCT descripcion_original) AS total_variantes,
    STRING_AGG(DISTINCT descripcion_original, ' | ') AS nombres_encontrados
FROM fact_ventas
GROUP BY codigo_producto
HAVING COUNT(DISTINCT descripcion_original) > 1
ORDER BY total_variantes DESC
LIMIT 10;


-- 7. Recomendación: productos con alta venta pero devolución crítica (>10%)
WITH metricas AS (
    SELECT 
        p.codigo_producto,
        p.nombre_canonico,
        p.categoria,
        SUM(v.revenue_bruto) AS revenue_bruto,
        SUM(v.cantidad) AS vendidas
    FROM fact_ventas v
    JOIN dim_producto p ON v.codigo_producto = p.codigo_producto
    GROUP BY p.codigo_producto, p.nombre_canonico, p.categoria
),
devoluciones AS (
    SELECT 
        codigo_producto,
        SUM(monto_devolucion) AS dinero_perdido,
        SUM(cantidad) AS devueltas
    FROM fact_devoluciones
    GROUP BY codigo_producto
)
SELECT 
    m.codigo_producto,
    m.nombre_canonico,
    m.categoria,
    m.vendidas,
    COALESCE(d.devueltas, 0) AS devueltas,
    ROUND((COALESCE(d.devueltas, 0)::numeric / NULLIF(m.vendidas, 0)) * 100, 2) AS pct_devolucion,
    COALESCE(ROUND(d.dinero_perdido, 2), 0) AS impacto_economico
FROM metricas m
LEFT JOIN devoluciones d ON m.codigo_producto = d.codigo_producto
WHERE m.vendidas >= 30 AND (COALESCE(d.devueltas, 0)::numeric / NULLIF(m.vendidas, 0)) > 0.10
ORDER BY impacto_economico DESC
LIMIT 5;
