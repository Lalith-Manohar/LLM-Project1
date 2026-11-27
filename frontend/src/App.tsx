import React, { useState, useEffect } from 'react'
import {
  ForecastRequest,
  ForecastResponse,
  HealthResponse
} from './types/forecast'
import {
  checkBackendHealth,
  submitForecast,
  ApiError
} from './services/api'
import { WorkspaceProvider, useWorkspace } from './context/WorkspaceContext'
import { WorkspaceCode } from './types/workspace'
import { BusinessIntelligenceView } from './modules/m06/BusinessIntelligenceView'
import { ProductLifecycleView } from './modules/m08/ProductLifecycleView'
import './App.css'

// Preset demo product SKUs from UCI Online Retail II dataset
const DEMO_SKUS = [
  { code: '85123A', name: 'White Hanging Heart T-Light Holder (High-volume active SKU, 739 days history)' },
  { code: '71053', name: 'White Metal Lantern (Medium-volume active SKU, 739 days history)' },
  { code: '85099B', name: 'Jumbo Bag Red Retrospot (Top high-demand active SKU, 739 days history)' },
  { code: '22423', name: 'Regency Cakestand 3 Tier (Core active SKU, 739 days history)' },
  { code: '20877', name: 'Short-lifespan SKU (9 days lifespan — tests insufficient history validation)' },
]

type ActiveDashboardTab = 'forecast' | 'm06' | 'm08'
type ActivePage = 'workspace_select' | 'dashboard'

