// =============================================================================
// RestaurantFlow — Tax Rates Page
// Phase 5
// =============================================================================

import { useState } from 'react'
import {
  useTaxRates,
  useCreateTaxRate,
  useUpdateTaxRate,
  useDisableTaxRate,
  useEnableTaxRate,
} from '@/hooks/useMenu'
import { useAllRestaurants as useRestaurants } from '@/hooks/useRestaurants'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/Button'
import { Modal, ConfirmDialog } from '@/components/ui/Modal'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/contexts/AuthContext'
import type { TaxRate, TaxRateCreatePayload, TaxRateUpdatePayload } from '@/types'

// ---------------------------------------------------------------------------
// Form
// ---------------------------------------------------------------------------

function TaxRateForm({
  initialValues,
  onSubmit,
  onCancel,
  loading,
  submitLabel = 'Save',
  restaurantId,
}: {
  initialValues?: Partial<TaxRate>
  onSubmit: (data: TaxRateCreatePayload | TaxRateUpdatePayload) => void
  onCancel: () => void
  loading?: boolean
  submitLabel?: string
  restaurantId?: string
}) {
  const { data: restaurantsData } = useRestaurants()
  const [form, setForm] = useState({
    restaurant: initialValues?.restaurant ?? restaurantId ?? '',
    name: initialValues?.name ?? '',
    code: initialValues?.code ?? '',
    rate: initialValues?.rate ?? '',
    description: initialValues?.description ?? '',
  })

  const field = (key: keyof typeof form) => ({
    value: form[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((p) => ({ ...p, [key]: e.target.value })),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit(form)
  }

  const inputClass =
    'w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-brand-500 placeholder-gray-600'
  const labelClass = 'block text-xs text-gray-500 mb-1.5'

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {!initialValues && (
        <div>
          <label className={labelClass}>Restaurant *</label>
          <select className={inputClass} {...field('restaurant')} required>
            <option value="">Select restaurant…</option>
            {restaurantsData?.results.map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        </div>
      )}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass}>Name *</label>
          <input className={inputClass} placeholder="GST Standard" required {...field('name')} />
        </div>
        <div>
          <label className={labelClass}>Code *</label>
          <input
            className={inputClass}
            placeholder="GST_STANDARD"
            required
            {...field('code')}
            style={{ textTransform: 'uppercase' }}
          />
        </div>
      </div>
      <div>
        <label className={labelClass}>Rate (%) *</label>
        <input
          className={inputClass}
          type="number"
          min="0"
          step="0.001"
          placeholder="5.000"
          required
          {...field('rate')}
        />
        <p className="mt-1 text-xs text-gray-600">
          Enter percentage value, e.g. 5.000 = 5%. For development/demo only — not legal tax advice.
        </p>
      </div>
      <div>
        <label className={labelClass}>Description</label>
        <textarea
          className={inputClass}
          rows={2}
          placeholder="Optional description…"
          {...field('description')}
        />
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <Button variant="ghost" type="button" onClick={onCancel}>Cancel</Button>
        <Button variant="primary" type="submit" loading={loading}>{submitLabel}</Button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function TaxRates() {
  const { hasPermission } = useAuth()
  const { toast } = useToast()

  const [restaurantFilter, setRestaurantFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [editTarget, setEditTarget] = useState<TaxRate | null>(null)
  const [confirmAction, setConfirmAction] = useState<{
    type: 'disable' | 'enable'
    rate: TaxRate
  } | null>(null)

  const params: Record<string, string | number> = {}
  if (restaurantFilter) params.restaurant = restaurantFilter

  const { data, isLoading, isError } = useTaxRates(params)
  const { data: restaurantsData } = useRestaurants()
  const createMut = useCreateTaxRate()
  const updateMut = useUpdateTaxRate(editTarget?.id ?? '')
  const disableMut = useDisableTaxRate()
  const enableMut = useEnableTaxRate()

  const canCreate = hasPermission('tax.create')
  const canUpdate = hasPermission('tax.update')

  async function handleCreate(payload: TaxRateCreatePayload | TaxRateUpdatePayload) {
    try {
      await createMut.mutateAsync(payload as TaxRateCreatePayload)
      setShowCreate(false)
      toast('Tax rate created.', 'success')
    } catch {
      toast('Failed to create tax rate.', 'error')
    }
  }

  async function handleUpdate(payload: TaxRateCreatePayload | TaxRateUpdatePayload) {
    if (!editTarget) return
    try {
      await updateMut.mutateAsync(payload as TaxRateUpdatePayload)
      setEditTarget(null)
      toast('Tax rate updated.', 'success')
    } catch {
      toast('Failed to update tax rate.', 'error')
    }
  }

  async function handleConfirm() {
    if (!confirmAction) return
    try {
      if (confirmAction.type === 'disable') {
        await disableMut.mutateAsync(confirmAction.rate.id)
        toast(`"${confirmAction.rate.name}" disabled.`, 'warning')
      } else {
        await enableMut.mutateAsync(confirmAction.rate.id)
        toast(`"${confirmAction.rate.name}" enabled.`, 'success')
      }
    } catch {
      toast('Action failed.', 'error')
    } finally {
      setConfirmAction(null)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title="Tax Rates"
        description="Restaurant-scoped tax configuration. Demo values only — not legal advice."
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Menu', to: '/menu' }, { label: 'Tax Rates' }]}
        actions={
          canCreate ? (
            <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
              + Add Tax Rate
            </Button>
          ) : undefined
        }
      />

      {/* Filter */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          aria-label="Filter by restaurant"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-500"
          value={restaurantFilter}
          onChange={(e) => setRestaurantFilter(e.target.value)}
        >
          <option value="">All Restaurants</option>
          {restaurantsData?.results.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-14 bg-gray-900/60 border border-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      )}
      {isError && (
        <div className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400" role="alert">
          Failed to load tax rates.
        </div>
      )}

      {!isLoading && data?.results.length === 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-6 py-12 text-center">
          <p className="text-gray-500 text-sm">No tax rates found.</p>
        </div>
      )}

      {!isLoading && data && data.results.length > 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 overflow-hidden">
          <table className="w-full text-sm" role="table">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Code</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Name</th>
                <th className="text-right px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Rate</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden sm:table-cell">Restaurant</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Status</th>
                <th className="px-4 py-3" aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {data.results.map((rate) => (
                <tr key={rate.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs text-gray-400 bg-gray-800 px-2 py-0.5 rounded">
                      {rate.code}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-200">{rate.name}</td>
                  <td className="px-4 py-3 text-right font-mono text-brand-400 font-medium">
                    {Number(rate.rate).toFixed(3)}%
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs hidden sm:table-cell">
                    {rate.restaurant_name}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${
                      rate.is_active
                        ? 'bg-green-500/10 text-green-400 border-green-500/20'
                        : 'bg-gray-700/30 text-gray-500 border-gray-700/30'
                    }`}>
                      {rate.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {canUpdate && (
                        <Button variant="ghost" size="sm" onClick={() => setEditTarget(rate)}>
                          Edit
                        </Button>
                      )}
                      {canUpdate && rate.is_active && (
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => setConfirmAction({ type: 'disable', rate })}
                        >
                          Disable
                        </Button>
                      )}
                      {canUpdate && !rate.is_active && (
                        <Button
                          variant="success"
                          size="sm"
                          onClick={() => setConfirmAction({ type: 'enable', rate })}
                        >
                          Enable
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-700">
            {data.count} rate{data.count !== 1 ? 's' : ''}
          </div>
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Add Tax Rate">
        <TaxRateForm
          onSubmit={handleCreate}
          onCancel={() => setShowCreate(false)}
          loading={createMut.isPending}
          submitLabel="Create Tax Rate"
        />
      </Modal>

      <Modal open={!!editTarget} onClose={() => setEditTarget(null)} title="Edit Tax Rate">
        {editTarget && (
          <TaxRateForm
            initialValues={editTarget}
            onSubmit={handleUpdate}
            onCancel={() => setEditTarget(null)}
            loading={updateMut.isPending}
            submitLabel="Save Changes"
          />
        )}
      </Modal>

      <ConfirmDialog
        open={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={handleConfirm}
        title={
          confirmAction?.type === 'disable'
            ? `Disable "${confirmAction.rate.name}"?`
            : `Enable "${confirmAction?.rate.name}"?`
        }
        message={
          confirmAction?.type === 'disable'
            ? 'This tax rate will be marked inactive.'
            : 'This tax rate will be re-enabled.'
        }
        confirmLabel={confirmAction?.type === 'disable' ? 'Disable' : 'Enable'}
        confirmVariant={confirmAction?.type === 'disable' ? 'danger' : 'success'}
        loading={disableMut.isPending || enableMut.isPending}
      />
    </div>
  )
}
