// =============================================================================
// RestaurantFlow — Availability Page
// Phase 5
// =============================================================================

import { useState } from 'react'
import {
  useAvailabilityList,
  useCreateAvailability,
  useUpdateAvailability,
  useMenuItems,
} from '@/hooks/useMenu'
import { useAllBranches } from '@/hooks/useBranches'
import { useAllRestaurants as useRestaurants } from '@/hooks/useRestaurants'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/contexts/AuthContext'
import type { MenuItemBranch, MenuItemBranchCreatePayload } from '@/types'

function AvailabilityForm({
  onSubmit,
  onCancel,
  loading,
}: {
  onSubmit: (data: MenuItemBranchCreatePayload) => void
  onCancel: () => void
  loading?: boolean
}) {
  const { data: restaurantsData } = useRestaurants()
  const [restaurantId, setRestaurantId] = useState('')

  const { data: itemsData } = useMenuItems(
    restaurantId ? { restaurant: restaurantId, is_active: 'true' } : undefined
  )
  const { data: branchesData } = useAllBranches()

  const [form, setForm] = useState({
    menu_item: '',
    branch: '',
    is_available: 'true',
    available_from: '',
    available_to: '',
  })

  const setField = (key: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((p) => ({ ...p, [key]: e.target.value }))

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit({
      menu_item: form.menu_item,
      branch: form.branch,
      is_available: form.is_available === 'true',
      available_from: form.available_from || null,
      available_to: form.available_to || null,
    })
  }

  const inputClass =
    'w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-brand-500 placeholder-gray-600'
  const labelClass = 'block text-xs text-gray-500 mb-1.5'

  const filteredBranches = restaurantId
    ? branchesData?.results.filter((b) => b.restaurant === restaurantId)
    : branchesData?.results

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className={labelClass}>Restaurant *</label>
        <select
          className={inputClass}
          value={restaurantId}
          onChange={(e) => { setRestaurantId(e.target.value); setForm((p) => ({ ...p, menu_item: '', branch: '' })) }}
          required
        >
          <option value="">Select restaurant…</option>
          {restaurantsData?.results.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
      </div>
      <div>
        <label className={labelClass}>Menu Item *</label>
        <select className={inputClass} value={form.menu_item} onChange={setField('menu_item')} required>
          <option value="">Select item…</option>
          {itemsData?.results.map((i) => (
            <option key={i.id} value={i.id}>{i.name}</option>
          ))}
        </select>
      </div>
      <div>
        <label className={labelClass}>Branch *</label>
        <select className={inputClass} value={form.branch} onChange={setField('branch')} required>
          <option value="">Select branch…</option>
          {filteredBranches?.map((b) => (
            <option key={b.id} value={b.id}>{b.name}</option>
          ))}
        </select>
      </div>
      <div>
        <label className={labelClass}>Availability</label>
        <select className={inputClass} value={form.is_available} onChange={setField('is_available')}>
          <option value="true">Available</option>
          <option value="false">Unavailable</option>
        </select>
      </div>
      <div>
        <label className={labelClass}>Time Window (optional)</label>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-xs text-gray-600 mb-1">Available From</p>
            <input
              className={inputClass}
              type="time"
              value={form.available_from}
              onChange={setField('available_from')}
            />
          </div>
          <div>
            <p className="text-xs text-gray-600 mb-1">Available To</p>
            <input
              className={inputClass}
              type="time"
              value={form.available_to}
              onChange={setField('available_to')}
            />
          </div>
        </div>
        <p className="mt-1 text-xs text-gray-600">
          Leave blank for all-day availability. Uses restaurant timezone.
        </p>
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <Button variant="ghost" type="button" onClick={onCancel}>Cancel</Button>
        <Button variant="primary" type="submit" loading={loading}>Set Availability</Button>
      </div>
    </form>
  )
}

