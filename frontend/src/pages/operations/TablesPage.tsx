// =============================================================================
// RestaurantFlow — Table Management Dashboard
// Phase 19: Advanced POS & Restaurant Operations
// =============================================================================

import { useEffect, useState } from 'react'
import { getOperationalTables, setTableStatus, closeTable, requestTableTransfer } from '@/services/operations'

const STATUS_COLORS: Record<string, string> = {
  AVAILABLE: 'border-green-500/40 bg-green-500/5 text-green-400',
  OCCUPIED: 'border-blue-500/40 bg-blue-500/5 text-blue-400',
  RESERVED: 'border-purple-500/40 bg-purple-500/5 text-purple-400',
  BILL_PENDING: 'border-yellow-500/40 bg-yellow-500/5 text-yellow-400',
  CLEANING: 'border-orange-500/40 bg-orange-500/5 text-orange-400',
  OUT_OF_SERVICE: 'border-red-500/40 bg-red-500/5 text-red-400',
}

const STATUS_DOT: Record<string, string> = {
  AVAILABLE: 'bg-green-400',
  OCCUPIED: 'bg-blue-400',
  RESERVED: 'bg-purple-400',
  BILL_PENDING: 'bg-yellow-400',
  CLEANING: 'bg-orange-400',
  OUT_OF_SERVICE: 'bg-red-400',
}

interface TableData {
  id: string
  table_number: string
  name: string
  section: string
  capacity: number
  operational_status: string
  has_open_session: boolean
  guest_count: number
}

