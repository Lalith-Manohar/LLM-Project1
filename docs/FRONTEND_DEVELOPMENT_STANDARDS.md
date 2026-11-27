# NEXORA — Frontend Module Development Standards & Parallel Integration Guide

- **Project:** NEXORA — AI-Powered Retail Management & Intelligence System
- **Document Version:** 1.0
- **Approved Frontend Baseline:** `main` (`7901fbcafe489d4a1d729f9944dd2a2156b560c2` + approved Tasks 10.5B/10.5C foundation)
- **Authoritative References:**
  - [`AGENTS.md`](../AGENTS.md)
  - [`docs/NEXORA — Technical Blueprint v1.0.md`](NEXORA%20%E2%80%94%20Technical%20Blueprint%20v1.0.md) *(Version 2.2)*
  - [`docs/DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) *(Version 2.9)*
  - [`docs/API_DOCUMENTATION.md`](API_DOCUMENTATION.md) *(Version 2.1)*
  - [`docs/FEATURES_STATUS.md`](FEATURES_STATUS.md) *(Version 2.3)*
  - [`docs/PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md) *(Version 2.0)*
  - [`docs/NEXORA — Application Functionality & System Workflow Guide.md`](NEXORA%20%E2%80%94%20Application%20Functionality%20%26%20System%20Workflow%20Guide.md) *(Version 1.0)*
  - [`frontend/README.md`](../frontend/README.md)

> [!IMPORTANT]
> **Purpose of This Guide:** This document defines the engineering, architecture, API, testing, and Git collaboration standards for **four developers** building NEXORA frontend modules in parallel on top of the approved two-page workspace foundation. It establishes conventions only — it does **not** implement business modules or alter approved backend/database contracts.

---

## 1. Approved Technology Stack

Use only the approved NEXORA frontend stack. **Do not install additional packages without coordinator approval**, and do not force a library into a simple screen where standard React or existing primitives are clearer.

| Library / Tool | Status in [`frontend/package.json`](../frontend/package.json) | When to Use |
| :--- | :--- | :--- |
| **React 18 + TypeScript 5 + Vite 6** | **Installed** (`react ^18.3.1`, `typescript ^5.8.3`, `vite ^6.3.5`) | Core UI runtime, strict static typing, local dev server (`localhost:5173`), production builds. |
| **Tailwind CSS 3 + `shadcn/ui`** | **Installed** (`tailwindcss ^3.4.17`, `@radix-ui/*`, `clsx`, `tailwind-merge`, `class-variance-authority`) | Layout, spacing, responsive grids, and accessible UI primitives (`frontend/src/components/ui/`). |
| **Lucide React** | **Installed** (`lucide-react ^0.554.0`) | Consistent UI icons across navigation, status badges, actions, and empty states. |
| **React Router v6** | **Installed** (`react-router-dom ^6.30.1`) | Strictly the two-page shell (`/` and `/dashboard`). Do not add separate per-role pages. |
| **Zustand** | **Installed** (`zustand ^5.0.8`) | Shared client-side UI workspace context (`useWorkspaceStore.ts`) only. |
| **TanStack Query** | **Installed** (`@tanstack/react-query ^5.90.10`) | Fetching, caching, loading/error states, and invalidation of FastAPI server data. |
| **Axios** | **Installed** (`axios ^1.13.2`) | All HTTP calls through the centralized `apiClient` (`frontend/src/services/api/client.ts`). |
| **Vitest + React Testing Library** | **Installed** (`vitest ^3.2.4`, `@testing-library/react ^16.3.0`, `jsdom ^26.1.0`) | Unit and component integration tests for every module (`npm test`). |
| **React Hook Form** | **Approved — Not Yet Installed** | Multi-field or complex operational forms (e.g., `M01`, `M02`, `M03`, `M05`, `M11`, `M16`, `M17`) once installed with coordinator approval. |
| **Zod** | **Approved — Not Yet Installed** | Declarative client-side validation schemas paired with React Hook Form (or payload validation) once installed with coordinator approval. |
| **Recharts** | **Approved — Not Yet Installed** | Charts and analytics visualizations (e.g., `M06`, `M07`, `M12`, `M13`) once installed with coordinator approval. |

