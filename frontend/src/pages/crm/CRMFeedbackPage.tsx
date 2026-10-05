// =============================================================================
// RestaurantFlow — CRM Feedback Management Page
// Phase 17
// =============================================================================

import { useState, useEffect } from 'react'
import crmApi, { CustomerFeedback } from '@/services/crm'

function StarDisplay({ rating }: { rating: number }) {
  return (
    <span className="text-amber-400">
      {'★'.repeat(rating)}
      <span className="text-gray-200">{'★'.repeat(5 - rating)}</span>
    </span>
  )
}

export function CRMFeedbackPage() {
  const [feedback, setFeedback] = useState<CustomerFeedback[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedFeedback, setSelectedFeedback] = useState<CustomerFeedback | null>(null)
  const [moderateStatus, setModerateStatus] = useState('APPROVED')
  const [moderateNote, setModerateNote] = useState('')
  const [moderating, setModerating] = useState(false)
  const [filters, setFilters] = useState({ rating: '', status: '', date_from: '', date_to: '' })

  const fetchFeedback = async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (filters.rating) params.rating = filters.rating
      if (filters.status) params.status = filters.status
      if (filters.date_from) params.date_from = filters.date_from
      if (filters.date_to) params.date_to = filters.date_to
      const res = await crmApi.listFeedback(params)
      setFeedback(res.data.results)
    } catch {
      setError('Failed to load feedback.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchFeedback() }, [])

  const handleModerate = async () => {
    if (!selectedFeedback) return
    setModerating(true)
    try {
      await crmApi.moderateFeedback(selectedFeedback.id, {
        status: moderateStatus,
        moderation_note: moderateNote,
      })
      setSelectedFeedback(null)
      setModerateNote('')
      fetchFeedback()
    } catch {
      setError('Moderation failed.')
    } finally {
      setModerating(false)
    }
  }

  const avgRating = feedback.length
    ? (feedback.reduce((s, f) => s + f.rating, 0) / feedback.length).toFixed(1)
    : '—'

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Customer Feedback</h1>
          <p className="text-sm text-gray-500 mt-1">
            {feedback.length} reviews · Average rating: {avgRating}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={filters.rating}
          onChange={e => setFilters(f => ({ ...f, rating: e.target.value }))}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none"
        >
          <option value="">All Ratings</option>
          {[1,2,3,4,5].map(r => <option key={r} value={r}>{r} Star{r !== 1 ? 's' : ''}</option>)}
        </select>
        <select
          value={filters.status}
          onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none"
        >
          <option value="">All Statuses</option>
          <option value="SUBMITTED">Submitted</option>
          <option value="REVIEWED">Reviewed</option>
          <option value="RESOLVED">Resolved</option>
          <option value="HIDDEN">Hidden</option>
        </select>
        <input
          type="date"
          value={filters.date_from}
          onChange={e => setFilters(f => ({ ...f, date_from: e.target.value }))}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none"
        />
        <input
          type="date"
          value={filters.date_to}
          onChange={e => setFilters(f => ({ ...f, date_to: e.target.value }))}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none"
        />
        <button
          onClick={fetchFeedback}
          className="px-4 py-2 bg-gray-800 text-white text-sm rounded-lg hover:bg-gray-700"
        >
          Apply
        </button>
      </div>

      {error && <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">{error}</div>}

      {/* Feedback list */}
      {loading ? (
        <div className="text-center text-gray-400 text-sm py-12">Loading…</div>
      ) : (
        <div className="space-y-3">
          {feedback.length === 0 ? (
            <div className="text-center text-gray-400 text-sm py-12">No feedback found.</div>
          ) : feedback.map(fb => (
            <div key={fb.id} className="bg-white border border-gray-200 rounded-xl p-5 hover:border-gray-300 transition-colors">
              <div className="flex items-start justify-between">
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-3">
                    <StarDisplay rating={fb.rating} />
                    <span className="text-sm text-gray-500">{fb.branch_name}</span>
                    <span className={`px-2 py-0.5 text-xs rounded-full ${
                      fb.status === 'RESOLVED' ? 'bg-green-100 text-green-700' :
                      fb.status === 'HIDDEN' ? 'bg-gray-100 text-gray-500' :
                      fb.status === 'REVIEWED' ? 'bg-blue-100 text-blue-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>{fb.status}</span>
                  </div>
                  {(fb.food_rating || fb.service_rating || fb.ambience_rating) && (
                    <div className="flex gap-4 text-xs text-gray-400">
                      {fb.food_rating && <span>Food: {fb.food_rating}/5</span>}
                      {fb.service_rating && <span>Service: {fb.service_rating}/5</span>}
                      {fb.ambience_rating && <span>Ambience: {fb.ambience_rating}/5</span>}
                    </div>
                  )}
                  {fb.comment && (
                    <p className="text-sm text-gray-700 mt-1">{fb.comment}</p>
                  )}
                  <p className="text-xs text-gray-400">{new Date(fb.created_at).toLocaleString()}</p>
                </div>
                <button
                  onClick={() => setSelectedFeedback(fb)}
                  className="ml-4 px-3 py-1.5 text-xs border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50"
                >
                  Moderate
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Moderation modal */}
      {selectedFeedback && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Moderate Feedback</h2>
            <div className="p-3 bg-gray-50 rounded-lg">
              <StarDisplay rating={selectedFeedback.rating} />
              {selectedFeedback.comment && (
                <p className="text-sm text-gray-700 mt-1">{selectedFeedback.comment}</p>
              )}
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 uppercase tracking-wide">Action</label>
              <select
                value={moderateStatus}
                onChange={e => setModerateStatus(e.target.value)}
                className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none"
              >
                <option value="APPROVED">Approve</option>
                <option value="HIDDEN">Hide</option>
                <option value="REJECTED">Reject</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 uppercase tracking-wide">Note</label>
              <textarea
                value={moderateNote}
                onChange={e => setModerateNote(e.target.value)}
                rows={3}
                className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none resize-none"
                placeholder="Optional moderation note…"
              />
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => { setSelectedFeedback(null); setModerateNote('') }}
                className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleModerate}
                disabled={moderating}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {moderating ? 'Saving…' : 'Submit'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
