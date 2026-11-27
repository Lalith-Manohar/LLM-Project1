> [!CAUTION]
> ## SUPERSEDED HISTORICAL DRAFT — DO NOT USE FOR IMPLEMENTATION
>
> **Status:** **SUPERSEDED HISTORICAL DRAFT** (retained exclusively for historical/reference purposes).
>
> - **Not Authoritative:** This document is **NOT** the current NEXORA database specification and **MUST NOT** be used as the source of truth for implementation, database migrations, SQLAlchemy ORM models, API integration, or application development.
> - **Potential Conflicts:** Its proposed schema, table definitions, authentication model, roles, relationships, and field names may conflict with the approved NEXORA architecture.
> - **Authoritative Replacement:** Refer exclusively to **[docs/DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** (**Version 2.9 — ML and Operational Data Integrity**).
>
> ### Key Historical Distinctions (Examples of Superseded Content)
> The historical draft below dates from an early milestone and is preserved intact solely as historical context; avoid copying its patterns into current development:
> - **Superseded Auth & Roles:** The historical `users` table and four-role authentication/RBAC design (`admin`, `manager`, `inventory_clerk`, `cashier`) are superseded. The current NEXORA architecture uses four UI-only operational workspaces (`Store Manager (Admin)`, `Inventory Staff`, `Purchase Manager`, `Finance Staff`) and does not implement user authentication or server-enforced RBAC.
> - **Non-Authoritative `forecast_cache`:** The historical `forecast_cache` proposal is not an authoritative current table definition.
> - **Superseded Inventory Types & Simplified Schema:** Historical integer inventory quantities (`INT` `current_stock`, `safety_stock`, `reorder_point`) and simplified entity relationships must not be copied into current implementation (the approved schema specifies 41 InnoDB tables with fractional `DECIMAL(14, 4)` base-UoM quantities and full operational/audit integrity).

---

# NEXORA – Database Design Specification (MySQL)

> **Notice:** This document defines the planned relational schema for future milestones. Database integration is not yet active in Milestone 1.

---

## 1. Entity-Relationship Overview

```mermaid
erDiagram
    USERS ||--o{ ORDERS : processes
    CUSTOMERS ||--o{ ORDERS : places
    ORDERS ||--|{ ORDER_ITEMS : contains
    PRODUCTS ||--o{ ORDER_ITEMS : ordered_in
    PRODUCTS ||--o{ INVENTORY : tracked_in
    PRODUCTS ||--o{ FORECAST_CACHE : predicts
    SUPPLIERS ||--o{ PURCHASE_ORDERS : fulfills
    PURCHASE_ORDERS ||--|{ PURCHASE_ORDER_ITEMS : contains
    PRODUCTS ||--o{ PURCHASE_ORDER_ITEMS : replenished_in
```

---

## 2. Planned Tables

### `users` (Authentication & RBAC)
- `id` (BIGINT PK AUTO_INCREMENT)
- `email` (VARCHAR 255 UNIQUE NOT NULL)
- `hashed_password` (VARCHAR 255 NOT NULL)
- `full_name` (VARCHAR 120 NOT NULL)
- `role` (ENUM('admin', 'manager', 'inventory_clerk', 'cashier') NOT NULL)
- `is_active` (BOOLEAN DEFAULT TRUE)
- `created_at` (TIMESTAMP)

### `products` (Catalog & SKU registry)
- `id` (BIGINT PK AUTO_INCREMENT)
- `stock_code` (VARCHAR 50 UNIQUE NOT NULL)
- `name` (VARCHAR 255 NOT NULL)
- `category` (VARCHAR 100)
- `unit_price` (DECIMAL(10,2) NOT NULL)
- `cost_price` (DECIMAL(10,2) NOT NULL)
- `created_at` (TIMESTAMP)

### `inventory` (Stock levels & warehouse locations)
- `id` (BIGINT PK AUTO_INCREMENT)
- `product_id` (BIGINT FK -> products.id)
- `current_stock` (INT NOT NULL DEFAULT 0)
- `safety_stock` (INT NOT NULL DEFAULT 0)
- `reorder_point` (INT NOT NULL DEFAULT 0)
- `last_restocked_at` (TIMESTAMP)

### `orders` & `order_items` (Sales & Billing)
- Tracks transactions, customer link, invoice total, tax, discount, and cashier reference.

### `forecast_cache` (Demand Projections)
- `id` (BIGINT PK AUTO_INCREMENT)
- `product_id` (BIGINT FK -> products.id)
- `horizon_days` (INT NOT NULL)
- `predicted_units` (DECIMAL(10,2) NOT NULL)
- `generated_at` (TIMESTAMP)
