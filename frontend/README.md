# NEXORA Frontend — Phase 1 Demonstration Client

This directory contains the **React 18 + TypeScript + Vite** client application for NEXORA, built for the 21 November 2026 academic project demonstration and viva presentation.

It provides an interactive, production-grade interface demonstrating real HTTP communication between a browser client and the NEXORA FastAPI ML inference backend.

---

## Capabilities & Architecture

- **Real HTTP API Communication:** Communicates directly with the FastAPI backend over native browser `fetch` (no mock data or internal Python imports).
- **Backend Health & Connectivity Monitoring:** Real-time polling of `GET /health` with visual status indicators (online / offline / checking).
- **Interactive Multi-Horizon Forecasting:**
  - Dynamic horizon selection across all 4 operational horizons: **7, 15, 30, and 90 days**.
  - Preset SKU catalog selector including top catalog SKUs (`85123A`, `71053`, `21777`) and an unseen SKU (`NEW_UNSEEN_SKU_DEMO`) to demonstrate robust fallback handling.
  - Granular historical feature controls (`lag_1`, `lag_7`, `lag_14`, `lag_28`, `rolling_mean_7`, `rolling_mean_28`) and calendar dates.
  - One-click **"Load Sample Feature Values"** button clearly identified for demonstration purposes.
- **Granular Model Metrics & Results Display:**
  - Displays predicted demand units per requested horizon.
  - Displays active ML model name (e.g. `Linear Regression` for D7, `Random Forest` for D15, D30, D90) and validation WAPE (%) benchmarks.
  - Informational warning cards for unseen or infrequent SKUs.
- **Raw HTTP Inspector Drawer:**
  - Expandable JSON viewer showing the exact `POST /api/v1/forecast/` request payload and HTTP 200 response JSON for live academic viva demonstration.

---

## Project Structure

```text
frontend/
├── index.html              # HTML5 entry with NEXORA branding and fonts
├── package.json            # React 18, TypeScript 5, Vite 5 dependencies
├── tsconfig.json           # Bundler-mode strict TypeScript configuration
├── vite.config.ts          # Vite build and dev-server configuration (Port 5173)
├── .env.example            # Environment template (VITE_API_BASE_URL)
├── public/
│   └── favicon.svg         # NEXORA brand icon
└── src/
    ├── main.tsx            # Application DOM mount
    ├── App.tsx             # Interactive forecasting client interface
    ├── App.css             # Component styling and layout system
    ├── index.css           # Global CSS variables and typography
    ├── vite-env.d.ts       # Vite environment type declarations
    ├── types/
    │   └── forecast.ts     # TypeScript interfaces matching backend Pydantic schemas
    └── services/
        └── api.ts          # Strongly-typed HTTP API client (fetch)
```

---

## Setup & Running the Frontend

### Prerequisites
- Node.js 18+ (tested on Node.js v26.x)
- npm 9+ (tested on npm 11.x)
- NEXORA FastAPI backend running on `http://localhost:8000`

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Configure Environment (Optional)
The default backend URL is `http://localhost:8000`. To customize:
```bash
cp .env.example .env
# Edit .env: VITE_API_BASE_URL=http://localhost:8000
```

### 3. Start Development Server
```bash
npm run dev
```
The application will be accessible at:
```text
http://localhost:5173
```

### 4. Build for Production
```bash
npm run build
```
Production assets are generated in `frontend/dist/`.
