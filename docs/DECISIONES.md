# Documento de Decisiones Técnicas - DataMart S.A.S.

Breve justificación de las decisiones de arquitectura, modelado y limpieza de datos tomadas en la solución.

---

## 1. Diseño del Repositorio Analítico (Data Warehouse)

Se adoptó un **esquema estrella** simplificado de 5 tablas:

- **`dim_producto`:** Almacena el catálogo de productos con código normalizado en mayúsculas, nombre canónico oficial y su categoría.
- **`dim_cliente`:** Registra clientes identificados y clasifica a las compras anónimas con el identificador especial `'GUEST'` (`es_registrado = FALSE`).
- **`fact_ventas`:** Hechos de ventas válidas con cantidades y precios estrictamente mayores a cero. Contiene tanto `revenue_bruto` como `revenue_neto`.
- **`fact_devoluciones`:** Hechos de transacciones con cantidades menores o iguales a cero. Registra el monto ajustado y la cantidad devuelta en valor positivo.
- **`log_rechazos`:** Tabla de auditoría donde se aíslan registros corruptos o ventas con precios menores o iguales a cero, guardando el motivo de rechazo y la fuente de origen.

*Justificación:* Separar hechos de ventas de devoluciones previene distorsiones en los cálculos de volumen transaccional y facilita calcular el revenue neto de forma directa y transparente.

---

## 2. Resolución de Casos Ambiguos

### Transacciones sin Customer ID
- **Decisión:** Se incluyen asignándoles el identificador `'GUEST'` y marcando `es_registrado = FALSE`.
- **Motivo:** En comercio electrónico, las compras como invitado representan ingresos financieros reales. Descartarlas provocaría que los cierres contables mensuales no cuadren con los ingresos bancarios.

### Descripciones inconsistentes de un mismo producto
- **Decisión:** Se calcula el nombre canónico oficial en `dim_producto` tomando la moda (el valor más frecuente) en mayúsculas.
- **Trazabilidad:** Se conserva la columna `descripcion_original` en las tablas de hechos para auditar la variabilidad y permitir responder consultas de inconsistencia léxica.

### Duplicados y solapamiento entre fuentes
- **Decisión:** Se utiliza la clave compuesta `(nro_transaccion, codigo_producto, fecha_transaccion)`. Si un registro existe en ambas fuentes, se prioriza la fuente de ventas diarias (`VENTAS_DIARIAS`) por ser el volcado operacional más reciente.

### Normalización de Fechas a UTC
- **Decisión:** Todas las marcas temporales se convierten a UTC usando `pd.to_datetime(..., format="mixed", utc=True)`.
- **Motivo:** DataMart opera en Colombia, México y Perú (diferentes zonas horarias). La unificación a UTC garantiza cierres mensuales consolidados sin desfases horarios.

---

## 3. Garantía de Idempotencia del Pipeline

Para asegurar que ejecutar el DAG varias veces el mismo día produzca exactamente el mismo resultado:

1. **Dimensiones:** Se utiliza la cláusula `ON CONFLICT DO UPDATE` (upsert), actualizando descripciones o categorías sin generar duplicados.
2. **Hechos:** Antes de insertar los registros del lote, se limpian las tablas de hechos (`TRUNCATE TABLE fact_ventas, fact_devoluciones, log_rechazos CASCADE`), garantizando una recarga atómica y consistente sin duplicidad de datos.
