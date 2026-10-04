// =============================================================================
// RestaurantFlow — Chart of Accounts Page
// Phase 13
// =============================================================================

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getAccountTree, listAccounts, deactivateAccount, type Account, type AccountTree } from '@/services/accounting'
import { useAuth } from '@/contexts/AuthContext'

const TYPE_BADGE: Record<string, string> = {
  ASSET:     'bg-blue-500/10 text-blue-400 border-blue-500/20',
  LIABILITY: 'bg-red-500/10 text-red-400 border-red-500/20',
  EQUITY:    'bg-purple-500/10 text-purple-400 border-purple-500/20',
  REVENUE:   'bg-green-500/10 text-green-400 border-green-500/20',
  EXPENSE:   'bg-amber-500/10 text-amber-400 border-amber-500/20',
}

function TreeNode({ node, depth = 0 }: { node: AccountTree; depth?: number }) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = node.children && node.children.length > 0
  const indent = depth * 20

  return (
    <div>
      <div
        className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-750 border-b border-gray-700/50 group"
        style={{ paddingLeft: `${16 + indent}px` }}
      >
        {/* Expand toggle */}
        <button
          onClick={() => setExpanded((v) => !v)}
          className="w-4 h-4 flex-shrink-0 text-gray-500"
        >
          {hasChildren ? (expanded ? '▾' : '▸') : <span className="opacity-0">▸</span>}
        </button>

        {/* Account code */}
        <span className="w-16 text-xs font-mono text-gray-400 flex-shrink-0">{node.code}</span>

        {/* Account name */}
        <span className={`flex-1 text-sm ${node.is_group ? 'font-semibold text-gray-200' : 'text-gray-300'}`}>
          {node.name}
        </span>

        {/* Type badge */}
        <span className={`px-2 py-0.5 rounded-full text-xs border ${TYPE_BADGE[node.account_type] ?? ''} hidden sm:inline-flex`}>
          {node.account_type}
        </span>

        {/* Normal balance */}
        <span className="text-xs text-gray-500 w-12 text-right hidden md:block">
          {node.normal_balance}
        </span>

        {/* Status */}
        {!node.is_active && (
          <span className="text-xs text-gray-500 bg-gray-700 px-2 py-0.5 rounded">Inactive</span>
        )}
        {!node.is_postable && node.is_active && (
          <span className="text-xs text-gray-500 bg-gray-700 px-2 py-0.5 rounded">Group</span>
        )}
      </div>
      {expanded && hasChildren && (
        <div>
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export function ChartOfAccountsPage() {
  const { user } = useAuth()
  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  const [tree, setTree] = useState<AccountTree[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [view, setView] = useState<'tree' | 'list'>('tree')
  const [accounts, setAccounts] = useState<Account[]>([])
  const [typeFilter, setTypeFilter] = useState('')

  useEffect(() => {
    if (!restaurantId) { setLoading(false); return }
    setLoading(true)
    Promise.all([
      getAccountTree(restaurantId),
      listAccounts({ restaurant: restaurantId }),
    ])
      .then(([t, a]) => { setTree(t); setAccounts(a) })
      .catch((e) => setError(e?.response?.data?.detail ?? 'Failed to load accounts'))
      .finally(() => setLoading(false))
  }, [restaurantId])

  const filteredAccounts = typeFilter
    ? accounts.filter((a) => a.account_type === typeFilter)
    : accounts

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Chart of Accounts</h1>
          <p className="text-sm text-gray-500 mt-1">Hierarchical account structure for double-entry bookkeeping</p>
        </div>
        <Link
          to="/accounting/accounts/new"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          + New Account
        </Link>
      </div>

      {/* View toggle + type filter */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
          <button
            onClick={() => setView('tree')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${view === 'tree' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
          >
            Tree
          </button>
          <button
            onClick={() => setView('list')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${view === 'list' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
          >
            List
          </button>
        </div>

        {view === 'list' && (
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
          >
            <option value="">All Types</option>
            <option value="ASSET">Asset</option>
            <option value="LIABILITY">Liability</option>
            <option value="EQUITY">Equity</option>
            <option value="REVENUE">Revenue</option>
            <option value="EXPENSE">Expense</option>
          </select>
        )}
      </div>

      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-10 bg-gray-800 rounded animate-pulse" />
          ))}
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>
      )}

      {!loading && !error && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          {/* Column headers */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-700 bg-gray-750">
            <span className="w-4 flex-shrink-0" />
            <span className="w-16 text-xs text-gray-500 font-medium flex-shrink-0">CODE</span>
            <span className="flex-1 text-xs text-gray-500 font-medium">NAME</span>
            <span className="text-xs text-gray-500 font-medium hidden sm:block">TYPE</span>
            <span className="w-12 text-xs text-gray-500 font-medium text-right hidden md:block">BALANCE</span>
          </div>

          {/* Tree view */}
          {view === 'tree' && tree.map((root) => (
            <TreeNode key={root.id} node={root} />
          ))}

          {/* List view */}
          {view === 'list' && filteredAccounts.map((acct) => (
            <div key={acct.id} className="flex items-center gap-3 px-4 py-2.5 border-b border-gray-700/50 hover:bg-gray-750">
              <span className="w-4 flex-shrink-0" />
              <span className="w-16 text-xs font-mono text-gray-400 flex-shrink-0">{acct.code}</span>
              <span className="flex-1 text-sm text-gray-300">{acct.name}</span>
              <span className={`px-2 py-0.5 rounded-full text-xs border hidden sm:inline-flex ${TYPE_BADGE[acct.account_type] ?? ''}`}>
                {acct.account_type}
              </span>
              <span className="text-xs text-gray-500 w-12 text-right hidden md:block">{acct.normal_balance}</span>
              {!acct.is_active && (
                <span className="text-xs bg-gray-700 text-gray-500 px-2 py-0.5 rounded">Inactive</span>
              )}
            </div>
          ))}

          {view === 'tree' && tree.length === 0 && !loading && (
            <div className="px-4 py-8 text-center text-gray-500 text-sm">
              No accounts found. Create your first account to get started.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
