// =============================================================================
// RestaurantFlow — Campaign Detail Page
// Phase 18
// =============================================================================

import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import marketingApi, { Campaign, CampaignAnalytics } from '@/services/marketing'
import { useAuth } from '@/contexts/AuthContext'

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    RUNNING:          'bg-emerald-100 text-emerald-700',
    SCHEDULED:        'bg-blue-100 text-blue-700',
    PAUSED:           'bg-amber-100 text-amber-700',
    DRAFT:            'bg-gray-100 text-gray-600',
    PENDING_APPROVAL: 'bg-purple-100 text-purple-700',
    APPROVED:         'bg-teal-100 text-teal-700',
    COMPLETED:        'bg-gray-200 text-gray-700',
    CANCELLED:        'bg-red-100 text-red-600',
    FAILED:           'bg-red-200 text-red-700',
  }
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${map[status] ?? 'bg-gray-100 text-gray-500'}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <dt className="text-xs text-gray-400 uppercase tracking-wide font-medium">{label}</dt>
      <dd className="mt-0.5 text-sm text-gray-900">{value || '—'}</dd>
    </div>
  )
}

function formatDate(dt: string | null | undefined) {
  if (!dt) return null
  return new Date(dt).toLocaleDateString(undefined, {
    day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { hasPermission } = useAuth()
  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [analytics, setAnalytics] = useState<CampaignAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [rejectNote, setRejectNote] = useState('')
  const [cancelReason, setCancelReason] = useState('')
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [showCancelModal, setShowCancelModal] = useState(false)

  useEffect(() => {
    if (!id) return
    Promise.all([
      marketingApi.getCampaign(id),
      marketingApi.getCampaignAnalytics(id).catch(() => ({ data: null })),
    ])
      .then(([campR, anlR]) => {
        setCampaign(campR.data)
        setAnalytics(anlR.data as CampaignAnalytics | null)
      })
      .catch(() => setError('Failed to load campaign.'))
      .finally(() => setLoading(false))
  }, [id])

  async function doAction(action: () => Promise<unknown>, label: string) {
    setActionLoading(true)
    setActionError('')
    try {
      await action()
      // Refresh
      const r = await marketingApi.getCampaign(id!)
      setCampaign(r.data)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? `Failed to ${label}.`
      setActionError(msg)
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) return <div className="flex justify-center p-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>
  if (error || !campaign) return <div className="p-12 text-center text-red-500">{error || 'Campaign not found.'}</div>

  const s = campaign.status
  const canSubmit = s === 'DRAFT' && hasPermission('marketing.campaign.submit')
  const canApprove = s === 'PENDING_APPROVAL' && hasPermission('marketing.campaign.approve')
  const canReject = s === 'PENDING_APPROVAL' && hasPermission('marketing.campaign.reject')
  const canSchedule = s === 'APPROVED' && hasPermission('marketing.campaign.schedule')
  const canPause = s === 'RUNNING' && hasPermission('marketing.campaign.pause')
  const canResume = s === 'PAUSED' && hasPermission('marketing.campaign.resume')
  const canCancel = !['COMPLETED', 'CANCELLED', 'FAILED'].includes(s) && hasPermission('marketing.campaign.cancel')

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-400">
        <Link to="/marketing/campaigns" className="hover:text-gray-600">Campaigns</Link>
        <span>/</span>
        <span className="text-gray-700 font-medium">{campaign.name}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-gray-900">{campaign.name}</h1>
            <StatusBadge status={campaign.status} />
          </div>
          <p className="text-sm text-gray-400 font-mono mt-0.5">{campaign.code}</p>
          {campaign.description && (
            <p className="text-sm text-gray-500 mt-1 max-w-xl">{campaign.description}</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-2">
          {canSubmit && (
            <button
              onClick={() => doAction(() => marketingApi.submitCampaign(campaign.id), 'submit')}
              disabled={actionLoading}
              className="px-3 py-1.5 bg-purple-600 text-white text-xs rounded-lg hover:bg-purple-700 disabled:opacity-50"
            >
              Submit for Approval
            </button>
          )}
          {canApprove && (
            <button
              onClick={() => doAction(() => marketingApi.approveCampaign(campaign.id, ''), 'approve')}
              disabled={actionLoading}
              className="px-3 py-1.5 bg-emerald-600 text-white text-xs rounded-lg hover:bg-emerald-700 disabled:opacity-50"
            >
              Approve
            </button>
          )}
          {canReject && (
            <button
              onClick={() => setShowRejectModal(true)}
              disabled={actionLoading}
              className="px-3 py-1.5 bg-red-600 text-white text-xs rounded-lg hover:bg-red-700 disabled:opacity-50"
            >
              Reject
            </button>
          )}
          {canSchedule && (
            <button
              onClick={() => doAction(() => marketingApi.scheduleCampaign(campaign.id), 'schedule')}
              disabled={actionLoading}
              className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Schedule
            </button>
          )}
          {canPause && (
            <button
              onClick={() => doAction(() => marketingApi.pauseCampaign(campaign.id), 'pause')}
              disabled={actionLoading}
              className="px-3 py-1.5 bg-amber-600 text-white text-xs rounded-lg hover:bg-amber-700 disabled:opacity-50"
            >
              Pause
            </button>
          )}
          {canResume && (
            <button
              onClick={() => doAction(() => marketingApi.resumeCampaign(campaign.id), 'resume')}
              disabled={actionLoading}
              className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Resume
            </button>
          )}
          {canCancel && (
            <button
              onClick={() => setShowCancelModal(true)}
              disabled={actionLoading}
              className="px-3 py-1.5 bg-white border border-red-300 text-red-600 text-xs rounded-lg hover:bg-red-50 disabled:opacity-50"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {actionError && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-2 rounded-lg">
          {actionError}
        </div>
      )}

      {/* Details Grid */}
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Campaign Details</h2>
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-4">
          <Field label="Type" value={campaign.campaign_type.replace(/_/g, ' ')} />
          <Field label="Status" value={campaign.status.replace(/_/g, ' ')} />
          <Field label="Restaurant" value={campaign.restaurant_name} />
          <Field label="Branch" value={campaign.branch_name} />
          <Field label="Start" value={formatDate(campaign.start_at) ?? undefined} />
          <Field label="End" value={formatDate(campaign.end_at) ?? undefined} />
          <Field label="Created by" value={campaign.created_by_email} />
          <Field label="Approved by" value={campaign.approved_by_email} />
          <Field label="Approved at" value={formatDate(campaign.approved_at) ?? undefined} />
        </dl>
      </div>

      {/* Analytics */}
      {analytics && (
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Campaign Analytics</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Audience', value: analytics.audience_total.toLocaleString() },
              { label: 'Contacted', value: analytics.contacted.toLocaleString() },
              { label: 'Converted', value: analytics.converted.toLocaleString() },
              { label: 'Delivery Rate', value: `${analytics.delivery_rate_pct}%` },
              { label: 'Conversion Rate', value: `${analytics.conversion_rate_pct}%` },
              { label: 'Deliveries Sent', value: analytics.deliveries_sent.toLocaleString() },
              { label: 'Delivery Failures', value: analytics.deliveries_failed.toLocaleString() },
              { label: 'Discount Given', value: `₹${parseFloat(analytics.discount_given).toLocaleString()}` },
            ].map(m => (
              <div key={m.label} className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-400">{m.label}</p>
                <p className="text-lg font-semibold text-gray-900 mt-0.5">{m.value}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-3">
            Revenue figures are directly attributed only. Not indicative of causal impact.
          </p>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-4">
            <h2 className="font-semibold text-gray-900">Reject Campaign</h2>
            <textarea
              value={rejectNote}
              onChange={e => setRejectNote(e.target.value)}
              placeholder="Rejection reason (required)…"
              rows={3}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
            />
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowRejectModal(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancel</button>
              <button
                disabled={!rejectNote.trim() || actionLoading}
                onClick={() => {
                  setShowRejectModal(false)
                  doAction(() => marketingApi.rejectCampaign(campaign.id, rejectNote), 'reject')
                }}
                className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-4">
            <h2 className="font-semibold text-gray-900">Cancel Campaign</h2>
            <textarea
              value={cancelReason}
              onChange={e => setCancelReason(e.target.value)}
              placeholder="Cancellation reason (optional)…"
              rows={3}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
            />
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowCancelModal(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Back</button>
              <button
                disabled={actionLoading}
                onClick={() => {
                  setShowCancelModal(false)
                  doAction(() => marketingApi.cancelCampaign(campaign.id, cancelReason), 'cancel')
                }}
                className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                Cancel Campaign
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
