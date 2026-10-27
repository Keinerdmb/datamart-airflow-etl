# Project Decisions - DataMart S.A.S.

Clear, non-technical explanations of the decisions made while building this data solution.

---

## 1. Database Structure

We chose a simple 5-table layout to keep things clean and easy to query:

- **Products (`dim_producto`):** One row per product code with its cleaned name and category.
- **Customers (`dim_cliente`):** List of customers, noting whether they have an account or shopped as a guest.
- **Sales (`fact_ventas`):** Only real, positive sales ($quantity > 0$ and $price > 0$).
- **Returns (`fact_devoluciones`):** Separated from sales so returns don't hide or confuse real sales numbers.
- **Rejected Records (`log_rechazos`):** Broken rows (like $price \le 0$) saved with the reason why they were excluded, so nothing is lost silently.

---

## 2. Practical Solutions to Data Issues

### Orders without a Customer ID
- **What we did:** Assigned them to a special customer named `'GUEST'`.
- **Why:** In online stores, people often buy without logging in. If we threw these away, our revenue totals wouldn't match bank accounts.

### Products with Different Names for the Same Code
- **What we did:** Picked the most common name (the mode) for the master catalog.
- **Why:** Keeps the catalog tidy while keeping the original description in the sales table for auditing.

### Duplicate Rows Across Files
- **What we did:** Checked uniqueness using `Transaction Number + Product Code + Date`. If a row appeared in both files, we kept the one from daily sales because it's newer.

### Timezones
- **What we did:** Converted all dates to universal time (UTC).
- **Why:** Since sales happen across different countries, using one standard time keeps reports accurate.

---

## 3. Safe Re-Runs (Idempotency)

Running the pipeline twice on the same day will **not duplicate rows**:
- Product and customer tables update existing records instead of inserting duplicates.
- The pipeline clears the previous batch before loading the new one so totals stay 100% correct.
