// =============================================================================
// RestaurantFlow — Marketing Analytics Page
// Phase 18
// =============================================================================

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import marketingApi, { CampaignConversion } from '@/services/marketing'

export function MarketingAnalyticsPage() {
  const [conversions, setConversions] = useState<CampaignConversion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [total, setTotal] = useState(0)

  useEffect(() => {
    marketingApi.getConversions()
      .then(r => { setConversions(r.data.results); setTotal(r.data.count) })
      .catch(() => setError('Failed to load analytics.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center p-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>
  if (error) return <div className="p-12 text-center text-red-500">{error}</div>

  const totalValue = conversions.reduce((sum, c) => sum + parseFloat(c.conversion_value || '0'), 0)

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Marketing Analytics</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Conversion tracking — directly attributed campaigns only.
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {[
          { label: 'Total Conversions', value: total.toLocaleString() },
          { label: 'Revenue Attributed', value: `₹${totalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
          { label: 'Avg. Value', value: total > 0 ? `₹${(totalValue / total).toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '—' },
        ].map(m => (
          <div key={m.label} className="bg-white border border-gray-200 rounded-xl p-5">
            <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">{m.label}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{m.value}</p>
          </div>
        ))}
      </div>

      {/* Attribution disclaimer */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
        <strong>Attribution note:</strong> Figures shown are directly attributed conversions only.
        These do not represent causal revenue. For official financial reporting, use the{' '}
        <Link to="/reports" className="underline">Reporting module</Link>.
      </div>

      {/* Conversions table */}
      {conversions.length === 0 ? (
        <div className="text-center text-gray-400 text-sm py-12">No conversions recorded yet.</div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">Recent Conversions</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  {['Campaign', 'Customer', 'Type', 'Value', 'Date'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {conversions.map(c => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <Link to={`/marketing/campaigns/${c.campaign}`}
                        className="text-blue-600 hover:underline font-mono text-xs">
                        {c.campaign_code}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-600 font-mono text-xs">{c.customer_number}</td>
                    <td className="px-4 py-3">
                      <span className="bg-gray-100 text-gray-700 text-xs px-2 py-0.5 rounded">
                        {c.conversion_type.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-700 font-medium">
                      {parseFloat(c.conversion_value) > 0
                        ? `₹${parseFloat(c.conversion_value).toLocaleString()}`
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">
                      {new Date(c.converted_at).toLocaleDateString(undefined, {
                        day: 'numeric', month: 'short', year: 'numeric'
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