> [!NOTE]
> **Simple Forms Before RHF/Zod Installation:** For trivial single-input filters or search bars, use controlled React `useState`. If a module genuinely needs `react-hook-form`, `zod`, `@hookform/resolvers`, or `recharts`, request coordinator approval before adding them to `frontend/package.json`.

---

## 2. Feature-Based Module Structure

All 18 core business modules must live under `frontend/src/features/` inside their designated module directory:

```text
frontend/src/features/
├── M01-ProductManagement/
├── M02-SupplierManagement/
├── M03-CustomerManagement/
├── M04-SalesManagement/
├── M05-OrderManagement/
├── M06-BusinessIntelligence/
├── M07-SeasonalDemand/
├── M08-ProductLifecycle/
├── M09-InventoryControl/
├── M10-StockMovement/
├── M11-PurchasePlanning/
├── M12-DemandForecasting/
├── M13-PriceRevenue/
├── M14-PredictivePlanner/
├── M15-AnomalyDetection/
├── M16-ReturnIntelligence/
├── M17-BillingFinance/
└── M18-ShippingDelivery/
```

> [!NOTE]
> **Baseline Fact:** In the Task 10.5B/10.5C foundation, `frontend/src/features/` does not yet exist on disk (`DashboardPage` renders `ModulePlaceholderView`). Create your assigned `frontend/src/features/Mxx-*/` directory when you begin implementing that module.

### Recommended Internal Module Layout

Use a lightweight structure inside your feature folder and **create only the subfolders your module actually needs**:

```text
frontend/src/features/M03-CustomerManagement/
├── components/    # Module-specific UI pieces (e.g., CustomerTable.tsx, CustomerFormDialog.tsx)
├── views/         # Main module view(s) rendered inside /dashboard (or pages/)
├── hooks/         # Module TanStack Query hooks (e.g., useCustomers.ts)
├── services/      # Module API calls using apiClient (e.g., customerApi.ts)
├── types/         # Module TypeScript interfaces matching backend schemas
└── index.ts       # Clean public export for DashboardPage wiring
```

- **Avoid over-engineering:** If a module has one view and one service file, do not create empty directories or extra wrapper layers.

---

## 3. Shared Component Ownership

| Directory | Owner / Purpose | Examples on `main` |
| :--- | :--- | :--- |
| `frontend/src/components/ui/` | Reusable `shadcn/ui` primitives | `badge.tsx`, `button.tsx`, `card.tsx`, `dialog.tsx`, `dropdown-menu.tsx`, `input.tsx`, `table.tsx` |
| `frontend/src/components/shared/` | Reusable app-level widgets | `BackendStatusBadge.tsx` |
| `frontend/src/components/navigation/` | Workspace switcher & sidebar | `SidebarNav.tsx`, `WorkspaceSwitcher.tsx` |
| `frontend/src/components/dashboard/` | Dashboard-level shell views | `ModulePlaceholderView.tsx` |
| `frontend/src/features/Mxx-*/` | Module-specific UI & logic | Assigned developer's module components |

### Ownership Rules
1. **Inspect before creating:** Check `components/ui/` and `components/shared/` before building any button, badge, table, dialog, or input.
2. **Never duplicate UI primitives:** Reuse `components/ui/*`; if a new `shadcn/ui` primitive is needed across multiple modules, ask the coordinator to add it centrally.
3. **Keep business logic out of shared folders:** Never place module-specific components (e.g., `CustomerForm` or `POApprovalModal`) inside `components/shared/` or `components/ui/`.
4. **Protect navigation and workspace config:** Do not modify `SidebarNav.tsx`, `WorkspaceSwitcher.tsx`, `DashboardLayout.tsx`, `AppRouter.tsx`, or `src/utils/modules.ts` without coordinator approval.

---

