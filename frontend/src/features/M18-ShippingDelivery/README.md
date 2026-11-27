# M18 — Shipping & Delivery

- **Module ID & Official Name:** `M18` — Shipping & Delivery
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 4 (Business Operations)

## Purpose
Manage internal warehouse pick lists, `1:N` split shipments per order (`DDR-05`), printable packing slips, routing labels, and delivery status events.

## Main Responsibilities & Boundaries
- Operate strictly as internal warehouse & dispatch preparation (`EXCL-02`: no external FedEx/UPS/DHL carrier API integrations).
- Support split shipments independently of fulfilment batches while preserving order/invoice consistency.

## Related Modules & Dependencies
- **Depends on:** `M05` (Order Management), `M03` (Customer Management), and `M17` (Billing & Finance).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Finance Staff`: Visible
- `Purchase Manager`: Hidden

## Known Backend / API Integration Status
- Internal shipping, pick-list, and delivery event endpoints are **PLANNED** (not yet implemented on `main`).