const NexoraShell: React.FC = () => {
  const { workspace, workspaceDef, setWorkspace, allWorkspaces } = useWorkspace()

  // Strict Two-Page Architecture: Page 1 (Workspace Selection) & Page 2 (Unified Dashboard)
  const [activePage, setActivePage] = useState<ActivePage>('dashboard')
  const [activeTab, setActiveTab] = useState<ActiveDashboardTab>('m06')

  // Backend connectivity state
  const [backendHealth, setBackendHealth] = useState<HealthResponse | null>(null)
  const [healthStatus, setHealthStatus] = useState<'checking' | 'online' | 'offline'>('checking')

  // Phase 1 Forecast simulator state (preserved intact)
  const [stockCode, setStockCode] = useState<string>('85123A')
  const [selectedHorizons, setSelectedHorizons] = useState<number[]>([7, 15, 30, 90])
  const [loading, setLoading] = useState<boolean>(false)
  const [forecastResult, setForecastResult] = useState<ForecastResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [lastPayload, setLastPayload] = useState<ForecastRequest | null>(null)
  const [showInspector, setShowInspector] = useState<boolean>(false)
  const [activeInspectorTab, setActiveInspectorTab] = useState<'request' | 'response'>('response')

  const verifyBackend = async () => {
    setHealthStatus('checking')
    try {
      const health = await checkBackendHealth()
      setBackendHealth(health)
      setHealthStatus('online')
    } catch {
      setBackendHealth(null)
      setHealthStatus('offline')
    }
  }

  useEffect(() => {
    verifyBackend()
  }, [])

  const toggleHorizon = (h: number) => {
    if (selectedHorizons.includes(h)) {
      if (selectedHorizons.length === 1) return
      setSelectedHorizons(selectedHorizons.filter((x) => x !== h))
    } else {
      setSelectedHorizons([...selectedHorizons, h].sort((a, b) => a - b))
    }
  }

  const handleSelectSku = (code: string) => {
    setStockCode(code)
    setErrorMessage(null)
  }

  const handleGenerateForecast = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)
    setLoading(true)

    const payload: ForecastRequest = {
      stock_code: stockCode.trim(),
      horizons: selectedHorizons
    }
    setLastPayload(payload)

    try {
      const response = await submitForecast(payload)
      setForecastResult(response)
      setShowInspector(true)
      setActiveInspectorTab('response')
    } catch (err: any) {
      if (err instanceof ApiError) {
        setErrorMessage(`[HTTP ${err.status}] ${err.message}`)
      } else {
        setErrorMessage(err.message || 'An unexpected error occurred during prediction.')
      }
      setForecastResult(null)
    } finally {
      setLoading(false)
    }
  }

  // Page 1: Stakeholder Workspace Selection (zero login/password fields per Blueprint v2.2)
  if (activePage === 'workspace_select') {
    return (
      <div className="app-container">
        <header className="app-header">
          <div className="header-brand">
            <div className="brand-logo">
              <svg viewBox="0 0 32 32" width="28" height="28">
                <rect width="32" height="32" rx="8" fill="#1e3a8a" />
                <path d="M7 23 L13 15 L18 19 L25 9" fill="none" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="25" cy="9" r="2.5" fill="#38bdf8" />
              </svg>
            </div>
            <div>
              <h1 className="brand-title">NEXORA</h1>
              <p className="brand-subtitle">AI-Powered Retail Management &amp; Intelligence System</p>
            </div>
          </div>
          <div className="header-meta">
            <button type="button" className="btn-secondary" onClick={() => setActivePage('dashboard')}>
              Return to Dashboard
            </button>
          </div>
        </header>

        <main className="main-content workspace-select-main">
          <div className="workspace-select-header">
            <h2>Welcome to NEXORA — Select Your Workspace</h2>
            <p className="section-desc">
              Choose an operational stakeholder workspace to configure dashboard views and provenance context (<code>X-NEXORA-Workspace</code>). No login credentials required.
            </p>
          </div>

          <div className="workspace-cards-grid">
            {allWorkspaces.map((ws) => (
              <button
                key={ws.code}
                type="button"
                className={`workspace-card ${workspace === ws.code ? 'active' : ''}`}
                onClick={() => {
                  setWorkspace(ws.code)
                  setActivePage('dashboard')
                }}
              >
                <div className="workspace-card-top">
                  <h3>{ws.label}</h3>
                  {workspace === ws.code && <span className="badge badge-success">Active</span>}
                </div>
                <p className="workspace-card-desc">{ws.description}</p>
                <div className="workspace-card-scopes">
                  <div><strong>M06:</strong> {ws.m06ScopeNote}</div>
                  <div><strong>M08:</strong> {ws.m08ScopeNote}</div>
                </div>
              </button>
            ))}
          </div>
        </main>
      </div>
    )
  }

  // Page 2: Unified Retail Management Dashboard
  return (
    <div className="app-container">
      {/* Top Header with In-Header Workspace Switcher */}
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-logo">
            <svg viewBox="0 0 32 32" width="28" height="28">
              <rect width="32" height="32" rx="8" fill="#1e3a8a" />
              <path d="M7 23 L13 15 L18 19 L25 9" fill="none" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="25" cy="9" r="2.5" fill="#38bdf8" />
            </svg>
          </div>
          <div>
            <h1 className="brand-title">NEXORA</h1>
            <p className="brand-subtitle">Unified Retail Management Dashboard • {workspaceDef.label}</p>
          </div>
        </div>

        <div className="header-meta">
          <div className="workspace-switcher-wrap">
            <label htmlFor="workspace-switcher" className="switcher-label">Workspace:</label>
            <select
              id="workspace-switcher"
              className="workspace-select-input"
              value={workspace}
              onChange={(e) => setWorkspace(e.target.value as WorkspaceCode)}
              aria-label="Switch stakeholder workspace"
            >
              {allWorkspaces.map((ws) => (
                <option key={ws.code} value={ws.code}>{ws.label}</option>
              ))}
            </select>
            <button
              type="button"
              className="btn-ghost-xs"
              onClick={() => setActivePage('workspace_select')}
              title="Open Page 1 Workspace Selection"
            >
              Cards
            </button>
          </div>

          <div className={`status-pill ${healthStatus}`}>
            <span className="status-dot"></span>
            <span className="status-text">
              {healthStatus === 'checking' && 'Checking Backend...'}
              {healthStatus === 'online' && `FastAPI Online (${backendHealth?.service || 'v0.1.0'})`}
              {healthStatus === 'offline' && 'Backend Offline (Port 8000)'}
            </span>
            <button className="btn-refresh" onClick={verifyBackend} title="Retry backend health check">
              ↻
            </button>
          </div>
        </div>
      </header>

      {/* Unified Dashboard Module Navigation Tabs */}
      <nav className="dashboard-nav" aria-label="Dashboard modules">
        <div className="dashboard-nav-inner">
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'm06' ? 'active' : ''}`}
            onClick={() => setActiveTab('m06')}
          >
            M06: Business Intelligence
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'm08' ? 'active' : ''}`}
            onClick={() => setActiveTab('m08')}
          >
            M08: Product Lifecycle Intelligence
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'forecast' ? 'active' : ''}`}
            onClick={() => setActiveTab('forecast')}
          >
            M12: Demand Forecasting (Phase 1 Baseline)
          </button>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="main-content">
        {activeTab === 'm06' && <BusinessIntelligenceView />}

        {activeTab === 'm08' && <ProductLifecycleView />}

        {activeTab === 'forecast' && (
          <div className="grid-layout">
            {/* Left Column: Form & Inputs (Preserved Phase 1 Simulator) */}
            <div className="card control-card">
              <div className="card-header">
                <h2>Demand Forecasting Simulator</h2>
                <p className="section-desc">
                  Select a product SKU and planning horizons to query multi-horizon ML demand regression forecasts from FastAPI.
                </p>
              </div>

              <form onSubmit={handleGenerateForecast}>
                <div className="form-group">
                  <label htmlFor="sku-input">
                    Product SKU / StockCode <span className="required">*</span>
                  </label>
                  <input
                    id="sku-input"
                    type="text"
                    className="input-text"
                    value={stockCode}
                    onChange={(e) => setStockCode(e.target.value)}
                    placeholder="e.g. 85123A"
                    required
                  />
                  <div className="preset-container">
                    <span className="preset-label">Catalog Presets:</span>
                    {DEMO_SKUS.map((item) => (
                      <button
                        key={item.code}
                        type="button"
                        className={`preset-pill ${stockCode === item.code ? 'active' : ''}`}
                        onClick={() => handleSelectSku(item.code)}
                        title={item.name}
                      >
                        {item.code}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="auto-notice">
                  <div className="auto-notice-title">
                    <span>⚡</span>
                    <strong>Automated Feature Engineering</strong>
                  </div>
                  <div className="auto-notice-body">
                    Historical sales data is automatically processed to generate demand forecasts.
                    The backend retrieves daily transaction records from the retail CSV dataset, calculates 7/14/28-day lags and rolling averages, and projects from the latest historical observation date (up to 09 Dec 2011).
                  </div>
                </div>

                <div className="form-group">
                  <label>Target Forecasting Horizons</label>
                  <div className="horizon-button-group">
                    {[7, 15, 30, 90].map((h) => {
                      const active = selectedHorizons.includes(h)
                      return (
                        <button
                          key={h}
                          type="button"
                          className={`horizon-btn ${active ? 'active' : ''}`}
                          onClick={() => toggleHorizon(h)}
                        >
                          <span className="horizon-days">{h} Days</span>
                          <span className="horizon-tag">
                            {h === 7 && 'Operational Restock'}
                            {h === 15 && 'Bi-Weekly Orders'}
                            {h === 30 && 'Monthly Planning'}
                            {h === 90 && 'Quarterly Quota'}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                  <p className="field-hint">Click to toggle one or more planning horizons.</p>
                </div>

                <button
                  type="submit"
                  className="btn-submit"
                  disabled={loading || selectedHorizons.length === 0}
                >
                  {loading ? (
                    <span className="spinner-text">
                      <span className="spinner"></span> Processing Historical Sales &amp; Running ML Models...
                    </span>
                  ) : (
                    `Generate Forecast (${selectedHorizons.length} Horizons)`
                  )}
                </button>
              </form>
            </div>

            {/* Right Column: Prediction Results & Output Cards */}
            <div className="card results-card">
              <div className="card-header">
                <h2>Multi-Horizon Forecast Results</h2>
                <p className="section-desc">
                  Machine learning demand estimates evaluated across Ridge Regression and Random Forest pipelines.
                </p>
              </div>

              {errorMessage && (
                <div className="alert alert-error">
                  <div className="alert-icon">⚠️</div>
                  <div className="alert-content">
                    <strong>Prediction Failed:</strong> {errorMessage}
                  </div>
                </div>
              )}

              {!forecastResult && !loading && !errorMessage && (
                <div className="empty-state">
                  <div className="empty-icon">📈</div>
                  <h3>No Prediction Executed Yet</h3>
                  <p>
                    Select a product SKU and target horizons on the left, then click <strong>Generate Forecast</strong>.
                  </p>
                  <div className="endpoint-tag">
                    Target Endpoint: <code>POST http://localhost:8000/api/v1/forecast/</code>
                  </div>
                </div>
              )}

              {loading && (
                <div className="loading-state">
                  <div className="large-spinner"></div>
                  <p className="loading-title">Retrieving Historical Sales &amp; Executing Inference...</p>
                  <p className="loading-subtitle">Filtering continuous daily records &amp; evaluating scikit-learn estimators</p>
                </div>
              )}

              {forecastResult && !loading && (
                <div className="results-container">
                  <div className="results-meta-bar">
                    <div>
                      <span className="meta-label">Product SKU:</span>
                      <strong className="meta-value">{forecastResult.stock_code}</strong>
                    </div>
                    {forecastResult.observation_date && (
                      <div>
                        <span className="meta-label">Forecast Origin:</span>
                        <strong className="meta-value date-highlight">{forecastResult.observation_date}</strong>
                      </div>
                    )}
                    {forecastResult.history_days && (
                      <div>
                        <span className="meta-label">Historical Base:</span>
                        <span className="meta-time">{forecastResult.history_days} Days Analyzed</span>
                      </div>
                    )}
                    <div>
                      <span className="meta-label">Status:</span>
                      <span className="badge badge-success">{forecastResult.status.toUpperCase()}</span>
                    </div>
                  </div>

                  {forecastResult.warnings && forecastResult.warnings.length > 0 && (
                    <div className="alert alert-warning">
                      <div className="alert-icon">ℹ️</div>
                      <div className="alert-content">
                        {forecastResult.warnings.map((w, idx) => (
                          <div key={idx}>{w}</div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="horizon-cards-grid">
                    {forecastResult.horizon_details.map((detail) => (
                      <div key={detail.horizon_days} className="horizon-card">
                        <div className="horizon-card-top">
                          <span className="card-horizon-title">{detail.horizon_days}-Day Horizon</span>
                          <span className="card-horizon-label">D_{detail.horizon_days}</span>
                        </div>
                        <div className="card-prediction-value">
                          {detail.predicted_demand.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })}
                          <span className="card-unit"> {forecastResult.units}</span>
                        </div>
                        <div className="card-model-meta">
                          <div className="meta-row">
                            <span className="meta-name">Active Model:</span>
                            <span className="meta-val" title={detail.model_name}>
                              {detail.model_name.includes('Linear') || detail.model_name.includes('Ridge') || detail.horizon_days === 7 ? 'Ridge Regression' : 'Random Forest'}
                            </span>
                          </div>
                          {detail.wape !== null && detail.wape !== undefined && (
                            <div className="meta-row">
                              <span className="meta-name">Validation WAPE:</span>
                              <span className="meta-val highlight">{detail.wape.toFixed(2)}%</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="inspector-wrapper">
                    <div className="inspector-header">
                      <button
                        type="button"
                        className="inspector-toggle"
                        onClick={() => setShowInspector(!showInspector)}
                      >
                        {showInspector ? '▼ Hide Raw HTTP Inspector' : '▶ Show Raw HTTP Inspector (Viva Demonstration)'}
                      </button>
                      {showInspector && (
                        <div className="inspector-tabs">
                          <button
                            type="button"
                            className={`tab-btn ${activeInspectorTab === 'response' ? 'active' : ''}`}
                            onClick={() => setActiveInspectorTab('response')}
                          >
                            HTTP 200 Response
                          </button>
                          <button
                            type="button"
                            className={`tab-btn ${activeInspectorTab === 'request' ? 'active' : ''}`}
                            onClick={() => setActiveInspectorTab('request')}
                          >
                            POST Request Payload
                          </button>
                        </div>
                      )}
                    </div>

                    {showInspector && (
                      <pre className="inspector-code">
                        {activeInspectorTab === 'response'
                          ? JSON.stringify(forecastResult, null, 2)
                          : JSON.stringify(lastPayload, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>
          NEXORA v0.1.0 • Unified Retail Intelligence Dashboard (M06 Business Intelligence • M08 Product Lifecycle Intelligence • M12 Baseline)
        </p>
      </footer>
    </div>
  )
}

export const App: React.FC = () => (
  <WorkspaceProvider>
    <NexoraShell />
  </WorkspaceProvider>
)

export default App
