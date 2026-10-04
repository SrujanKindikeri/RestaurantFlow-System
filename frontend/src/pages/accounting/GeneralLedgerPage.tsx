// =============================================================================
// RestaurantFlow — General Ledger Page
// Phase 13
// =============================================================================

import { useEffect, useState } from 'react'
import { getGeneralLedger, listAccounts, type GeneralLedgerRow, type Account } from '@/services/accounting'
import { useAuth } from '@/contexts/AuthContext'

const fmt = (v: string | number) =>
  Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export function GeneralLedgerPage() {
  const { user } = useAuth()
  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  const [rows, setRows] = useState<GeneralLedgerRow[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [accountFilter, setAccountFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [sourceType, setSourceType] = useState('')

  // Load accounts for the dropdown
  useEffect(() => {
    if (!restaurantId) return
    listAccounts({ restaurant: restaurantId, is_postable: 'true' })
      .then(setAccounts)
      .catch(() => {})
  }, [restaurantId])

  const loadLedger = () => {
    if (!restaurantId) return
    setLoading(true)
    setError(null)
    const params: Record<string, string> = {}
    if (accountFilter) params.account = accountFilter
    if (dateFrom) params.date_from = dateFrom
    if (dateTo) params.date_to = dateTo
    if (sourceType) params.source_type = sourceType

    getGeneralLedger(restaurantId, params)
      .then((res) => setRows(res.results ?? []))
      .catch((e) => setError(e?.response?.data?.detail ?? 'Failed to load general ledger'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadLedger() }, [restaurantId, accountFilter, dateFrom, dateTo, sourceType])

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">General Ledger</h1>
        <p className="text-sm text-gray-500 mt-1">All posted accounting transactions with running balance</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={accountFilter}
          onChange={(e) => setAccountFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
        >
          <option value="">All Accounts</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>[{a.code}] {a.name}</option>
          ))}
        </select>
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500" />
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500" />
        <select
          value={sourceType}
          onChange={(e) => setSourceType(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
        >
          <option value="">All Sources</option>
          <option value="BILL">Sales</option>
          <option value="PAYMENT">Payment</option>
          <option value="PAYMENT_REFUND">Refund</option>
          <option value="EXPENSE">Expense</option>
          <option value="SUPPLIER_INVOICE">Purchase</option>
          <option value="INVENTORY_CONSUMPTION">COGS</option>
          <option value="MANUAL">Manual</option>
        </select>
      </div>

      {loading && (
        <div className="space-y-2">{Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-10 bg-gray-800 rounded animate-pulse" />
        ))}</div>
      )}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>
      )}

      <div className="text-xs text-gray-500">{rows.length} transaction lines</div>

      <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-auto">
        <table className="w-full text-sm min-w-max">
          <thead>
            <tr className="border-b border-gray-700">
              <th className="px-4 py-3 text-xs text-gray-500 font-medium text-left">Date</th>
              <th className="px-4 py-3 text-xs text-gray-500 font-medium text-left">Journal #</th>
              <th className="px-4 py-3 text-xs text-gray-500 font-medium text-left">Account</th>
              <th className="px-4 py-3 text-xs text-gray-500 font-medium text-left">Description</th>
              <th className="px-4 py-3 text-xs text-gray-500 font-medium text-left hidden md:table-cell">Source</th>
              <th className="px-4 py-3 text-xs text-gray-500 font-medium text-right">Debit</th>
              <th className="px-4 py-3 text-xs text-gray-500 font-medium text-right">Credit</th>
              <th className="px-4 py-3 text-xs text-gray-500 font-medium text-right">Balance</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                  No ledger entries found. Apply filters or check if there are posted journal entries.
                </td>
              </tr>
            )}
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-gray-700/30 hover:bg-gray-750">
                <td className="px-4 py-2.5 text-gray-400 text-xs whitespace-nowrap">{row.date}</td>
                <td className="px-4 py-2.5 font-mono text-blue-400 text-xs whitespace-nowrap">{row.journal_number}</td>
                <td className="px-4 py-2.5">
                  <span className="font-mono text-xs text-gray-400">{row.account_code}</span>
                  <span className="text-xs text-gray-300 ml-2">{row.account_name}</span>
                </td>
                <td className="px-4 py-2.5 text-gray-300 text-xs max-w-xs truncate">{row.description}</td>
                <td className="px-4 py-2.5 text-gray-500 text-xs hidden md:table-cell">{row.source_type}</td>
                <td className="px-4 py-2.5 text-right font-mono text-xs text-gray-300">
                  {Number(row.debit) > 0 ? `₹${fmt(row.debit)}` : ''}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-xs text-gray-300">
                  {Number(row.credit) > 0 ? `₹${fmt(row.credit)}` : ''}
                </td>
                <td className={`px-4 py-2.5 text-right font-mono text-xs font-medium ${
                  Number(row.balance) >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  ₹{fmt(row.balance)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
