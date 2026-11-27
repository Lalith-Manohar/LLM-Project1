import React, { useEffect, useState } from 'react'
import { LifecycleSettingItem } from '../types'

interface LifecycleSettingsPanelProps {
  settings: LifecycleSettingItem[]
  isStoreManager: boolean
  saving: boolean
  error: string | null
  successMessage: string | null
  onSave: (updates: Record<string, string | number | undefined>) => void
  onReset: (operatorRef?: string) => void
}

/**
 * Bounded DDR-08 lifecycle settings administration panel with min/max validation,
 * forward-only preservation notice, and Reset-to-Default action.
 */
export const LifecycleSettingsPanel: React.FC<LifecycleSettingsPanelProps> = ({
  settings,
  isStoreManager,
  saving,
  error,
  successMessage,
  onSave,
  onReset
}) => {
  const [draftValues, setDraftValues] = useState<Record<string, string>>({})
  const [operatorRef, setOperatorRef] = useState<string>('')
  const [localError, setLocalError] = useState<string | null>(null)
  const [confirmResetOpen, setConfirmResetOpen] = useState<boolean>(false)

  useEffect(() => {
    const initial: Record<string, string> = {}
    settings.forEach((s) => {
      initial[s.setting_key] = String(s.setting_value)
    })
    setDraftValues(initial)
  }, [settings])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError(null)
    const payload: Record<string, string | number | undefined> = {}
    const errors: string[] = []

    for (const spec of settings) {
      const raw = (draftValues[spec.setting_key] ?? '').trim()
      const num = Number(raw)
      if (!raw || Number.isNaN(num)) {
        errors.push(`${spec.setting_key} must be a valid number.`)
        continue
      }
      if (num < Number(spec.min_bound) || num > Number(spec.max_bound)) {
        errors.push(
          `${spec.setting_key} (${num}) must be within [${spec.min_bound}, ${spec.max_bound}].`
        )
        continue
      }
      payload[spec.setting_key] = spec.value_type === 'INTEGER' ? Math.trunc(num) : raw
    }

    if (errors.length > 0) {
      setLocalError(errors.join(' '))
      return
    }
    if (operatorRef.trim()) {
      payload.operator_ref = operatorRef.trim()
    }
    onSave(payload)
  }

  return (
    <div className="card">
      <div className="module-header-row">
        <div>
          <h3>Bounded Lifecycle Thresholds (`operational_settings` — DDR-08)</h3>
          <p className="section-desc">
            Changes apply strictly to <strong>future</strong> evaluations and never rewrite historical{' '}
            <code>product_lifecycle_snapshots</code>. All updates write a Tier 1 fail-closed audit entry.
          </p>
        </div>
        {isStoreManager && (
          <button
            type="button"
            className="btn-ghost-sm"
            disabled={saving}
            onClick={() => setConfirmResetOpen(true)}
          >
            Reset to System Defaults
          </button>
        )}
      </div>

      {!isStoreManager && (
        <div className="alert alert-warning">
          <span className="alert-icon">ℹ️</span>
          <div>
            <strong>Read-Only View:</strong> Switch workspace to <strong>Store Manager (Admin)</strong> to modify
            bounded lifecycle thresholds or reset defaults (UI workflow governance per DDR-08).
          </div>
        </div>
      )}

      {(localError || error) && (
        <div className="alert alert-error" role="alert">
          <span className="alert-icon">⚠️</span>
          <div>{localError || error}</div>
        </div>
      )}

      {successMessage && (
        <div className="alert alert-success" role="status">
          <span className="alert-icon">✅</span>
          <div>{successMessage}</div>
        </div>
      )}

      {confirmResetOpen && (
        <div className="inline-confirm-box">
          <span>Reset all 7 lifecycle parameters to approved system defaults (Tier 1 audited)?</span>
          <div className="inline-confirm-actions">
            <button
              type="button"
              className="btn-ghost-sm"
              onClick={() => setConfirmResetOpen(false)}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn-danger-sm"
              disabled={saving}
              onClick={() => {
                setConfirmResetOpen(false)
                onReset(operatorRef.trim() || undefined)
              }}
            >
              Confirm Reset Defaults
            </button>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="settings-grid">
          {settings.map((spec) => (
            <div key={spec.setting_key} className="setting-card">
              <div className="setting-card-head">
                <label htmlFor={`set-${spec.setting_key}`} className="mono">
                  {spec.setting_key}
                </label>
                <span className="bounds-tag">
                  Bounds: [{spec.min_bound}, {spec.max_bound}] • Default: {spec.default_value}
                </span>
              </div>
              <p className="field-hint">{spec.description}</p>
              <input
                id={`set-${spec.setting_key}`}
                type="number"
                step={spec.value_type === 'INTEGER' ? '1' : '0.01'}
                className="input-text"
                disabled={!isStoreManager || saving}
                value={draftValues[spec.setting_key] ?? ''}
                onChange={(e) =>
                  setDraftValues((prev) => ({ ...prev, [spec.setting_key]: e.target.value }))
                }
              />
            </div>
          ))}
        </div>

        {isStoreManager && (
          <div className="settings-footer">
            <div className="filter-field" style={{ maxWidth: '280px' }}>
              <label htmlFor="settings-operator-ref">Optional Operator Ref (Audit Provenance)</label>
              <input
                id="settings-operator-ref"
                type="text"
                maxLength={64}
                className="input-text"
                placeholder="e.g. STORE-MGR-01"
                value={operatorRef}
                onChange={(e) => setOperatorRef(e.target.value)}
              />
            </div>
            <button type="submit" className="btn-primary-sm" disabled={saving}>
              {saving ? 'Saving & Auditing...' : 'Save Bounded Thresholds'}
            </button>
          </div>
        )}
      </form>
    </div>
  )
}
