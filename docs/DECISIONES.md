# Technical Decisions Document - DataMart S.A.S.

Architectural, modeling, and data-cleansing decisions implemented in the pipeline.

---

## 1. Analytical Repository Design (Data Warehouse)

A simplified **Star Schema** with 5 tables was implemented:

- **`dim_producto`:** Product catalog storing normalized uppercase product codes, canonical product names, and assigned business categories.
- **`dim_cliente`:** Customer dimension tracking registered users and grouping anonymous/guest transactions under the synthetic identifier `'GUEST'` (`es_registrado = FALSE`).
- **`fact_ventas`:** Fact table for valid sales records where quantity and unit price are strictly greater than zero. Contains both `revenue_bruto` and `revenue_neto`.
- **`fact_devoluciones`:** Fact table for adjustments and returns (records with quantity $\le 0$). Stores adjusted revenue and positive return quantities for clear aggregation.
- **`log_rechazos`:** Data quality audit table storing discarded records (e.g., unit price $\le 0$ or corrupted rows), including the exact rejection reason and source identifier.

*Rationale:* Separating sales facts from return facts prevents distorted transaction volume metrics and enables straightforward net revenue calculation without ambiguous boolean flags.

---

## 2. Ambiguity Resolution & Business Rules

### Transactions without Customer ID
- **Decision:** Included under the customer key `'GUEST'` with flag `es_registrado = FALSE`.
- **Rationale:** In e-commerce, guest checkouts represent actual cash receipts. Excluding them would cause monthly financial consolidation reports to understate gross and net revenue relative to bank balances.

### Inconsistent Product Descriptions for a Single Code
- **Decision:** The canonical name in `dim_producto` is calculated using the statistical mode (most frequent uppercase description).
- **Auditability:** The original description string is preserved in the fact tables (`descripcion_original`) to maintain audit trails and allow direct SQL analysis of naming inconsistencies.

### Duplicates and Overlapping Date Ranges between Sources
- **Decision:** Deduplication uses a composite key: `(nro_transaccion, codigo_producto, fecha_transaccion)`. When an identical transaction exists in both files, priority is given to the daily stream (`VENTAS_DIARIAS`) as it originates from the latest operational dump.

### UTC Timestamp Standardization
- **Decision:** All transaction timestamps are normalized to UTC via `pd.to_datetime(..., format="mixed", utc=True)`.
- **Rationale:** DataMart operates across Colombia, Mexico, and Peru (different local timezones). UTC standardization prevents cross-regional timezone mismatch during financial consolidation.

---

## 3. Pipeline Idempotency Guarantee

To ensure executing the DAG multiple times on the same date produces the exact same state without duplicate records:

1. **Dimensions:** Loaded using `ON CONFLICT DO UPDATE` (upsert), ensuring product and customer records are safely refreshed without duplicate primary keys.
2. **Fact Tables:** Existing batch records are cleaned before loading (`TRUNCATE TABLE fact_ventas, fact_devoluciones, log_rechazos CASCADE`), guaranteeing an atomic, consistent reload with zero duplicate rows.
