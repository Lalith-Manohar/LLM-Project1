# M15 — Anomaly Detection

- **Module ID & Official Name:** `M15` — Anomaly Detection
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 2 (Business Intelligence & Predictive)

## Purpose
Detect and surface statistical and rule-based anomaly events across demand spikes, returns, inventory variances, and Purchase Orders (`DDR-08`).

## Main Responsibilities & Boundaries
- Compute/inspect domain anomaly events and severity classifications.
- Keep anomaly detection logic distinct from **`SYS-03` Smart Alerts**, which handles cross-module alert presentation and unresolved duplicate suppression.

## Related Modules & Dependencies
- **Monitors:** `M04`/`M05` (demand/sales), `M09` (inventory), `M11` (POs), and `M16` (returns).
- **Publishes to:** `SYS-03` (Smart Alerts).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Purchase Manager`: Visible
- `Finance Staff`: Visible

## Known Backend / API Integration Status
- Anomaly detection endpoints are **PLANNED** (not yet implemented on `main`).
