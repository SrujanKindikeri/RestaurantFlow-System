// =============================================================================
// RestaurantFlow — Suppliers Page
// Phase 10
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { listSuppliers, createSupplier, updateSupplier } from '@/services/inventory'
import type { Supplier, CreateSupplierPayload } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

export function SuppliersPage() {
  const { user, hasPermission } = useAuth()
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)

  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  const emptyForm = (): Partial<CreateSupplierPayload> => ({
    restaurant_id: restaurantId,
    name: '', code: '', contact_person: '', phone: '', email: '',
    address: '', tax_identifier: '', notes: '',
  })
  const [form, setForm] = useState<Partial<CreateSupplierPayload>>(emptyForm())

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (restaurantId) params.restaurant = restaurantId
    listSuppliers(params)
      .then(r => setSuppliers(r.data))
      .catch(e => setError(e?.response?.data?.message ?? 'Failed to load suppliers'))
      .finally(() => setLoading(false))
  }, [restaurantId])

  useEffect(() => { load() }, [load])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setFormError(null)
    try {
      if (editingId) {
        await updateSupplier(editingId, form)
      } else {
        await createSupplier({ ...form, restaurant_id: restaurantId } as CreateSupplierPayload)
      }
      setShowForm(false)
      setEditingId(null)
      setForm(emptyForm())
      load()
    } catch (e: any) {
      const detail = e?.response?.data
      setFormError(detail?.message ?? 'Failed to save supplier')
    } finally {
      setSaving(false)
    }
  }

  const openEdit = (s: Supplier) => {
    setForm({ name: s.name, code: s.code, contact_person: s.contact_person, phone: s.phone, email: s.email, address: s.address, tax_identifier: s.tax_identifier, notes: s.notes })
    setEditingId(s.id)
    setShowForm(true)
  }

  const handleToggle = async (s: Supplier) => {
    try { await updateSupplier(s.id, { is_active: !s.is_active }); load() } catch { /* ignore */ }
  }

  const f = (key: keyof CreateSupplierPayload) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm(v => ({ ...v, [key]: e.target.value }))

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Suppliers</h1>
          <p className="text-sm text-gray-500 mt-0.5">{suppliers.length} suppliers</p>
        </div>
        {hasPermission('supplier.create') && (
          <button onClick={() => { setShowForm(v => !v); setEditingId(null); setForm(emptyForm()) }}
            className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm hover:bg-brand-600 transition-colors">
            + Add Supplier
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-white">{editingId ? 'Edit Supplier' : 'New Supplier'}</h3>
          {formError && <p className="text-xs text-red-400">{formError}</p>}
          <div className="grid grid-cols-2 gap-3">
            {([['name','Name',true],['code','Code',true],['contact_person','Contact Person',false],['phone','Phone',false],['email','Email',false],['tax_identifier','Tax ID / GSTIN',false]] as [keyof CreateSupplierPayload, string, boolean][]).map(([key, label, req]) => (
              <div key={key}>
                <label className="block text-xs text-gray-400 mb-1">{label}{req && ' *'}</label>
                <input required={req} value={(form[key] as string) ?? ''} onChange={f(key)}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" />
              </div>
            ))}
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Address</label>
            <textarea value={form.address ?? ''} onChange={f('address')} rows={2}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500 resize-none" />
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={saving} className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm disabled:opacity-50 hover:bg-brand-600">
              {saving ? 'Saving…' : editingId ? 'Update' : 'Create'}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg text-sm hover:bg-gray-600">
              Cancel
            </button>
          </div>
        </form>
      )}

      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>}

      {loading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-14 bg-gray-800 rounded-lg animate-pulse" />)}</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                {['Name', 'Code', 'Contact', 'Phone', 'Email', 'Status', ''].map(h => (
                  <th key={h} className="text-left text-xs text-gray-500 font-medium px-3 py-2">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {suppliers.map(s => (
                <tr key={s.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="px-3 py-3 text-gray-200 font-medium">{s.name}</td>
                  <td className="px-3 py-3 text-gray-400 font-mono text-xs">{s.code}</td>
                  <td className="px-3 py-3 text-gray-400">{s.contact_person || '—'}</td>
                  <td className="px-3 py-3 text-gray-400">{s.phone || '—'}</td>
                  <td className="px-3 py-3 text-gray-400">{s.email || '—'}</td>
                  <td className="px-3 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${s.is_active ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-gray-700 text-gray-500 border-gray-600'}`}>
                      {s.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-3 py-3 flex gap-3">
                    {hasPermission('supplier.update') && (
                      <>
                        <button onClick={() => openEdit(s)} className="text-xs text-brand-400 hover:text-brand-300">Edit</button>
                        <button onClick={() => handleToggle(s)} className="text-xs text-gray-500 hover:text-gray-300">
                          {s.is_active ? 'Disable' : 'Enable'}
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
              {suppliers.length === 0 && (
                <tr><td colSpan={7} className="px-3 py-8 text-center text-gray-600 text-sm">No suppliers found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
