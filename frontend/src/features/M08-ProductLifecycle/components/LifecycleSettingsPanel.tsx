import { useEffect, useState, type FormEvent } from 'react'
import { RotateCcw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import type { LifecycleSettingItem } from '../types'

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
 * Bounded DDR-08 lifecycle settings administration panel (`operational_settings`),
 * enforcing min/max bounds, forward-only preservation, and Reset-to-Default.
 */
export function LifecycleSettingsPanel({
  settings,
  isStoreManager,
  saving,
  error,
  successMessage,
  onSave,
  onReset,
}: LifecycleSettingsPanelProps) {
  const [draftValues, setDraftValues] = useState<Record<string, string>>({})
  const [operatorRef, setOperatorRef] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)
  const [confirmResetOpen, setConfirmResetOpen] = useState(false)

  useEffect(() => {
    const initial: Record<string, string> = {}
    settings.forEach((s) => {
      initial[s.setting_key] = String(s.setting_value)
    })
    setDraftValues(initial)
  }, [settings])

  const handleSubmit = (e: FormEvent) => {
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
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-lg">
              Bounded Lifecycle Thresholds (operational_settings — DDR-08)
            </CardTitle>
            <CardDescription>
              Updates apply strictly to <strong>future</strong> evaluations and never rewrite existing{' '}
              <code>product_lifecycle_snapshots</code>. All updates emit a Tier 1 fail-closed audit log.
            </CardDescription>
          </div>
          {isStoreManager && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={saving}
              onClick={() => setConfirmResetOpen(true)}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset to System Defaults
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {!isStoreManager && (
          <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-950">
            <strong>Read-Only View:</strong> Switch workspace to{' '}
            <strong>Store Manager (Admin)</strong> to modify bounded lifecycle thresholds or reset defaults (DDR-08 UI governance).
          </div>
        )}

        {(localError || error) && (
          <div
            role="alert"
            className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            {localError || error}
          </div>
        )}

        {successMessage && (
          <div
            role="status"
            className="rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-900"
          >
            {successMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {settings.map((spec) => (
              <div key={spec.setting_key} className="space-y-2 rounded-lg border bg-muted/30 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <label
                    htmlFor={`set-${spec.setting_key}`}
                    className="font-mono text-xs font-semibold text-foreground"
                  >
                    {spec.setting_key}
                  </label>
                  <Badge variant="outline" className="font-mono text-[11px]">
                    [{spec.min_bound}, {spec.max_bound}] • Default: {spec.default_value}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">{spec.description}</p>
                <Input
                  id={`set-${spec.setting_key}`}
                  type="number"
                  step={spec.value_type === 'INTEGER' ? '1' : '0.01'}
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
            <div className="flex flex-wrap items-end justify-between gap-3 border-t pt-4">
              <div className="w-full max-w-xs space-y-1">
                <label
                  htmlFor="settings-operator-ref"
                  className="text-xs font-medium text-muted-foreground"
                >
                  Optional Operator Ref (Audit Provenance)
                </label>
                <Input
                  id="settings-operator-ref"
                  type="text"
                  maxLength={64}
                  placeholder="e.g. STORE-MGR-01"
                  value={operatorRef}
                  onChange={(e) => setOperatorRef(e.target.value)}
                />
              </div>
              <Button type="submit" size="sm" disabled={saving}>
                {saving ? 'Saving & Auditing...' : 'Save Bounded Thresholds'}
              </Button>
            </div>
          )}
        </form>
      </CardContent>

      <Dialog open={confirmResetOpen} onOpenChange={setConfirmResetOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset Lifecycle Thresholds to System Defaults?</DialogTitle>
            <DialogDescription>
              Restores all lifecycle configuration parameters to approved system defaults forward-only and logs a Tier 1{' '}
              <code>LIFECYCLE_CONFIG_RESET</code> audit event. Prior snapshots remain unchanged.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setConfirmResetOpen(false)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              size="sm"
              disabled={saving}
              onClick={() => {
                setConfirmResetOpen(false)
                onReset(operatorRef.trim() || undefined)
              }}
            >
              Confirm Reset Defaults
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