export function Availability() {
  const { hasPermission } = useAuth()
  const { toast } = useToast()

  const [branchFilter, setBranchFilter] = useState('')
  const [availableFilter, setAvailableFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [editTarget, setEditTarget] = useState<MenuItemBranch | null>(null)

  const params: Record<string, string | number> = {}
  if (branchFilter) params.branch = branchFilter
  if (availableFilter !== '') params.is_available = availableFilter

  const { data, isLoading, isError } = useAvailabilityList(params)
  const { data: branchesData } = useAllBranches()
  const createMut = useCreateAvailability()
  const updateMut = useUpdateAvailability(editTarget?.id ?? '')

  const canUpdate = hasPermission('menu.availability.update')

  async function handleCreate(payload: MenuItemBranchCreatePayload) {
    try {
      await createMut.mutateAsync(payload)
      setShowCreate(false)
      toast('Availability record created.', 'success')
    } catch {
      toast('Failed to set availability. A record may already exist for this item+branch.', 'error')
    }
  }

  async function handleToggle(record: MenuItemBranch) {
    setEditTarget(record)
    try {
      await updateMut.mutateAsync({ is_available: !record.is_available })
      toast(
        !record.is_available
          ? `"${record.menu_item_name}" is now available at ${record.branch_name}.`
          : `"${record.menu_item_name}" marked unavailable at ${record.branch_name}.`,
        !record.is_available ? 'success' : 'warning',
      )
    } catch {
      toast('Failed to update availability.', 'error')
    } finally {
      setEditTarget(null)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title="Branch Availability"
        description="Control which items are available at each branch, with optional time windows."
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Menu', to: '/menu' }, { label: 'Availability' }]}
        actions={
          canUpdate ? (
            <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
              + Set Availability
            </Button>
          ) : undefined
        }
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          aria-label="Filter by branch"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-500"
          value={branchFilter}
          onChange={(e) => setBranchFilter(e.target.value)}
        >
          <option value="">All Branches</option>
          {branchesData?.results.map((b) => (
            <option key={b.id} value={b.id}>{b.name}</option>
          ))}
        </select>
        <select
          aria-label="Filter by availability"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-500"
          value={availableFilter}
          onChange={(e) => setAvailableFilter(e.target.value)}
        >
          <option value="">All</option>
          <option value="true">Available</option>
          <option value="false">Unavailable</option>
        </select>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-14 bg-gray-900/60 border border-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400" role="alert">
          Failed to load availability records.
        </div>
      )}

      {!isLoading && data?.results.length === 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-6 py-12 text-center">
          <p className="text-gray-500 text-sm">No availability records found.</p>
        </div>
      )}

      {!isLoading && data && data.results.length > 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 overflow-hidden">
          <table className="w-full text-sm" role="table">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Item</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Branch</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden md:table-cell">Time Window</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Available</th>
                {canUpdate && <th className="px-4 py-3" aria-label="Toggle" />}
              </tr>
            </thead>
            <tbody>
              {data.results.map((rec) => {
                const isUpdating = editTarget?.id === rec.id
                return (
                  <tr key={rec.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-gray-200">{rec.menu_item_name}</p>
                      {rec.menu_item_sku && (
                        <span className="font-mono text-xs text-gray-600">{rec.menu_item_sku}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-sm">{rec.branch_name}</td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      {rec.available_from || rec.available_to ? (
                        <span className="text-xs text-gray-400 font-mono">
                          {rec.available_from ?? '—'} → {rec.available_to ?? '—'}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-700">All day</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border ${
                        rec.is_available
                          ? 'bg-green-500/10 text-green-400 border-green-500/20'
                          : 'bg-red-500/10 text-red-400 border-red-500/20'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${rec.is_available ? 'bg-green-400' : 'bg-red-400'}`} />
                        {rec.is_available ? 'Available' : 'Unavailable'}
                      </span>
                    </td>
                    {canUpdate && (
                      <td className="px-4 py-3 text-right">
                        <Button
                          variant={rec.is_available ? 'danger' : 'success'}
                          size="sm"
                          loading={isUpdating}
                          onClick={() => handleToggle(rec)}
                        >
                          {rec.is_available ? 'Set Unavailable' : 'Set Available'}
                        </Button>
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
          <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-700">
            {data.count} record{data.count !== 1 ? 's' : ''}
          </div>
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Set Branch Availability" size="lg">
        <AvailabilityForm
          onSubmit={handleCreate}
          onCancel={() => setShowCreate(false)}
          loading={createMut.isPending}
        />
      </Modal>
    </div>
  )
}
