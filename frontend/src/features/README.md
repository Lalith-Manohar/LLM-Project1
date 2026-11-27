# NEXORA Frontend Features (`frontend/src/features/`)

This directory holds the **18 core business modules (`M01`–`M18`)** of NEXORA. Supporting system capabilities (`SYS-01`–`SYS-04`) are tracked separately and are **not** core feature modules.

---

## 1. Why Feature-Based Architecture Exists
- **Parallelism:** Allows four developers to build assigned modules on separate feature branches with minimal merge conflicts.
- **Clarity:** Keeps each module's UI components, views, hooks, API services, and types together so student developers can read and explain a module end-to-end.
- **Isolation:** Prevents business-specific logic from leaking into global shared folders.

---

## 2. Module Ownership & Provisional Allocation
See [`docs/FRONTEND_DEVELOPMENT_STANDARDS.md`](../../../docs/FRONTEND_DEVELOPMENT_STANDARDS.md) for the full governance rules:
- **Developer 1 (Retail Foundation):** `M01`–`M05`
- **Developer 2 (BI & Predictive):** `M06`–`M08`, `M12`–`M15`
- **Developer 3 (Inventory & Procurement):** `M09`–`M11`
- **Developer 4 (Business Operations):** `M16`–`M18`

---

## 3. Recommended Internal Module Structure
Create **only** the folders and files your module actually needs when you begin implementing it:

```text
Mxx-ModuleName/
├── README.md
├── components/   # Module-specific UI pieces (when needed)
├── views/        # Main module view(s) rendered inside /dashboard (when needed)
├── hooks/        # Module TanStack Query hooks (when needed)
├── services/     # Module API functions using apiClient (when needed)
├── types/        # Module TypeScript interfaces matching backend schemas (when needed)
└── index.ts      # Clean public export for DashboardPage wiring (when useful)
```

---

## 4. Protected Shared Folders (Coordinator Approval Required)
Do **not** modify these shared files/directories without coordinator approval:
- `frontend/src/components/ui/`
- `frontend/src/components/shared/`
- `frontend/src/components/navigation/`
- `frontend/src/components/dashboard/`
- `frontend/src/app/` (`AppRouter.tsx`, `AppProviders.tsx`, `DashboardLayout.tsx`)
- `frontend/src/pages/` (`WorkspaceSelectionPage.tsx`, `DashboardPage.tsx`)
- `frontend/src/stores/useWorkspaceStore.ts`
- `frontend/src/services/api/client.ts`
- `frontend/src/utils/modules.ts`
- `frontend/src/types/api.ts`, `frontend/src/types/workspace.ts`
- `frontend/package.json`

---

## 5. Integrating With the Dashboard
- Keep the **two-page architecture** (`/` and `/dashboard`) intact.
- Export each module's main view from `Mxx-ModuleName/index.ts` so the coordinator can wire `activeNavItem === 'Mxx'` cleanly inside `DashboardPage` when ready for integration.
- Respect workspace visibility in `frontend/src/utils/modules.ts` (never treat UI visibility as authentication or RBAC).

---

## 6. Do Not Duplicate Shared Components
Before creating any button, badge, card, dialog, dropdown, input, or table, inspect `frontend/src/components/ui/` and `frontend/src/components/shared/`. Reuse existing `shadcn/ui` primitives and keep module-specific components strictly inside `Mxx-ModuleName/components/`.