## 4. API Integration Standards

All HTTP requests must go through `apiClient` in [`frontend/src/services/api/client.ts`](../frontend/src/services/api/client.ts) (`VITE_API_BASE_URL` defaulting to `http://localhost:8000`).

### Conventions
- **Service modules (`features/Mxx-*/services/`):** Export small typed async functions (`fetchProducts`, `createCustomer`, `updateCustomer`, etc.) that call `apiClient.get/post/put/patch/delete` and return `data`.
- **TanStack Query hooks (`features/Mxx-*/hooks/`):**
  - **GET queries:** Use `useQuery` with structured, module-scoped query keys (e.g., `['m03', 'customers', filters]`).
  - **POST / PUT / PATCH / DELETE mutations:** Use `useMutation` (only for methods actually implemented by FastAPI) and invalidate relevant query keys in `onSuccess` via `queryClient.invalidateQueries({ queryKey: ['m03', 'customers'] })`.
- **UI States:** Every data-driven view must explicitly handle **Loading** (skeleton/spinner), **Error** (clear message + retry action, never silent failure), and **Empty** (helpful empty-state message) states.
- **API Response Typing:** Place module-specific request/response interfaces in `features/Mxx-*/types/` and shared probe/common types in `frontend/src/types/api.ts`.

### Strict API Restrictions
1. **Never invent API endpoints.**
2. **Never assume a documented endpoint is already implemented.** As of the Task 10.5C baseline, only `/health`, `/ready`, `/api/v1/forecast/*`, `/api/v1/experimental/*`, and stateless `POST /api/v1/inventory/recommend` exist in `backend/app/api/routes/`.
3. **Verify backend implementation before integrating** by inspecting `backend/app/api/routes/` and `backend/app/schemas/`.
4. **Follow [`docs/API_DOCUMENTATION.md`](API_DOCUMENTATION.md) and live Pydantic schemas**; never create frontend types that contradict backend contracts.
5. **Do not inject undocumented headers** (such as `X-NEXORA-Workspace` or `X-Correlation-ID`) into `apiClient` until the corresponding backend middleware/contract is implemented and approved by the coordinator.
6. **Never fabricate realistic mock production data** (no fake revenue numbers, fake SKUs, or fake customer balances presented as live data).
7. **If an endpoint is still `PLANNED`,** render a clearly labelled placeholder/status notice instead of faking a live integration.

---

## 5. Workspace & Module Visibility

Preserve the exact two-page structure (`/` and `/dashboard`), the **4 workspaces**, the **18 core modules (`M01`–`M18`)**, and the **4 separate supporting capabilities (`SYS-01`–`SYS-04`)** defined in [`frontend/src/utils/modules.ts`](../frontend/src/utils/modules.ts):

- **Workspaces:** `Store Manager (Admin)`, `Inventory Staff`, `Purchase Manager`, `Finance Staff`
- **`M03 Customer Management` Visibility Rule:**
  - `Store Manager (Admin)`: **Visible**
  - `Finance Staff`: **Visible**
  - `Inventory Staff`: **Hidden**
  - `Purchase Manager`: **Hidden**

> [!WARNING]
> **Workspace Selection Is UI Context Only — NOT Security:**
> Workspace selection filters UI navigation and operational focus. It is **not** user authentication, identity verification, server-side authorization, or RBAC. Never describe or rely on frontend visibility rules as a security boundary.

---

## 6. State Management Rules

| State Type | Approved Tool | Example |
| :--- | :--- | :--- |
| **Local UI state** | React `useState` | Dialog open/close, search input text, selected table row |
| **Shared workspace context** | Zustand (`useWorkspaceStore`) | `activeWorkspace`, `activeNavItem` |
| **Server data & cache** | TanStack Query | API lists, detail records, forecast responses, `/health` |
| **Complex form state** | React Hook Form *(when approved/installed)* | Multi-field create/edit forms |
| **Schema validation** | Zod *(when approved/installed)* | Form field rules matching backend Pydantic constraints |

