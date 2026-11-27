# M17 — Billing & Finance

- **Module ID & Official Name:** `M17` — Billing & Finance
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 4 (Business Operations)

## Purpose
Manage immutable `INR` invoices (`DDR-04`), manual payment recording, credit notes, `refunds` settlement tracking, and financial reconciliation.

## Main Responsibilities & Boundaries
- Preserve immutable finalized invoices (corrections happen via credit notes/refunds, never silent invoice edits).
- Track `Receivable Due`, `Open Refund Payable`, and `payment_status` states cleanly.
- Exclude statutory government E-Way bill generation (`EXCL-01`).

## Related Modules & Dependencies
- **Depends on:** `M03` (Customer Management), `M04` (Sales Management), `M05` (Order Management), and `M16` (Return Intelligence).
- **Referenced by:** `M18` (Shipping & Delivery) for order-invoice alignment.

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Finance Staff`: Visible
- `Inventory Staff`: Hidden
- `Purchase Manager`: Hidden

## Known Backend / API Integration Status
- Billing, invoice, payment, credit note, and refund endpoints are **PLANNED** (not yet implemented on `main`).
