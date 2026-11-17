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
import './App.css'

// Preset demo product SKUs from UCI Online Retail II dataset
const DEMO_SKUS = [
  { code: '85123A', name: 'White Hanging Heart T-Light Holder (High-volume active SKU, 374 days history)' },
  { code: '71053', name: 'White Metal Lantern (Medium-volume active SKU, 374 days history)' },
  { code: '85099B', name: 'Jumbo Bag Red Retrospot (Top high-demand active SKU, 374 days history)' },
  { code: '22423', name: 'Regency Cakestand 3 Tier (Core active SKU, 374 days history)' },
  { code: '21777', name: 'Recipe Box with Metal Heart (6 days lifespan — tests insufficient history validation)' },
]

export const App: React.FC = () => {
  // Backend connectivity state
  const [backendHealth, setBackendHealth] = useState<HealthResponse | null>(null)
  const [healthStatus, setHealthStatus] = useState<'checking' | 'online' | 'offline'>('checking')

  // Form input state
  const [stockCode, setStockCode] = useState<string>('85123A')
  const [selectedHorizons, setSelectedHorizons] = useState<number[]>([7, 15, 30, 90])

  // Request & Response state
  const [loading, setLoading] = useState<boolean>(false)
  const [forecastResult, setForecastResult] = useState<ForecastResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Debug/Viva inspector state
  const [lastPayload, setLastPayload] = useState<ForecastRequest | null>(null)
  const [showInspector, setShowInspector] = useState<boolean>(false)
  const [activeInspectorTab, setActiveInspectorTab] = useState<'request' | 'response'>('response')

  // Check backend health on initial load
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

  // Toggle horizon selection
  const toggleHorizon = (h: number) => {
    if (selectedHorizons.includes(h)) {
      if (selectedHorizons.length === 1) return // Keep at least one
      setSelectedHorizons(selectedHorizons.filter(x => x !== h))
    } else {
      setSelectedHorizons([...selectedHorizons, h].sort((a, b) => a - b))
    }
  }

  // Switch SKU preset
  const handleSelectSku = (code: string) => {
    setStockCode(code)
    setErrorMessage(null)
  }

  // Submit forecast prediction request
  const handleGenerateForecast = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)
    setLoading(true)

    // Simplified SKU-only payload: backend automatically calculates the 9 ML features from CSV!
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

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-logo">
            <svg viewBox="0 0 32 32" width="28" height="28">
              <rect width="32" height="32" rx="8" fill="#1e3a8a"/>
              <path d="M7 23 L13 15 L18 19 L25 9" fill="none" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
              <circle cx="25" cy="9" r="2.5" fill="#38bdf8"/>
            </svg>
          </div>
          <div>
            <h1 className="brand-title">NEXORA</h1>
            <p className="brand-subtitle">AI-Powered Retail Management & Intelligence System</p>
          </div>
        </div>

        <div className="header-meta">
          <span className="badge milestone-badge">Phase 1 Milestone</span>
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

      {/* Main Content Layout */}
      <main className="main-content">
        <div className="grid-layout">
          {/* Left Column: Form & Inputs */}
          <div className="card control-card">
            <div className="card-header">
              <h2>Demand Forecasting Simulator</h2>
              <p className="section-desc">
                Select a product SKU and planning horizons to query multi-horizon ML demand regression forecasts from FastAPI.
              </p>
            </div>

            <form onSubmit={handleGenerateForecast}>
              {/* Product SKU Selector */}
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
                
                {/* SKU Preset Quick-Pills */}
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

              {/* Automatic Pipeline Information Notice */}
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

              {/* Planning Horizon Selector */}
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

              {/* Submit Button */}
              <button
                type="submit"
                className="btn-submit"
                disabled={loading || selectedHorizons.length === 0}
              >
                {loading ? (
                  <span className="spinner-text">
                    <span className="spinner"></span> Processing Historical Sales & Running ML Models...
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

            {/* Error Notification */}
            {errorMessage && (
              <div className="alert alert-error">
                <div className="alert-icon">⚠️</div>
                <div className="alert-content">
                  <strong>Prediction Failed:</strong> {errorMessage}
                </div>
              </div>
            )}

            {/* Empty State */}
            {!forecastResult && !loading && !errorMessage && (
              <div className="empty-state">
                <div className="empty-icon">📈</div>
                <h3>No Prediction Executed Yet</h3>
                <p>
                  Select a product SKU and target horizons on the left, then click <strong>Generate Forecast</strong>. NEXORA will automatically retrieve the historical sales history and compute predictions.
                </p>
                <div className="endpoint-tag">
                  Target Endpoint: <code>POST http://localhost:8000/api/v1/forecast/</code>
                </div>
              </div>
            )}

            {/* In-Flight Spinner State */}
            {loading && (
              <div className="loading-state">
                <div className="large-spinner"></div>
                <p className="loading-title">Retrieving Historical Sales & Executing Inference...</p>
                <p className="loading-subtitle">Filtering continuous daily records & evaluating scikit-learn estimators</p>
              </div>
            )}

            {/* Results Presentation */}
            {forecastResult && !loading && (
              <div className="results-container">
                {/* Meta summary header with Observation Date Transparency */}
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

                {/* Warnings Section (e.g. for unseen SKUs or data notes) */}
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

                {/* Horizon Prediction Cards Grid */}
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

                {/* Raw HTTP Inspector Drawer for Academic Viva Demo */}
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
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>
          NEXORA v0.1.0 (Phase 1 Milestone) • Multi-Horizon Retail Intelligence Engine • Powered by FastAPI & Scikit-learn
        </p>
      </footer>
    </div>
  )
}

export default App
