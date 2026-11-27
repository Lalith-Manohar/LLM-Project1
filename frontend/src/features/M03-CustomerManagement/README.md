# M03 — Customer Management

- **Module ID & Official Name:** `M03` — Customer Management
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 1 (Retail Foundation)

## Purpose
Manage manually entered customer records, billing/shipping contacts, and soft customer status control (`customers.is_active`).

## Main Responsibilities & Boundaries
- Provide manual customer intake, editing, and soft deactivation/reactivation (never hard-delete customer records).
- Strictly exclude automated customer-address scraping from UCI historical records (`EXCL-08`).
- Does **not** own order fulfillment (`M05`) or invoice settlement (`M17`).

## Related Modules & Dependencies
- **Consumed by:** `M04` (Sales Management), `M05` (Order Management), `M17` (Billing & Finance), and `M18` (Shipping & Delivery).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: **Visible**
- `Finance Staff`: **Visible**
- `Inventory Staff`: **Hidden**
- `Purchase Manager`: **Hidden**

> **Important:** `M03` is visible in the UI **only** to `Store Manager (Admin)` and `Finance Staff`. This is **UI navigation visibility only — NOT security authorization, authentication, or server-side RBAC**.

## Known Backend / API Integration Status
- Operational customer CRUD endpoints (`/api/v1/customers`) are **PLANNED** (not yet implemented on `main`).