**Avoid:**
- Duplicating server-fetched API lists or records inside Zustand.
- Adding extra global stores or unnecessary React Context providers.
- Calling `axios` / `apiClient` directly inside JSX event handlers instead of a `services/` + `hooks/` layer.

---

## 7. UI & Coding Standards

NEXORA is built by a student team that must read, maintain, and explain every line of code:

- **Prefer clarity over cleverness:** Write straightforward, readable TypeScript and JSX rather than generic factories or deep abstractions.
- **Functional components & strict TypeScript:** Use typed `interface` props; avoid `any` (use `unknown` + narrowing when needed).
- **Naming conventions:**
  - Components & view files: `PascalCase` (e.g., `CustomerTable.tsx`, `ForecastChartCard.tsx`)
  - Hooks: `camelCase` prefixed with `use` (e.g., `useCustomers.ts`)
  - Services & utilities: `camelCase` (e.g., `customerApi.ts`, `formatCurrency.ts`)
  - Module folders: exact `Mxx-ModuleName` convention in Section 2
- **Styling & layout:** Use Tailwind utility classes and `shadcn/ui` primitives; keep layouts responsive (`sm:`, `md:`, `lg:`) inside `DashboardLayout`.
- **Accessibility:** Use semantic elements (`<button>`, `<table>`, `<label>`), `aria-label` for icon-only buttons, and keyboard-accessible dialogs/menus.
- **Comments:** Add brief docstrings/comments explaining *why* a non-obvious rule exists (e.g., `INR` vs `GBP` display separation, `UNAVAILABLE` lead-time state).

---

## 8. Testing Standards

Every module PR must include Vitest + React Testing Library tests under `frontend/tests/` (or co-located `*.test.tsx` discovered by Vitest) covering this practical minimum checklist — **no arbitrary coverage percentage is required**:

1. Main module view renders cleanly without runtime errors.
2. Key user interactions work (tabs, filters, dialogs, buttons).
3. Form validation catches invalid inputs where forms exist.
4. Loading, error, and empty states render appropriately.
5. Workspace visibility behaves correctly (especially `M03` hidden in `Inventory Staff` and `Purchase Manager`).
6. API calls are cleanly mocked/verified against expected FastAPI contracts.
7. Critical module UI rules are verified (e.g., `INR` formatting, non-negative forecasts, 5 separate stock metrics).
8. All existing tests (including `tests/foundation.test.tsx`) continue to pass.

---

## 9. Git & Parallel Development Rules

1. **Always branch from the latest approved `main`.**
2. **Never commit, merge, or push directly to `main`.**
3. **Own only your assigned module directories** (`frontend/src/features/Mxx-*/` and your module tests).
4. **Coordinator approval is required** before modifying `components/ui/`, `components/shared/`, `components/navigation/`, `stores/`, `services/api/client.ts`, `types/api.ts`, `types/workspace.ts`, `utils/modules.ts`, `AppRouter.tsx`, `DashboardPage.tsx`, or `package.json`.
5. **Database schema (`DATABASE_SCHEMA.md`) and backend API contracts (`API_DOCUMENTATION.md`) are owned centrally** — developers must not alter them independently.
6. **Coordinator integrates all module branches** after review.

### Branch Naming Example
```text
feat/m01-product-management
feat/m03-customer-management
feat/m09-inventory-control
feat/m12-demand-forecasting
```

### Required Developer Completion Report Template
```markdown
## Module Completion Report — <Mxx Module Name>
- **Branch:** `feat/mxx-...` (based on `main` @ `<commit-sha>`)
- **Files Created / Modified:** <list exact paths>
- **Backend Endpoints Integrated / Placeholder Status:** <verified live routes vs PLANNED placeholders>
- **Checks Run:**
  - `npx tsc --noEmit` (exit code)
  - `npm run build` (exit code)
  - `npm test` (exact pass/fail counts)
- **Known Issues / Dependencies:** <list any shared wiring needed in DashboardPage or backend blockers>
```

---

## 10. Module Completion Checklist

