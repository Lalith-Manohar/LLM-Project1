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
  { code: '85123A', name: 'White Hanging Heart T-Light Holder (Top Catalog SKU)' },
  { code: '71053', name: 'White Metal Lantern' },
  { code: '21777', name: 'Recipe Box with Metal Heart' },
  { code: 'NEW_UNSEEN_SKU_DEMO', name: 'Unseen SKU (Tests Infrequent Category Fallback)' },
]

// Preset verified historical demonstration features
const SAMPLE_FEATURES = {
  day_of_week: 2, // Wednesday
  month: 11,     // November
  day_of_month: 15,
  lag_1: 12.0,
  lag_7: 15.0,
  lag_14: 10.0,
  lag_28: 14.0,
  rolling_mean_7: 13.5,
  rolling_mean_28: 12.8
}

export const App: React.FC = () => {
  // Backend connectivity state
  const [backendHealth, setBackendHealth] = useState<HealthResponse | null>(null)
  const [healthStatus, setHealthStatus] = useState<'checking' | 'online' | 'offline'>('checking')

  // Form input state
  const [stockCode, setStockCode] = useState<string>('85123A')
  const [selectedHorizons, setSelectedHorizons] = useState<number[]>([7, 15, 30, 90])
  const [features, setFeatures] = useState(SAMPLE_FEATURES)
  const [isSampleLoaded, setIsSampleLoaded] = useState<boolean>(true)

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

  // Handle feature input changes
  const handleFeatureChange = (field: keyof typeof SAMPLE_FEATURES, value: string) => {
    const num = parseFloat(value)
    setFeatures(prev => ({
      ...prev,
      [field]: isNaN(num) ? 0 : num
    }))
    setIsSampleLoaded(false)
  }

  // Load sample demonstration values
  const handleLoadSample = () => {
    setFeatures(SAMPLE_FEATURES)
    setIsSampleLoaded(true)
  }

  // Submit forecast prediction request
  const handleGenerateForecast = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)
    setLoading(true)

    const payload: ForecastRequest = {
      stock_code: stockCode.trim(),
      horizons: selectedHorizons,
      features: {
        day_of_week: Number(features.day_of_week),
        month: Number(features.month),
        day_of_month: Number(features.day_of_month),
        lag_1: Number(features.lag_1),
        lag_7: Number(features.lag_7),
        lag_14: Number(features.lag_14),
        lag_28: Number(features.lag_28),
        rolling_mean_7: Number(features.rolling_mean_7),
        rolling_mean_28: Number(features.rolling_mean_28)
      }
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
            <p className="brand-subtitle">Retail Management & Intelligence System</p>
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
                Select an SKU and target horizons to query real-time multi-horizon ML regression predictions from FastAPI.
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
                      onClick={() => setStockCode(item.code)}
                      title={item.name}
                    >
                      {item.code}
                    </button>
                  ))}
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

              {/* Historical Feature Input Grid */}
              <div className="form-group">
                <div className="feature-header-row">
                  <label>Historical Features Vector</label>
                  <button
                    type="button"
                    className={`btn-sample ${isSampleLoaded ? 'active' : ''}`}
                    onClick={handleLoadSample}
                  >
                    ✓ Load Demonstration Sample
                  </button>
                </div>
                <p className="field-hint demo-notice">
                  {isSampleLoaded
                    ? '★ Currently loaded: Verified demonstration features representing a medium-demand product.'
                    : 'Custom feature values entered.'}
                </p>

                <div className="features-grid">
                  <div className="feature-field">
                    <label>Lag 1 Day (t-1)</label>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={features.lag_1}
                      onChange={(e) => handleFeatureChange('lag_1', e.target.value)}
                      required
                    />
                  </div>
                  <div className="feature-field">
                    <label>Lag 7 Days (t-7)</label>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={features.lag_7}
                      onChange={(e) => handleFeatureChange('lag_7', e.target.value)}
                      required
                    />
                  </div>
                  <div className="feature-field">
                    <label>Lag 14 Days (t-14)</label>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={features.lag_14}
                      onChange={(e) => handleFeatureChange('lag_14', e.target.value)}
                      required
                    />
                  </div>
                  <div className="feature-field">
                    <label>Lag 28 Days (t-28)</label>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={features.lag_28}
                      onChange={(e) => handleFeatureChange('lag_28', e.target.value)}
                      required
                    />
                  </div>
                  <div className="feature-field">
                    <label>Rolling Mean 7d</label>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={features.rolling_mean_7}
                      onChange={(e) => handleFeatureChange('rolling_mean_7', e.target.value)}
                      required
                    />
                  </div>
                  <div className="feature-field">
                    <label>Rolling Mean 28d</label>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={features.rolling_mean_28}
                      onChange={(e) => handleFeatureChange('rolling_mean_28', e.target.value)}
                      required
                    />
                  </div>
                </div>

                {/* Calendar Features Row */}
                <div className="calendar-grid">
                  <div className="calendar-field">
                    <label>Day of Week (0=Mon)</label>
                    <input
                      type="number"
                      min="0"
                      max="6"
                      value={features.day_of_week}
                      onChange={(e) => handleFeatureChange('day_of_week', e.target.value)}
                    />
                  </div>
                  <div className="calendar-field">
                    <label>Month (1-12)</label>
                    <input
                      type="number"
                      min="1"
                      max="12"
                      value={features.month}
                      onChange={(e) => handleFeatureChange('month', e.target.value)}
                    />
                  </div>
                  <div className="calendar-field">
                    <label>Day of Month (1-31)</label>
                    <input
                      type="number"
                      min="1"
                      max="31"
                      value={features.day_of_month}
                      onChange={(e) => handleFeatureChange('day_of_month', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                className="btn-submit"
                disabled={loading || selectedHorizons.length === 0}
              >
                {loading ? (
                  <span className="spinner-text">
                    <span className="spinner"></span> Querying FastAPI ML Inference...
                  </span>
                ) : (
                  `Execute Forecast (${selectedHorizons.length} Horizons)`
                )}
              </button>
            </form>
          </div>

          {/* Right Column: Prediction Results & Output Cards */}
          <div className="card results-card">
            <div className="card-header">
              <h2>Forecast Intelligence Outputs</h2>
              <p className="section-desc">
                Live empirical predictions returned over HTTP by FastAPI from trained Joblib models.
              </p>
            </div>

            {/* Error Message Display */}
            {errorMessage && (
              <div className="alert alert-error">
                <div className="alert-icon">⚠️</div>
                <div className="alert-content">
                  <strong>Request Error:</strong> {errorMessage}
                </div>
              </div>
            )}

            {/* Empty State before first prediction */}
            {!loading && !forecastResult && !errorMessage && (
              <div className="empty-state">
                <div className="empty-icon">📈</div>
                <h3>No Prediction Executed Yet</h3>
                <p>
                  Select a product SKU and planning horizons on the left, then click <strong>Execute Forecast</strong> to query the ML models.
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
                <p className="loading-title">Communicating with FastAPI...</p>
                <p className="loading-subtitle">Invoking scikit-learn Ridge & Random Forest estimators</p>
              </div>
            )}

            {/* Results Presentation */}
            {forecastResult && !loading && (
              <div className="results-container">
                {/* Meta summary header */}
                <div className="results-meta-bar">
                  <div>
                    <span className="meta-label">Product SKU:</span>
                    <strong className="meta-value">{forecastResult.stock_code}</strong>
                  </div>
                  <div>
                    <span className="meta-label">Status:</span>
                    <span className="badge badge-success">{forecastResult.status.toUpperCase()}</span>
                  </div>
                  <div>
                    <span className="meta-label">Timestamp:</span>
                    <span className="meta-time">{new Date(forecastResult.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>

                {/* Warnings Section (e.g. for unseen SKUs) */}
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
                            {detail.model_name.includes('Ridge') ? 'Ridge Regression' : 'Random Forest'}
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
                          HTTP POST Request Body
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
          NEXORA Phase 1 Demonstration Client &bull; Communicating directly via HTTP with FastAPI Backend on{' '}
          <code>http://localhost:8000</code> &bull; Academic Viva Ready
        </p>
      </footer>
    </div>
  )
}

export default App