export function TablesPage() {
  const [tables, setTables] = useState<TableData[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTable, setSelectedTable] = useState<TableData | null>(null)
  const [filterSection, setFilterSection] = useState<string>('all')
  const [error, setError] = useState('')
  const [actionLoading, setActionLoading] = useState(false)

  const sections = ['all', ...Array.from(new Set(tables.map(t => t.section || 'Main').filter(Boolean)))]

  const load = () => {
    setLoading(true)
    getOperationalTables()
      .then(r => setTables(r))
      .catch(() => setError('Failed to load tables'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  // Auto-refresh every 30s
  useEffect(() => {
    const id = setInterval(load, 30_000)
    return () => clearInterval(id)
  }, [])

  const filtered = filterSection === 'all'
    ? tables
    : tables.filter(t => (t.section || 'Main') === filterSection)

  const setStatus = async (status: string) => {
    if (!selectedTable) return
    setActionLoading(true)
    try {
      await setTableStatus(selectedTable.id, status)
      setSelectedTable(null)
      load()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to update status')
    } finally {
      setActionLoading(false)
    }
  }

  const handleClose = async () => {
    if (!selectedTable) return
    setActionLoading(true)
    try {
      await closeTable(selectedTable.id)
      setSelectedTable(null)
      load()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to close table')
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-white">Table Map</h1>
          <p className="text-sm text-gray-500 mt-0.5">{tables.length} tables · click to manage</p>
        </div>
        <button
          onClick={load}
          className="text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg px-4 py-3 text-sm flex justify-between">
          {error}
          <button onClick={() => setError('')} className="text-xs underline">Dismiss</button>
        </div>
      )}

      {/* Status legend */}
      <div className="flex flex-wrap gap-3">
        {Object.entries(STATUS_COLORS).map(([s, cls]) => (
          <span key={s} className={`inline-flex items-center gap-1.5 text-xs border rounded-full px-2.5 py-1 ${cls}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[s]}`} />
            {s.replace('_', ' ')}
          </span>
        ))}
      </div>

      {/* Section filter */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {sections.map(sec => (
          <button
            key={sec}
            onClick={() => setFilterSection(sec)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap capitalize transition-colors ${
              filterSection === sec ? 'bg-brand-500 text-white' : 'bg-gray-900 text-gray-400 hover:text-white border border-gray-800'
            }`}
          >
            {sec}
          </button>
        ))}
      </div>

      {/* Table grid */}
      {loading ? (
        <div className="text-gray-500 text-sm py-10 text-center">Loading tables…</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {filtered.map(table => (
            <button
              key={table.id}
              onClick={() => setSelectedTable(table)}
              className={`relative border-2 rounded-xl p-4 text-left transition-all hover:scale-105 ${STATUS_COLORS[table.operational_status] ?? 'border-gray-700 bg-gray-900'}`}
            >
              {/* Table number */}
              <p className="text-lg font-bold">{table.table_number}</p>

              {/* Name */}
              {table.name && <p className="text-xs opacity-70 truncate">{table.name}</p>}

              {/* Capacity */}
              <p className="text-xs opacity-60 mt-1">
                {table.capacity} seats
              </p>

              {/* Guest count if occupied */}
              {table.has_open_session && (
                <p className="text-xs font-medium mt-0.5">
                  {table.guest_count} guests
                </p>
              )}

              {/* Status dot */}
              <span className={`absolute top-2 right-2 w-2 h-2 rounded-full ${STATUS_DOT[table.operational_status]}`} />
            </button>
          ))}
        </div>
      )}

      {/* Table detail panel */}
      {selectedTable && (
        <div className="fixed inset-0 z-50 bg-gray-950/80 flex items-center justify-center p-4" onClick={() => setSelectedTable(null)}>
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-sm p-5 shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-white">Table {selectedTable.table_number}</h2>
                <p className="text-sm text-gray-500">{selectedTable.section || 'Main'} · {selectedTable.capacity} seats</p>
              </div>
              <span className={`text-xs border rounded-full px-2 py-1 ${STATUS_COLORS[selectedTable.operational_status]}`}>
                {selectedTable.operational_status.replace('_', ' ')}
              </span>
            </div>

            {selectedTable.has_open_session && (
              <div className="mb-4 bg-gray-800 rounded-lg p-3 text-sm">
                <p className="text-gray-400">Guests: <span className="text-white font-medium">{selectedTable.guest_count}</span></p>
              </div>
            )}

            <div className="space-y-2">
              <p className="text-xs text-gray-600 uppercase tracking-widest">Actions</p>
              {selectedTable.operational_status === 'AVAILABLE' && (
                <ActionButton onClick={() => setStatus('OCCUPIED')} loading={actionLoading} color="blue">Mark Occupied</ActionButton>
              )}
              {selectedTable.operational_status === 'OCCUPIED' && (
                <>
                  <ActionButton onClick={() => setStatus('BILL_PENDING')} loading={actionLoading} color="yellow">Bill Pending</ActionButton>
                  <ActionButton onClick={handleClose} loading={actionLoading} color="green">Close Table</ActionButton>
                </>
              )}
              {selectedTable.operational_status === 'BILL_PENDING' && (
                <ActionButton onClick={handleClose} loading={actionLoading} color="green">Close Table</ActionButton>
              )}
              <ActionButton onClick={() => setStatus('CLEANING')} loading={actionLoading} color="orange">Set Cleaning</ActionButton>
              <ActionButton onClick={() => setStatus('OUT_OF_SERVICE')} loading={actionLoading} color="red">Out of Service</ActionButton>
              {selectedTable.operational_status !== 'AVAILABLE' && (
                <ActionButton onClick={() => setStatus('AVAILABLE')} loading={actionLoading} color="green">Set Available</ActionButton>
              )}
              <button
                onClick={() => setSelectedTable(null)}
                className="w-full text-sm text-gray-500 hover:text-gray-300 mt-1"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ActionButton({ onClick, loading, color, children }: { onClick: () => void; loading?: boolean; color: string; children: React.ReactNode }) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20 hover:bg-blue-500/20',
    yellow: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20 hover:bg-yellow-500/20',
    green: 'bg-green-500/10 text-green-400 border-green-500/20 hover:bg-green-500/20',
    orange: 'bg-orange-500/10 text-orange-400 border-orange-500/20 hover:bg-orange-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/20',
  }
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`w-full border rounded-lg py-2 text-sm font-medium disabled:opacity-40 transition-colors ${colors[color] ?? 'bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-700'}`}
    >
      {loading ? '…' : children}
    </button>
  )
}
