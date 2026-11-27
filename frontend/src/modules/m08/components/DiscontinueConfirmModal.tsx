import React, { useState } from 'react'
import { LifecycleSkuSummary } from '../types'

interface DiscontinueConfirmModalProps {
  sku: LifecycleSkuSummary
  submitting: boolean
  error: string | null
  onCancel: () => void
  onConfirm: (payload: { reason: string; operatorRef?: string }) => void
}

/**
 * Mandatory explicit confirmation modal before executing manual `Discontinued` transition
 * (AGENTS.md Section 10 rule 9, DDR-08, DDR-10 Tier 1 fail-closed audit, EXCL-04).
 */
export const DiscontinueConfirmModal: React.FC<DiscontinueConfirmModalProps> = ({
  sku,
  submitting,
  error,
  onCancel,
  onConfirm
}) => {
  const [reason, setReason] = useState<string>('')
  const [operatorRef, setOperatorRef] = useState<string>('')
  const [acknowledged, setAcknowledged] = useState<boolean>(false)
  const [localError, setLocalError] = useState<string | null>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = reason.trim()
    if (trimmed.length < 3) {
      setLocalError('Please provide a clear discontinuation reason (at least 3 characters).')
      return
    }
    if (!acknowledged) {
      setLocalError('You must explicitly check the confirmation box to authorize Discontinued status.')
      return
    }
    setLocalError(null)
    onConfirm({
      reason: trimmed,
      operatorRef: operatorRef.trim() || undefined
    })
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="discontinue-modal-title">
      <div className="modal-card">
        <div className="modal-header">
          <h3 id="discontinue-modal-title">Confirm Manual Product Discontinuation</h3>
          <button type="button" className="btn-close" onClick={onCancel} aria-label="Close modal">
            ×
          </button>
        </div>

        <p className="modal-lead">
          You are about to transition SKU <code className="mono">{sku.stock_code}</code> ({sku.description}) from{' '}
          <strong>{sku.lifecycle_stage}</strong> to <strong>Discontinued</strong>.
        </p>

        <div className="alert alert-warning">
          <span className="alert-icon">🛡️</span>
          <div>
            <strong>DDR-08 &amp; DDR-10 Governance:</strong> This action appends an immutable{' '}
            <code>manual_discontinued</code> snapshot and writes a <strong>Tier 1 fail-closed audit log</strong>.
            Per <strong>EXCL-04</strong>, no autonomous price markdowns will be triggered.
          </div>
        </div>

        {(localError || error) && (
          <div className="alert alert-error" role="alert">
            <span className="alert-icon">⚠️</span>
            <div>{localError || error}</div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="discontinue-reason">
              Discontinuation Reason <span className="required">*</span>
            </label>
            <textarea
              id="discontinue-reason"
              className="input-text"
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Supplier discontinued product line after seasonal clearance review"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="discontinue-operator">Optional Operator Reference (Non-Auth Provenance)</label>
            <input
              id="discontinue-operator"
              type="text"
              className="input-text"
              maxLength={64}
              value={operatorRef}
              onChange={(e) => setOperatorRef(e.target.value)}
              placeholder="e.g. OPS-LEAD-01 (optional)"
            />
          </div>

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
            />
            <span>
              I explicitly confirm transitioning <strong>{sku.stock_code}</strong> to <strong>Discontinued</strong>.
            </span>
          </label>

          <div className="modal-actions">
            <button type="button" className="btn-ghost-sm" onClick={onCancel} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn-danger-sm" disabled={submitting}>
              {submitting ? 'Committing & Auditing...' : 'Confirm Discontinue'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
