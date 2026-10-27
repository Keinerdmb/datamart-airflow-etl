-- ==========================================================
-- DDL DATA WAREHOUSE - DATAMART S.A.S.
-- ==========================================================

-- Catálogo de productos: código limpio y nombre oficial unificado
CREATE TABLE IF NOT EXISTS dim_producto (
    codigo_producto VARCHAR(50) PRIMARY KEY,
    nombre_canonico VARCHAR(255) NOT NULL,
    categoria VARCHAR(100) NOT NULL DEFAULT 'Otros',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Clientes: compras anónimas quedan agrupadas bajo 'GUEST'
CREATE TABLE IF NOT EXISTS dim_cliente (
    id_cliente VARCHAR(50) PRIMARY KEY,
    es_registrado BOOLEAN NOT NULL DEFAULT TRUE, -- False si compró como invitado
    pais VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ventas válidas: cantidad y precio unitario mayores a cero
CREATE TABLE IF NOT EXISTS fact_ventas (
    id_venta SERIAL PRIMARY KEY,
    nro_transaccion VARCHAR(50) NOT NULL,
    fecha_transaccion TIMESTAMPTZ NOT NULL, -- Siempre en UTC
    codigo_producto VARCHAR(50) REFERENCES dim_producto(codigo_producto),
    descripcion_original VARCHAR(255),      -- Texto original para comparar inconsistencias
    id_cliente VARCHAR(50) REFERENCES dim_cliente(id_cliente),
    pais VARCHAR(100) NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(12, 2) NOT NULL CHECK (precio_unitario > 0),
    revenue_bruto NUMERIC(14, 2) NOT NULL,  -- cantidad * precio
    revenue_neto NUMERIC(14, 2) NOT NULL,   -- bruto menos devoluciones del mismo día
    fuente_origen VARCHAR(50) NOT NULL,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Devoluciones y ajustes: transacciones con cantidad menor o igual a cero
CREATE TABLE IF NOT EXISTS fact_devoluciones (
    id_devolucion SERIAL PRIMARY KEY,
    nro_transaccion VARCHAR(50) NOT NULL,
    fecha_transaccion TIMESTAMPTZ NOT NULL,
    codigo_producto VARCHAR(50) REFERENCES dim_producto(codigo_producto),
    descripcion_original VARCHAR(255),
    id_cliente VARCHAR(50) REFERENCES dim_cliente(id_cliente),
    pais VARCHAR(100) NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0), -- Guardado en positivo para cálculos
    precio_unitario NUMERIC(12, 2) NOT NULL,
    monto_devolucion NUMERIC(14, 2) NOT NULL,
    motivo_ajuste VARCHAR(100) DEFAULT 'DEVOLUCION_O_AJUSTE',
    fuente_origen VARCHAR(50) NOT NULL,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Auditoría: registros con precio <= 0 o datos anómalos
CREATE TABLE IF NOT EXISTS log_rechazos (
    id_rechazo SERIAL PRIMARY KEY,
    nro_transaccion VARCHAR(100),
    codigo_producto VARCHAR(100),
    precio_unitario NUMERIC(12, 2),
    cantidad NUMERIC(12, 2),
    motivo_rechazo VARCHAR(255) NOT NULL,
    fuente_origen VARCHAR(100) NOT NULL,
    payload_original TEXT,
    fecha_rechazo TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para que las consultas analíticas del negocio respondan rápido
CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON fact_ventas(fecha_transaccion);
CREATE INDEX IF NOT EXISTS idx_ventas_prod ON fact_ventas(codigo_producto);
CREATE INDEX IF NOT EXISTS idx_ventas_cliente ON fact_ventas(id_cliente);
CREATE INDEX IF NOT EXISTS idx_devoluciones_fecha ON fact_devoluciones(fecha_transaccion);
CREATE INDEX IF NOT EXISTS idx_devoluciones_prod ON fact_devoluciones(codigo_producto);
