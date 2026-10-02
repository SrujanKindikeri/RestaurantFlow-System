// =============================================================================
// RestaurantFlow — Pricing Page
// Phase 5
// =============================================================================

import { useState } from 'react'
import {
  usePrices,
  useCreatePrice,
  useDeactivatePrice,
  useMenuItems,
} from '@/hooks/useMenu'
import { useAllBranches } from '@/hooks/useBranches'
import { useAllRestaurants as useRestaurants } from '@/hooks/useRestaurants'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/Button'
import { Modal, ConfirmDialog } from '@/components/ui/Modal'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/contexts/AuthContext'
import type { MenuItemPrice, MenuItemPriceCreatePayload } from '@/types'

function PriceForm({
  onSubmit,
  onCancel,
  loading,
}: {
  onSubmit: (data: MenuItemPriceCreatePayload) => void
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
    price: '',
    effective_from: '',
    effective_to: '',
  })

  const setField = (key: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((p) => ({ ...p, [key]: e.target.value }))

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit({
      ...form,
      effective_from: form.effective_from || null,
      effective_to: form.effective_to || null,
      is_active: true,
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
            <option key={i.id} value={i.id}>{i.name}{i.sku ? ` (${i.sku})` : ''}</option>
          ))}
        </select>
      </div>
      <div>
        <label className={labelClass}>Branch *</label>
        <select className={inputClass} value={form.branch} onChange={setField('branch')} required>
          <option value="">Select branch…</option>
          {filteredBranches?.map((b) => (
            <option key={b.id} value={b.id}>{b.name}{b.restaurant_name ? ` — ${b.restaurant_name}` : ''}</option>
          ))}
        </select>
      </div>
      <div>
        <label className={labelClass}>Price (₹) *</label>
        <input
          className={inputClass}
          type="number"
          min="0"
          step="0.01"
          placeholder="0.00"
          required
          value={form.price}
          onChange={setField('price')}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass}>Effective From</label>
          <input className={inputClass} type="datetime-local" value={form.effective_from} onChange={setField('effective_from')} />
        </div>
        <div>
          <label className={labelClass}>Effective To</label>
          <input className={inputClass} type="datetime-local" value={form.effective_to} onChange={setField('effective_to')} />
        </div>
      </div>
      <p className="text-xs text-gray-600">
        A new active price record will be created. Deactivate the previous price first to avoid overlap errors.
      </p>
      <div className="flex justify-end gap-3 pt-2">
        <Button variant="ghost" type="button" onClick={onCancel}>Cancel</Button>
        <Button variant="primary" type="submit" loading={loading}>Create Price</Button>
      </div>
    </form>
  )
}

export function Pricing() {
  const { hasPermission } = useAuth()
  const { toast } = useToast()

  const [branchFilter, setBranchFilter] = useState('')
  const [activeFilter, setActiveFilter] = useState('true')
  const [showCreate, setShowCreate] = useState(false)
  const [confirmDeactivate, setConfirmDeactivate] = useState<MenuItemPrice | null>(null)

  const params: Record<string, string | number> = {}
  if (branchFilter) params.branch = branchFilter
  if (activeFilter !== '') params.is_active = activeFilter

  const { data, isLoading, isError } = usePrices(params)
  const { data: branchesData } = useAllBranches()
  const createMut = useCreatePrice()
  const deactivateMut = useDeactivatePrice()

  const canCreate = hasPermission('menu.price.create')
  const canUpdate = hasPermission('menu.price.update')

  async function handleCreate(payload: MenuItemPriceCreatePayload) {
    try {
      await createMut.mutateAsync(payload)
      setShowCreate(false)
      toast('Price created.', 'success')
    } catch {
      toast('Failed to create price. Check for overlapping active prices.', 'error')
    }
  }

  async function handleDeactivate() {
    if (!confirmDeactivate) return
    try {
      await deactivateMut.mutateAsync(confirmDeactivate.id)
      toast('Price marked as historical.', 'warning')
    } catch {
      toast('Failed to deactivate price.', 'error')
    } finally {
      setConfirmDeactivate(null)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title="Branch Pricing"
        description="Manage branch-specific prices. Price history is preserved — never overwritten."
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Menu', to: '/menu' }, { label: 'Pricing' }]}
        actions={
          canCreate ? (
            <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
              + Add Price
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
          aria-label="Filter by status"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-500"
          value={activeFilter}
          onChange={(e) => setActiveFilter(e.target.value)}
        >
          <option value="true">Active Prices</option>
          <option value="false">Historical</option>
          <option value="">All</option>
        </select>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-14 bg-gray-900/60 border border-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400" role="alert">
          Failed to load prices.
        </div>
      )}

      {!isLoading && data?.results.length === 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-6 py-12 text-center">
          <p className="text-gray-500 text-sm">No price records found.</p>
        </div>
      )}

      {!isLoading && data && data.results.length > 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 overflow-hidden">
          <table className="w-full text-sm" role="table">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Item</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden sm:table-cell">Branch</th>
                <th className="text-right px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Price</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden md:table-cell">Effective From</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden lg:table-cell">Effective To</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Status</th>
                <th className="px-4 py-3" aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {data.results.map((price) => (
                <tr key={price.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-3">
                    <p className="text-gray-200">{price.menu_item_name}</p>
                    {price.menu_item_sku && (
                      <span className="font-mono text-xs text-gray-600">{price.menu_item_sku}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs hidden sm:table-cell">{price.branch_name}</td>
                  <td className="px-4 py-3 text-right font-mono text-brand-400 font-semibold">
                    ₹{Number(price.price).toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs hidden md:table-cell">
                    {price.effective_from
                      ? new Date(price.effective_from).toLocaleDateString()
                      : <span className="text-gray-700">—</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs hidden lg:table-cell">
                    {price.effective_to
                      ? new Date(price.effective_to).toLocaleDateString()
                      : <span className="text-gray-700">Current</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${
                      price.is_active
                        ? 'bg-green-500/10 text-green-400 border-green-500/20'
                        : 'bg-gray-700/30 text-gray-500 border-gray-700/30'
                    }`}>
                      {price.is_active ? 'Active' : 'Historical'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {canUpdate && price.is_active && (
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => setConfirmDeactivate(price)}
                      >
                        Deactivate
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-700">
            {data.count} price record{data.count !== 1 ? 's' : ''}
          </div>
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Add Branch Price" size="lg">
        <PriceForm
          onSubmit={handleCreate}
          onCancel={() => setShowCreate(false)}
          loading={createMut.isPending}
        />
      </Modal>

      <ConfirmDialog
        open={!!confirmDeactivate}
        onClose={() => setConfirmDeactivate(null)}
        onConfirm={handleDeactivate}
        title="Deactivate Price?"
        message={`Mark ₹${confirmDeactivate ? Number(confirmDeactivate.price).toFixed(2) : ''} for "${confirmDeactivate?.menu_item_name}" as historical? This preserves the record for reporting.`}
        confirmLabel="Deactivate"
        confirmVariant="warning"
        loading={deactivateMut.isPending}
      />
    </div>
  )
}
