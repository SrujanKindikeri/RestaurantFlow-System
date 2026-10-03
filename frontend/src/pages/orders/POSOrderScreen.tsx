// =============================================================================
// RestaurantFlow — POS Order Screen
// Phase 6: Fast order entry for counter, takeaway, and dine-in
//
// Flow:
//   1. Select branch (auto-selected if user has only one)
//   2. Select order type (DINE_IN / COUNTER / TAKEAWAY)
//   3. Select table (DINE_IN) or counter (COUNTER/TAKEAWAY)
//   4. Browse catalog, add items
//   5. Save DRAFT or CONFIRM
// =============================================================================

import { useState, useEffect, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { cn } from '@/utils/cn'
import { useAuth } from '@/contexts/AuthContext'
import { useTables, useCreateOrder, useAddOrderItem, useConfirmOrder } from '@/hooks/useOrders'
import { MenuCategoryTabs } from '@/components/orders/MenuCategoryTabs'
import { MenuItemCard } from '@/components/orders/MenuItemCard'

import { getBranchCatalog } from '@/services/menu'
import { listCounters, listSessions } from '@/services/counters'
import type {
  OrderType, DiningTable, CatalogItem, CatalogCategory,
} from '@/types'

// ---------------------------------------------------------------------------
// Local cart state — items before the order is created on the backend
// ---------------------------------------------------------------------------

interface CartItem {
  menu_item_id: string
  name: string
  price: number
  tax_rate: string | null
  tax_code: string | null
  quantity: number
  notes: string
}

export function POSOrderScreen() {
  const navigate  = useNavigate()
  const [params]  = useSearchParams()
  const { user }  = useAuth()

  // Step state
  const [orderType,    setOrderType]    = useState<OrderType>('COUNTER')
  const [branchId,     setBranchId]     = useState<string>('')
  const [selectedTable, setSelectedTable] = useState<DiningTable | null>(null)
  const [counterId,    setCounterId]    = useState<string>('')
  const [sessionId,    setSessionId]    = useState<string>('')  // counter session
  const [tableSessionId, setTableSessionId] = useState<string>('')
  const [activeCatId,  setActiveCatId]  = useState<string | null>(null)
  const [searchQuery,  setSearchQuery]  = useState('')
  const [cart,         setCart]         = useState<CartItem[]>([])
  const [orderId,      setOrderId]      = useState<string | null>(null)
  const [orderNumber,  setOrderNumber]  = useState<string | null>(null)
  const [orderStatus,  setOrderStatus]  = useState<'idle' | 'creating' | 'created' | 'confirmed' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Pre-fill from query params (coming from table grid)
  useEffect(() => {
    const tableParam   = params.get('table')
    const sessionParam = params.get('session')
    if (tableParam) {
      setOrderType('DINE_IN')
    }
    if (sessionParam) {
      setTableSessionId(sessionParam)
    }
  }, [params])

  // Accessible branches from user scope
  const branchOptions = useMemo(() => {
    const branches: { id: string; name: string }[] = []
    user?.scope?.roles?.forEach((r) => {
      if (r.branch) branches.push({ id: r.branch.id, name: r.branch.name })
    })
    return branches
  }, [user])

  // Auto-select first branch
  useEffect(() => {
    if (!branchId && branchOptions.length > 0) {
      setBranchId(branchOptions[0].id)
    }
  }, [branchOptions, branchId])

  // Catalog
  const { data: catalog } = useQuery({
    queryKey: ['branch-catalog', branchId],
    queryFn: () => getBranchCatalog(branchId),
    enabled: !!branchId,
  })

  const categories: CatalogCategory[] = catalog?.categories ?? []

  // Auto-select first category
  useEffect(() => {
    if (!activeCatId && categories.length > 0) {
      setActiveCatId(categories[0].id)
    }
  }, [categories, activeCatId])

  // Tables for DINE_IN
  const { data: tablesData } = useTables({ branch: branchId, occupied: false })
  const availableTables = tablesData?.results?.filter((t) => t.status === 'ACTIVE' && !t.is_occupied) ?? []

  // Counters for COUNTER/TAKEAWAY
  const { data: countersData } = useQuery({
    queryKey: ['counters-for-branch', branchId],
    queryFn: () => listCounters({ branch: branchId, status: 'ACTIVE' }),
    enabled: !!branchId && orderType !== 'DINE_IN',
  })
  const counters = countersData?.results ?? []

  // Open sessions for selected counter
  const { data: sessionsData } = useQuery({
    queryKey: ['counter-sessions-open', counterId],
    queryFn: () => listSessions({ counter: counterId, status: 'OPEN' }),
    enabled: !!counterId,
  })
  const openSessions = sessionsData?.results ?? []

  useEffect(() => {
    if (openSessions.length > 0 && !sessionId) {
      setSessionId(openSessions[0].id)
    }
  }, [openSessions, sessionId])

  // Filtered items
  const activeCategory = categories.find((c) => c.id === activeCatId)
  const filteredItems: CatalogItem[] = useMemo(() => {
    const source = searchQuery
      ? categories.flatMap((c) => c.items)
      : (activeCategory?.items ?? [])
    if (!searchQuery) return source
    const q = searchQuery.toLowerCase()
    return source.filter(
      (i) => i.name.toLowerCase().includes(q) || i.sku?.toLowerCase().includes(q),
    )
  }, [searchQuery, activeCategory, categories])

  // Mutations
  const createOrder  = useCreateOrder()
  const addItem      = useAddOrderItem(orderId ?? '')
  const confirmOrder = useConfirmOrder()

  // Cart total
  const cartTotal = cart.reduce((acc, item) => acc + item.price * item.quantity, 0)
  const cartCount = cart.reduce((acc, item) => acc + item.quantity, 0)

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  function addToCart(item: CatalogItem) {
    if (!item.price) return
    setCart((prev) => {
      const existing = prev.find((i) => i.menu_item_id === item.id)
      if (existing) {
        return prev.map((i) =>
          i.menu_item_id === item.id ? { ...i, quantity: i.quantity + 1 } : i,
        )
      }
      return [
        ...prev,
        {
          menu_item_id: item.id,
          name: item.name,
          price: parseFloat(item.price!),
          tax_rate: item.tax_rate,
          tax_code: item.tax_rate_code,
          quantity: 1,
          notes: '',
        },
      ]
    })
  }

  function updateCartQty(menuItemId: string, delta: number) {
    setCart((prev) => {
      const updated = prev.map((i) =>
        i.menu_item_id === menuItemId ? { ...i, quantity: i.quantity + delta } : i,
      )
      return updated.filter((i) => i.quantity > 0)
    })
  }

  function removeFromCart(menuItemId: string) {
    setCart((prev) => prev.filter((i) => i.menu_item_id !== menuItemId))
  }

  async function handleSaveDraft() {
    if (!branchId) { setErrorMessage('Please select a branch.'); return }
    if (cart.length === 0) { setErrorMessage('Add at least one item.'); return }
    setErrorMessage(null)
    setOrderStatus('creating')

    try {
      const payload: any = {
        branch: branchId,
        order_type: orderType,
      }

      if (orderType === 'DINE_IN') {
        if (!selectedTable) { setErrorMessage('Please select a table.'); setOrderStatus('idle'); return }
        if (!tableSessionId) { setErrorMessage('No open table session. Open a session first.'); setOrderStatus('idle'); return }
        payload.table = selectedTable.id
        payload.table_session = tableSessionId
      } else {
        if (!counterId) { setErrorMessage('Please select a counter.'); setOrderStatus('idle'); return }
        if (!sessionId) { setErrorMessage('No open counter session. Open a session first.'); setOrderStatus('idle'); return }
        payload.counter = counterId
        payload.counter_session = sessionId
      }

      const order = await createOrder.mutateAsync(payload)
      setOrderId(order.id)
      setOrderNumber(order.order_number)

      // Add all cart items
      for (const cartItem of cart) {
        await addItem.mutateAsync({
          menu_item: cartItem.menu_item_id,
          quantity: cartItem.quantity.toString(),
          notes: cartItem.notes,
        })
      }

      setOrderStatus('created')
    } catch (e: any) {
      const msg = e?.response?.data?.message || e?.message || 'Failed to create order.'
      setErrorMessage(msg)
      setOrderStatus('error')
    }
  }

  async function handleConfirm() {
    if (!orderId) {
      await handleSaveDraft()
      return
    }
    setErrorMessage(null)
    try {
      await confirmOrder.mutateAsync(orderId)
      setOrderStatus('confirmed')
      navigate(`/orders/${orderId}`)
    } catch (e: any) {
      const msg = e?.response?.data?.message || e?.message || 'Failed to confirm order.'
      setErrorMessage(msg)
      setOrderStatus('error')
    }
  }

  const isCreating = createOrder.isPending || addItem.isPending || confirmOrder.isPending

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (orderStatus === 'confirmed') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center">
          <svg className="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <p className="text-lg font-semibold text-gray-100">Order Confirmed</p>
        <p className="text-sm text-gray-400 font-mono">{orderNumber}</p>
        <div className="flex gap-3">
          <button onClick={() => navigate(`/orders/${orderId}`)} className="px-4 py-2 rounded-lg bg-brand-500 text-white text-sm">
            View Order
          </button>
          <button onClick={() => { setCart([]); setOrderId(null); setOrderNumber(null); setOrderStatus('idle') }} className="px-4 py-2 rounded-lg bg-gray-800 text-gray-300 text-sm">
            New Order
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      {/* ------------------------------------------------------------------ */}
      {/* LEFT: Menu catalog                                                  */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800 bg-gray-900 flex-shrink-0">
          <button
            onClick={() => navigate('/tables')}
            className="text-gray-600 hover:text-gray-300 transition-colors"
            aria-label="Back"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          {/* Branch selector */}
          <select
            value={branchId}
            onChange={(e) => { setBranchId(e.target.value); setActiveCatId(null) }}
            className="text-xs bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-2 py-1 focus:outline-none focus:border-brand-500"
            aria-label="Select branch"
          >
            <option value="">Select branch…</option>
            {branchOptions.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>

          {/* Order type toggle */}
          <div className="flex rounded-lg overflow-hidden border border-gray-700 flex-shrink-0" role="group" aria-label="Order type">
            {(['COUNTER', 'TAKEAWAY', 'DINE_IN'] as OrderType[]).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setOrderType(type)}
                className={cn(
                  'px-2.5 py-1 text-[10px] font-medium transition-colors',
                  orderType === type
                    ? 'bg-brand-500 text-white'
                    : 'bg-gray-800 text-gray-500 hover:text-gray-300',
                )}
                aria-pressed={orderType === type}
              >
                {type === 'DINE_IN' ? 'Dine In' : type === 'TAKEAWAY' ? 'Takeaway' : 'Counter'}
              </button>
            ))}
          </div>

          {/* Order number badge */}
          {orderNumber && (
            <span className="text-xs font-mono text-brand-400 ml-auto">
              {orderNumber}
            </span>
          )}

          {/* Search */}
          <div className="relative ml-auto">
            <input
              type="search"
              placeholder="Search menu…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-44 pl-7 pr-3 py-1.5 rounded-lg text-xs bg-gray-800 border border-gray-700 text-gray-300 placeholder-gray-600 focus:outline-none focus:border-brand-500"
              aria-label="Search menu items"
            />
            <svg className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        {/* Category tabs */}
        {!searchQuery && (
          <div className="px-4 pt-3 pb-1 border-b border-gray-800 flex-shrink-0">
            <MenuCategoryTabs
              categories={categories}
              activeCategoryId={activeCatId}
              onSelect={setActiveCatId}
            />
          </div>
        )}

        {/* Menu items grid */}
        <div className="flex-1 overflow-y-auto p-4">
          {!branchId ? (
            <div className="flex items-center justify-center h-full text-gray-600 text-sm">
              Select a branch to view the menu.
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-600 text-sm">
              {searchQuery ? 'No items match your search.' : 'No items in this category.'}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {filteredItems.map((item) => (
                <MenuItemCard key={item.id} item={item} onAdd={addToCart} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* RIGHT: Order panel                                                  */}
      {/* ------------------------------------------------------------------ */}
      <div className="w-80 flex flex-col border-l border-gray-800 bg-gray-900 flex-shrink-0">
        {/* Order header */}
        <div className="px-4 py-3 border-b border-gray-800 flex-shrink-0">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-200">
              {orderStatus === 'created' ? 'Order' : 'New Order'}
            </p>
            {orderStatus === 'created' && orderNumber && (
              <span className="text-xs font-mono text-brand-400">{orderNumber}</span>
            )}
          </div>

          {/* Table / counter selector */}
          {orderType === 'DINE_IN' ? (
            <div className="mt-2">
              <select
                value={selectedTable?.id ?? ''}
                onChange={(e) => {
                  const t = availableTables.find((x) => x.id === e.target.value) ?? null
                  setSelectedTable(t)
                  setTableSessionId(t?.active_session_id ?? '')
                }}
                className="w-full text-xs bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:border-brand-500"
                aria-label="Select table"
              >
                <option value="">Select table…</option>
                {availableTables.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.table_number}{t.section ? ` — ${t.section}` : ''} ({t.capacity} seats)
                  </option>
                ))}
              </select>
              {selectedTable && !tableSessionId && (
                <p className="text-[10px] text-yellow-400 mt-1">
                  No open session. Open a table session first.
                </p>
              )}
            </div>
          ) : (
            <div className="mt-2 space-y-1.5">
              <select
                value={counterId}
                onChange={(e) => { setCounterId(e.target.value); setSessionId('') }}
                className="w-full text-xs bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:border-brand-500"
                aria-label="Select counter"
              >
                <option value="">Select counter…</option>
                {counters.map((c) => (
                  <option key={c.id} value={c.id}>{c.code} — {c.name}</option>
                ))}
              </select>
              {counterId && openSessions.length === 0 && (
                <p className="text-[10px] text-yellow-400">
                  No open session on this counter.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Cart items */}
        <div className="flex-1 overflow-y-auto px-4 py-3">
          {cart.length === 0 ? (
            <p className="text-xs text-gray-600 text-center mt-8">
              Tap items in the menu to add them here.
            </p>
          ) : (
            <ul className="space-y-2" role="list">
              {cart.map((item) => (
                <li key={item.menu_item_id} className="flex items-center gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-200 truncate">{item.name}</p>
                    <p className="text-[10px] text-gray-500">₹{item.price.toFixed(2)}</p>
                  </div>

                  {/* Qty controls */}
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button
                      type="button"
                      onClick={() => updateCartQty(item.menu_item_id, -1)}
                      className="w-6 h-6 rounded bg-gray-700 hover:bg-gray-600 text-gray-300 flex items-center justify-center transition-colors"
                      aria-label={`Decrease ${item.name}`}
                    >
                      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M20 12H4" />
                      </svg>
                    </button>
                    <span className="w-6 text-center text-xs font-medium text-gray-200">
                      {item.quantity}
                    </span>
                    <button
                      type="button"
                      onClick={() => updateCartQty(item.menu_item_id, 1)}
                      className="w-6 h-6 rounded bg-gray-700 hover:bg-gray-600 text-gray-300 flex items-center justify-center transition-colors"
                      aria-label={`Increase ${item.name}`}
                    >
                      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                      </svg>
                    </button>
                  </div>

                  {/* Line total */}
                  <span className="text-xs font-medium text-gray-200 w-16 text-right flex-shrink-0">
                    ₹{(item.price * item.quantity).toFixed(2)}
                  </span>

                  {/* Remove */}
                  <button
                    type="button"
                    onClick={() => removeFromCart(item.menu_item_id)}
                    className="p-1 rounded text-gray-600 hover:text-red-400 transition-colors flex-shrink-0"
                    aria-label={`Remove ${item.name}`}
                  >
                    <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Totals + actions */}
        <div className="px-4 py-4 border-t border-gray-800 space-y-3 flex-shrink-0">
          {/* Total */}
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">{cartCount} item{cartCount !== 1 ? 's' : ''}</span>
            <span className="font-bold text-gray-100">₹{cartTotal.toFixed(2)}</span>
          </div>

          {/* Error */}
          {errorMessage && (
            <p className="text-xs text-red-400 bg-red-900/20 rounded px-2 py-1.5">
              {errorMessage}
            </p>
          )}

          {/* Buttons */}
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={handleSaveDraft}
              disabled={isCreating || cart.length === 0 || orderStatus === 'created'}
              className={cn(
                'py-2.5 rounded-lg text-sm font-medium transition-colors',
                'bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-700',
                'disabled:opacity-40 disabled:cursor-not-allowed',
              )}
            >
              {createOrder.isPending ? 'Saving…' : 'Save Draft'}
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={isCreating || cart.length === 0}
              className={cn(
                'py-2.5 rounded-lg text-sm font-medium transition-colors',
                'bg-brand-500 hover:bg-brand-400 text-white',
                'disabled:opacity-40 disabled:cursor-not-allowed',
              )}
            >
              {confirmOrder.isPending ? 'Confirming…' : 'Confirm Order'}
            </button>
          </div>

          {orderStatus === 'created' && orderId && (
            <button
              onClick={() => navigate(`/orders/${orderId}`)}
              className="w-full text-xs text-brand-400 hover:text-brand-300 text-center"
            >
              View order #{orderNumber} →
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