Before requesting coordinator review and integration, confirm every item:

- [ ] Code lives inside the assigned `frontend/src/features/Mxx-*/` directory.
- [ ] Workspace visibility matches [`frontend/src/utils/modules.ts`](../frontend/src/utils/modules.ts) (including `M03` restriction).
- [ ] UI uses approved Tailwind + `shadcn/ui` components cleanly and responsively.
- [ ] All integrated API endpoints and types are verified against `backend/` and `API_DOCUMENTATION.md` (unimplemented APIs clearly marked as placeholders).
- [ ] Loading, error, and empty states are handled explicitly.
- [ ] Form validation is implemented where forms exist.
- [ ] Module tests cover rendering, interactions, states, visibility, and mocked API behavior.
- [ ] `npx tsc --noEmit` passes with exit code `0`.
- [ ] `npm run build` passes with exit code `0`.
- [ ] `npm test` passes with zero regressions.
- [ ] Zero unrelated files or undocumented npm dependencies were modified/added.
- [ ] Completion report is prepared using the Section 9 template.

---

## 11. Four-Developer Ownership & Provisional Allocation

This allocation is **provisional** (subject to coordinator adjustment) and groups modules by **functional cohesion and shared domain dependencies** rather than equal module counts:

| Developer | Domain Group | Assigned Modules |
| :--- | :--- | :--- |
| **Developer 1** | **Retail Foundation** | `M01` Product Management, `M02` Supplier Management, `M03` Customer Management, `M04` Sales Management, `M05` Order Management |
| **Developer 2** | **Business Intelligence & Predictive** | `M06` Business Intelligence, `M07` Seasonal Demand Calendar, `M08` Product Lifecycle Intelligence, `M12` Demand Forecasting, `M13` Price & Revenue Intelligence, `M14` Predictive Planner, `M15` Anomaly Detection |
| **Developer 3** | **Inventory & Procurement** | `M09` Inventory Control, `M10` Stock Movement Tracking, `M11` Purchase Planning Simulator |
| **Developer 4** | **Business Operations** | `M16` Return Intelligence, `M17` Billing & Finance, `M18` Shipping & Delivery |

---

## 12. Cross-Module Boundaries & Workflows

Developers must respect these domain boundaries and preserve **Workflows A–G** in [`docs/NEXORA — Application Functionality & System Workflow Guide.md`](NEXORA%20%E2%80%94%20Application%20Functionality%20%26%20System%20Workflow%20Guide.md) as well as `DDR-01`–`DDR-10` and `EXCL-01`–`EXCL-08` in [`Technical Blueprint v2.2`](NEXORA%20%E2%80%94%20Technical%20Blueprint%20v1.0.md) *(this guide does not redefine business rules)*:

- **`M01` & `M02`:** Provide catalog SKUs, UoM conversions, suppliers, and supplier-product lead-time foundations.
- **`M03`:** Provides customer records consumed by `M04` Sales and `M05` Orders (and restricted in UI nav to `Store Manager` and `Finance Staff`).
- **`M04` vs. `M05`:** Preserve the strict distinction between **confirmed/fulfilled Orders (`M05`)** and **realized Sales (`M04`)**.
- **`M09` vs. `M10`:** `M09` owns live stock balances (5 separate metrics); `M10` displays the immutable stock movement ledger and must not duplicate inventory ownership.
- **`M11`:** Manages purchase simulations, PO drafting, dual-control approvals, and receipts.
- **`M12` vs. `M14`:** `M12` provides ML demand forecasts (`7/15/30/90`d); `M14` provides supplier lead-time predictive planning and must not be conflated with `M12`.
- **`M15` vs. `SYS-03`:** `M15` owns anomaly detection events; `SYS-03` owns cross-module smart alert presentation.
- **`M16`, `M17`, `M18`:** `M16` handles returns and refund workflows; `M17` handles billing, invoices, payments, credit notes, and financial records; `M18` handles internal pick lists, split shipments, packing slips, and routing labels.
