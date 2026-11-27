# NEXORA Frontend — Learning-Friendly React Foundation

## 1. What the Frontend Is
This directory holds the **Two-Page Single Page Application (SPA)** foundation for **NEXORA — AI-Powered Retail Management & Intelligence System**. It replaces the earlier single-screen Phase 1 forecasting demo with a structured workspace shell prepared for all **18 core modules (`M01`–`M18`)** and **4 supporting capabilities (`SYS-01`–`SYS-04`)** across the **4 operational workspaces**.

## 2. Technology Stack & Purpose
- **React 18 & TypeScript:** Functional UI components with compile-time type safety.
- **Vite:** Fast local dev server (`http://localhost:5173`) and ES-module production bundler.
- **Tailwind CSS:** Utility-first styling (`src/styles/globals.css`, `tailwind.config.js`).
- **shadcn/ui + Radix UI + Lucide React:** Accessible, copy-owned UI primitives in `src/components/ui/` (`Button`, `Card`, `Input`, `Dialog`, `DropdownMenu`, `Table`, `Badge`) paired with crisp icons.
- **React Router:** Strictly two top-level pages (`/` and `/dashboard`).
- **Zustand:** Minimal, readable global store for UI workspace selection (`src/stores/useWorkspaceStore.ts`).
- **Axios + TanStack Query:** Centralized HTTP client (`src/services/api/client.ts`) and cached server-state queries (`src/hooks/useBackendHealth.ts`).
- **Vitest + React Testing Library:** Fast unit and UI foundation tests (`tests/foundation.test.tsx`).
- **Planned Next-Phase Approved Libraries** *(added when module forms/charts are built)*: `React Hook Form`, `Zod`, and `Recharts`.

## 3. Prerequisites
- **Node.js** `v18+` (includes `npm`)
- Optional for live API status: **NEXORA FastAPI backend** running on `http://localhost:8000` (via `.\start.ps1` from repository root or `uvicorn app.main:app --reload` in `backend/`)

## 4. Installation
```powershell
cd frontend
npm install
```
*(In clean CI or `start.ps1` runs, `npm ci` uses `package-lock.json` directly.)*

## 5. Development Startup
```powershell
npm run dev
```
- Opens on **`http://localhost:5173`** (kept identical to `backend/app/main.py` CORS origins and root `start.ps1`).
- Copy `.env.example` to `.env` if you need to override `VITE_API_BASE_URL` (defaults to `http://localhost:8000`).

## 6. Production Build
```powershell
npm run build
```
Outputs bundled static assets to gitignored `frontend/dist/`.

## 7. TypeScript Validation
```powershell
npm run typecheck
```
Runs `tsc --noEmit` across `src/` and `tests/` with strict mode enabled.

## 8. Test Execution
```powershell
npm test
```
Runs `vitest run` over `tests/foundation.test.tsx`.

## 9. Directory Structure
```text
frontend/
├── public/favicon.svg
├── src/
│   ├── app/
│   │   ├── layouts/DashboardLayout.tsx
│   │   ├── providers/AppProviders.tsx
│   │   └── router/AppRouter.tsx
│   ├── pages/
│   │   ├── WorkspaceSelection/WorkspaceSelectionPage.tsx
│   │   └── Dashboard/DashboardPage.tsx
│   ├── components/
│   │   ├── ui/               # Core shadcn/ui primitives (7 files)
│   │   ├── navigation/       # SidebarNav & in-header WorkspaceSwitcher
│   │   ├── dashboard/        # ModulePlaceholderView
│   │   └── shared/           # BackendStatusBadge (live /health check)
│   ├── services/api/         # Axios instance & verified endpoint helpers
│   ├── stores/               # Zustand workspace context store
│   ├── hooks/                # TanStack Query hooks
│   ├── types/                # TypeScript interfaces matching live backend schemas
│   ├── utils/                # cn() class helper & 18-module / 4-SYS catalog
│   └── styles/globals.css    # Tailwind CSS + theme tokens
└── tests/                    # Vitest + Testing Library checks
```

## 10. Application Routing
`src/app/router/AppRouter.tsx` enforces **two primary pages only**:
1. **`/` (`WorkspaceSelectionPage`)** — Displays `"Welcome to NEXORA — Select Your Workspace"` and the 4 workspace cards.
2. **`/dashboard` (`DashboardPage`)** — Renders `DashboardLayout` with workspace switcher, sidebar navigation, and active module view. Unknown routes redirect to `/`.

## 11. Workspace Context (UI Only — NOT Authentication or RBAC)
`src/stores/useWorkspaceStore.ts` stores `activeWorkspace` (`Store Manager (Admin)`, `Inventory Staff`, `Purchase Manager`, `Finance Staff`) and `activeNavItem`.
- Selecting a workspace adjusts **UI navigation visibility only** (for example, `M03 Customer Management` appears in `Store Manager (Admin)` and `Finance Staff`, never in `Inventory Staff` or `Purchase Manager`).
- NEXORA does **not** use user login, passwords, JWT tokens, or server-side RBAC.

## 12. API Integration Architecture
- `src/services/api/client.ts` configures a single Axios instance (`API_BASE_URL` from `VITE_API_BASE_URL` or `http://localhost:8000`).
- `src/services/api/healthApi.ts` and `src/types/api.ts` cover verified live endpoints (`GET /health`, `GET /ready`).
- Custom provenance headers (`X-NEXORA-Workspace`, `X-Correlation-ID`) are **not** auto-injected yet because Phase 1 backend routes do not consume workspace middleware today; wire them cleanly once Phase 2 backend middleware lands.

## 13. How to Add a New Module (`M01`–`M18`)
1. Check `docs/API_DOCUMENTATION.md` v2.1 and `backend/app/` to confirm the backend endpoints and Pydantic schemas exist (or are being built together).
2. Add typed request/response interfaces in `src/types/` matching the exact Pydantic fields.
3. Add Axios API helper functions under `src/services/api/` and TanStack Query hooks under `src/hooks/`.
4. Create a focused feature folder under `src/features/MXX-ModuleName/` with small React components (install `react-hook-form`, `zod`, or `recharts` only when that module actually needs forms or charts).
5. Wire the module's case into `DashboardPage.tsx` / `ModulePlaceholderView.tsx` without creating extra top-level routes outside `/` and `/dashboard`.

## 14. Current Limitations
- This task delivers the **foundation shell only**: `M01`–`M18` and `SYS-01`–`SYS-04` display placeholder cards (`ModulePlaceholderView`) with **no fabricated data**.
- MySQL operational CRUD endpoints (`M01`–`M11`, `M13`, `M15`–`M18`, `SYS-01`–`SYS-04`) are still **planned** in the backend (`0` operational DB tables exist yet).
- `React Hook Form`, `Zod`, and `Recharts` are intentionally omitted from `package.json` until form/chart modules are implemented.
