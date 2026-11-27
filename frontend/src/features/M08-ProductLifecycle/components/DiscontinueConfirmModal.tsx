import { useState, type FormEvent } from 'react'
import { ShieldAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import type { LifecycleSkuSummary } from '../types'

interface DiscontinueConfirmModalProps {
  sku: LifecycleSkuSummary | null
  submitting: boolean
  error: string | null
  onCancel: () => void
  onConfirm: (payload: { reason: string; operatorRef?: string }) => void
}

/**
 * Mandatory confirmation dialog before manual `Discontinued` transition
 * (DDR-08, DDR-10 Tier 1 fail-closed audit, EXCL-04).
 */
export function DiscontinueConfirmModal({
  sku,
  submitting,
  error,
  onCancel,
  onConfirm,
}: DiscontinueConfirmModalProps) {
  const [reason, setReason] = useState('')
  const [operatorRef, setOperatorRef] = useState('')
  const [acknowledged, setAcknowledged] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  const handleSubmit = (e: FormEvent) => {
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
      operatorRef: operatorRef.trim() || undefined,
    })
  }

  return (
    <Dialog open={sku !== null} onOpenChange={(open) => !open && onCancel()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirm Manual Product Discontinuation</DialogTitle>
          <DialogDescription>
            {sku && (
              <>
                Transition SKU <code className="font-mono font-semibold">{sku.stock_code}</code> (
                {sku.description}) from <strong>{sku.lifecycle_stage}</strong> to{' '}
                <strong>Discontinued</strong>.
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-950">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <strong>DDR-08 &amp; DDR-10 Governance:</strong> Appends an immutable{' '}
            <code>manual_discontinued</code> snapshot and commits a{' '}
            <strong>Tier 1 fail-closed audit log</strong>. Per <strong>EXCL-04</strong>, zero autonomous price markdowns are triggered.
          </div>
        </div>

        {(localError || error) && (
          <div
            role="alert"
            className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive"
          >
            {localError || error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="discontinue-reason" className="text-xs font-semibold text-foreground">
              Discontinuation Reason *
            </label>
            <textarea
              id="discontinue-reason"
              rows={3}
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Supplier discontinued product line after seasonal clearance review"
              className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>

          <div className="space-y-1">
            <label htmlFor="discontinue-operator" className="text-xs font-semibold text-foreground">
              Optional Operator Reference (Non-Auth Provenance)
            </label>
            <Input
              id="discontinue-operator"
              type="text"
              maxLength={64}
              value={operatorRef}
              onChange={(e) => setOperatorRef(e.target.value)}
              placeholder="e.g. OPS-LEAD-01 (optional)"
            />
          </div>

          <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-foreground">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
            />
            <span>
              I explicitly confirm transitioning <strong>{sku?.stock_code}</strong> to{' '}
              <strong>Discontinued</strong>.
            </span>
          </label>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" size="sm" onClick={onCancel} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" size="sm" disabled={submitting}>
              {submitting ? 'Committing & Auditing...' : 'Confirm Discontinue'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
