# Data Model Guide - DataMart S.A.S.

A visual guide to how the tables are connected and what each table stores.

---

## Diagram

```mermaid
erDiagram
    dim_producto ||--o{ fact_ventas : "codigo_producto"
    dim_producto ||--o{ fact_devoluciones : "codigo_producto"
    dim_cliente ||--o{ fact_ventas : "id_cliente"
    dim_cliente ||--o{ fact_devoluciones : "id_cliente"

    dim_producto {
        varchar codigo_producto PK "Product code"
        varchar nombre_canonico "Clean name"
        varchar categoria "Category"
    }

    dim_cliente {
        varchar id_cliente PK "Customer ID or GUEST"
        boolean es_registrado "Has an account (Yes/No)"
        varchar pais "Country"
    }

    fact_ventas {
        serial id_venta PK "Auto ID"
        varchar nro_transaccion "Invoice number"
        timestamptz fecha_transaccion "Date and time"
        varchar codigo_producto FK "Product"
        varchar id_cliente FK "Customer"
        integer cantidad "Units sold"
        numeric precio_unitario "Unit price"
        numeric revenue_bruto "Total amount"
        numeric revenue_neto "Net amount"
    }

    fact_devoluciones {
        serial id_devolucion PK "Auto ID"
        varchar nro_transaccion "Invoice number"
        timestamptz fecha_transaccion "Date and time"
        varchar codigo_producto FK "Product"
        varchar id_cliente FK "Customer"
        integer cantidad "Units returned"
        numeric monto_devolucion "Refund value"
    }

    log_rechazos {
        serial id_rechazo PK "Auto ID"
        varchar nro_transaccion "Invoice number"
        varchar motivo_rechazo "Why it was skipped"
    }
```

---

## What Each Table Is For

1. **`dim_producto` (Products):** Central list of products, standardized names, and categories.
2. **`dim_cliente` (Customers):** Distinguishes registered shoppers from guest orders (`GUEST`).
3. **`fact_ventas` (Sales):** Records every completed order with quantities and prices.
4. **`fact_devoluciones` (Returns):** Tracks returned units and refund totals separately from sales.
5. **`log_rechazos` (Audit Log):** Keeps track of bad records (like $0 price) so you can review what went wrong and why.
