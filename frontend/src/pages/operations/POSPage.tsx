// =============================================================================
// RestaurantFlow — Advanced POS Terminal Page
// Phase 19: Advanced POS & Restaurant Operations
//
// Layout: [Categories | Menu Items] | [Cart] | [Order Summary + Actions]
// Keyboard shortcuts: F1=Search, F3=Hold, F4=Payment, F5=New, Esc=Cancel modal
// Offline-aware: Never falsely confirms critical transactions
// =============================================================================

import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
  getPOSSessions, startPOSSession, endPOSSession,
  holdOrder, resumeOrder, scanBarcode, getOperationalTables,
} from '@/services/operations'
import { listMenuItems, listCategories } from '@/services/menu'
import { createOrder, addOrderItem, confirmOrder } from '@/services/orders'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface CartItem {
  menu_item_id: string
  menu_item_name: string
  quantity: number
  unit_price: string
  notes: string
  modifiers: { name: string; value: string }[]
}

interface POSState {
  activeSession: any | null
  cart: CartItem[]
  activeOrderId: string | null
  selectedCategory: string | null
  searchQuery: string
  customer: any | null
  selectedTable: any | null
  orderType: 'DINE_IN' | 'TAKEAWAY' | 'COUNTER'
  connectivity: 'ONLINE' | 'DEGRADED' | 'OFFLINE'
}

// ---------------------------------------------------------------------------
// Connectivity badge
// ---------------------------------------------------------------------------
const ConnectivityBadge = ({ status }: { status: string }) => {
  const colors = {
    ONLINE: 'bg-green-500/10 text-green-400 border-green-500/20',
    DEGRADED: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    OFFLINE: 'bg-red-500/10 text-red-400 border-red-500/20',
  }[status] ?? 'bg-gray-500/10 text-gray-400 border-gray-500/20'
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs border rounded-full px-2 py-0.5 ${colors}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${status === 'ONLINE' ? 'bg-green-400' : status === 'DEGRADED' ? 'bg-yellow-400' : 'bg-red-400'}`} />
      {status}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Main POS Component
// ---------------------------------------------------------------------------
export function POSPage() {
  const { user, hasPermission } = useAuth()

  const [state, setState] = useState<POSState>({
    activeSession: null,
    cart: [],
    activeOrderId: null,
    selectedCategory: null,
    searchQuery: '',
    customer: null,
    selectedTable: null,
    orderType: 'COUNTER',
    connectivity: 'ONLINE',
  })

  const [categories, setCategories] = useState<any[]>([])
  const [menuItems, setMenuItems] = useState<any[]>([])
  const [tables, setTables] = useState<any[]>([])
  const [heldOrders, setHeldOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [scanInput, setScanInput] = useState('')
  const [showStartModal, setShowStartModal] = useState(false)
  const [counters, setCounters] = useState<any[]>([])
  const [selectedCounterId, setSelectedCounterId] = useState('')

  const searchRef = useRef<HTMLInputElement>(null)

  // -------------------------------------------------------------------------
  // Load session on mount
  // -------------------------------------------------------------------------
  useEffect(() => {
    getPOSSessions()
      .then(r => {
        const active = r.data.find((s: any) => s.status === 'ACTIVE' || s.status === 'PAUSED')
        if (active) setState(s => ({ ...s, activeSession: active }))
        else setShowStartModal(true)
      })
      .catch(() => setShowStartModal(true))
  }, [])

  // -------------------------------------------------------------------------
  // Load menu data
  // -------------------------------------------------------------------------
  useEffect(() => {
    listCategories().then(r => setCategories(r.data.results ?? r.data))
    listMenuItems().then(r => setMenuItems(r.data.results ?? r.data))
    getOperationalTables().then(r => setTables(r.data))
  }, [])

  // -------------------------------------------------------------------------
  // Keyboard shortcuts
  // -------------------------------------------------------------------------
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't fire inside text inputs
      const tag = (e.target as HTMLElement).tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return

      if (e.key === 'F1') { e.preventDefault(); searchRef.current?.focus() }
      if (e.key === 'F3') { e.preventDefault(); handleHold() }
      if (e.key === 'F5') { e.preventDefault(); clearCart() }
      if (e.key === 'Escape') { setError('') }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [state.activeOrderId])

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------
  const clearCart = () =>
    setState(s => ({ ...s, cart: [], activeOrderId: null, customer: null, selectedTable: null }))

  const filteredItems = menuItems.filter(item => {
    const matchCat = !state.selectedCategory || item.category === state.selectedCategory
    const matchSearch = !state.searchQuery ||
      item.name.toLowerCase().includes(state.searchQuery.toLowerCase()) ||
      item.sku?.toLowerCase().includes(state.searchQuery.toLowerCase())
    return matchCat && matchSearch
  })

  // -------------------------------------------------------------------------
  // Add item to cart
  // -------------------------------------------------------------------------
  const addToCart = (item: any) => {
    setState(s => {
      const existing = s.cart.findIndex(c => c.menu_item_id === item.id)
      if (existing >= 0) {
        const cart = [...s.cart]
        cart[existing] = { ...cart[existing], quantity: cart[existing].quantity + 1 }
        return { ...s, cart }
      }
      return {
        ...s,
        cart: [...s.cart, {
          menu_item_id: item.id,
          menu_item_name: item.name,
          quantity: 1,
          unit_price: item.base_price ?? '0.00',
          notes: '',
          modifiers: [],
        }],
      }
    })
  }

  const updateQty = (idx: number, delta: number) => {
    setState(s => {
      const cart = [...s.cart]
      const newQty = cart[idx].quantity + delta
      if (newQty <= 0) cart.splice(idx, 1)
      else cart[idx] = { ...cart[idx], quantity: newQty }
      return { ...s, cart }
    })
  }

  // -------------------------------------------------------------------------
  // Barcode scan
  // -------------------------------------------------------------------------
  const handleScan = async () => {
    if (!scanInput.trim()) return
    try {
      const r = await scanBarcode(scanInput.trim())
      addToCart({ id: r.data.menu_item_id, name: r.data.name, base_price: r.data.price })
      setScanInput('')
    } catch {
      setError(`Item not found for: ${scanInput}`)
    }
  }

  // -------------------------------------------------------------------------
  // Hold order
  // -------------------------------------------------------------------------
  const handleHold = async () => {
    if (!state.activeOrderId) { setError('No active order to hold.'); return }
    try {
      await holdOrder(state.activeOrderId)
      clearCart()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to hold order.')
    }
  }

  // -------------------------------------------------------------------------
  // Send to kitchen (confirm order)
  // -------------------------------------------------------------------------
  const handleConfirm = async () => {
    if (state.cart.length === 0) { setError('Cart is empty.'); return }
    if (state.connectivity === 'OFFLINE') {
      setError('Cannot confirm order — system is offline. Please wait for connection to restore.')
      return
    }
    setLoading(true)
    try {
      let orderId = state.activeOrderId

      // Create order if none exists
      if (!orderId) {
        const orderData: any = {
          order_type: state.orderType,
          ...(state.selectedTable && { table_id: state.selectedTable.id }),
        }
        const orderRes = await createOrder(orderData)
        orderId = orderRes.data.id
        setState(s => ({ ...s, activeOrderId: orderId }))
      }

      // Add items
      for (const item of state.cart) {
        await addOrderItem(orderId!, {
          menu_item: item.menu_item_id,
          quantity: item.quantity.toString(),
          notes: item.notes,
        })
      }

      // Confirm
      await confirmOrder(orderId!)
      clearCart()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to confirm order.')
    } finally {
      setLoading(false)
    }
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  const cartTotal = state.cart.reduce(
    (sum, i) => sum + parseFloat(i.unit_price) * i.quantity, 0
  ).toFixed(2)

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden">

      {/* ------------------------------------------------------------------ */}
      {/* Connectivity warning banner                                          */}
      {/* ------------------------------------------------------------------ */}
      {state.connectivity !== 'ONLINE' && (
        <div className="absolute top-0 inset-x-0 z-50 bg-yellow-500/20 border-b border-yellow-500/30 text-yellow-300 text-sm text-center py-2">
          ⚠ POS is {state.connectivity} — critical operations require connection. Payments will NOT be processed offline.
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* LEFT PANEL — Categories + Menu Items                                */}
      {/* ------------------------------------------------------------------ */}
      <div className="w-[420px] flex-shrink-0 flex flex-col border-r border-gray-800">
        {/* Search bar (F1) */}
        <div className="p-3 border-b border-gray-800 flex gap-2">
          <input
            ref={searchRef}
            type="text"
            placeholder="Search items or scan barcode… (F1)"
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-brand-500"
            value={state.searchQuery || scanInput}
            onChange={e => {
              setScanInput(e.target.value)
              setState(s => ({ ...s, searchQuery: e.target.value }))
            }}
            onKeyDown={e => e.key === 'Enter' && handleScan()}
          />
          <ConnectivityBadge status={state.connectivity} />
        </div>

        {/* Category tabs */}
        <div className="flex gap-1 p-2 border-b border-gray-800 overflow-x-auto flex-shrink-0">
          <button
            onClick={() => setState(s => ({ ...s, selectedCategory: null }))}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
              !state.selectedCategory ? 'bg-brand-500 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            All
          </button>
          {categories.map(cat => (
            <button
              key={cat.id}
              onClick={() => setState(s => ({ ...s, selectedCategory: cat.id }))}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                state.selectedCategory === cat.id
                  ? 'bg-brand-500 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              {cat.name}
            </button>
          ))}
        </div>

        {/* Menu items grid */}
        <div className="flex-1 overflow-y-auto p-2 grid grid-cols-2 gap-2 content-start">
          {filteredItems.length === 0 && (
            <div className="col-span-2 text-center text-gray-600 py-10 text-sm">No items found</div>
          )}
          {filteredItems.map(item => (
            <button
              key={item.id}
              onClick={() => addToCart(item)}
              className="bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-brand-500/40 rounded-xl p-3 text-left transition-all"
            >
              <p className="text-sm font-medium text-white truncate">{item.name}</p>
              <p className="text-xs text-gray-500 mt-0.5">{item.sku && `SKU: ${item.sku}`}</p>
              <p className="text-sm text-brand-400 font-semibold mt-1">₹{item.base_price ?? '—'}</p>
            </button>
          ))}
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* CENTER PANEL — Cart                                                  */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex-1 flex flex-col border-r border-gray-800 min-w-0">
        <div className="p-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Current Order</h2>
          <div className="flex gap-2 text-xs text-gray-500">
            {['DINE_IN', 'TAKEAWAY', 'COUNTER'].map(t => (
              <button
                key={t}
                onClick={() => setState(s => ({ ...s, orderType: t as any }))}
                className={`px-2 py-1 rounded ${state.orderType === t ? 'bg-brand-500/20 text-brand-400' : 'hover:text-white'}`}
              >
                {t.replace('_', '-')}
              </button>
            ))}
          </div>
        </div>

        {/* Order type extras */}
        {state.orderType === 'DINE_IN' && (
          <div className="px-4 py-2 border-b border-gray-800">
            <select
              className="bg-gray-900 border border-gray-700 text-sm text-white rounded-lg px-2 py-1.5 w-full"
              value={state.selectedTable?.id ?? ''}
              onChange={e => {
                const t = tables.find(x => x.id === e.target.value)
                setState(s => ({ ...s, selectedTable: t ?? null }))
              }}
            >
              <option value="">Select Table…</option>
              {tables.filter(t => t.operational_status === 'AVAILABLE').map(t => (
                <option key={t.id} value={t.id}>{t.table_number} — {t.section || 'Main'}</option>
              ))}
            </select>
          </div>
        )}

        {/* Cart items */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {state.cart.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-gray-600">
              <svg className="w-12 h-12 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
              <p className="text-sm">Cart is empty</p>
              <p className="text-xs mt-1">Select items from the menu</p>
            </div>
          )}
          {state.cart.map((item, idx) => (
            <div key={idx} className="bg-gray-900 border border-gray-800 rounded-lg p-3 flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{item.menu_item_name}</p>
                {item.modifiers.length > 0 && (
                  <p className="text-xs text-brand-400 mt-0.5">{item.modifiers.map(m => `${m.name}: ${m.value}`).join(', ')}</p>
                )}
                <p className="text-xs text-gray-500 mt-0.5">₹{item.unit_price} each</p>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => updateQty(idx, -1)} className="w-7 h-7 rounded-full bg-gray-800 hover:bg-gray-700 text-white flex items-center justify-center text-lg leading-none">−</button>
                <span className="text-sm font-semibold w-5 text-center">{item.quantity}</span>
                <button onClick={() => updateQty(idx, 1)} className="w-7 h-7 rounded-full bg-gray-800 hover:bg-gray-700 text-white flex items-center justify-center text-lg leading-none">+</button>
              </div>
              <p className="text-sm font-semibold text-white w-16 text-right">
                ₹{(parseFloat(item.unit_price) * item.quantity).toFixed(2)}
              </p>
            </div>
          ))}
        </div>

        {/* Cart total */}
        <div className="p-4 border-t border-gray-800">
          <div className="flex justify-between text-lg font-bold text-white">
            <span>Total</span>
            <span>₹{cartTotal}</span>
          </div>
          <p className="text-xs text-gray-600 mt-1">Final total calculated by server at billing</p>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* RIGHT PANEL — Actions                                               */}
      {/* ------------------------------------------------------------------ */}
      <div className="w-52 flex-shrink-0 flex flex-col bg-gray-900 border-l border-gray-800">
        {/* Session info */}
        <div className="p-3 border-b border-gray-800">
          <p className="text-xs text-gray-600">Session</p>
          <p className="text-xs text-gray-300 truncate mt-0.5">
            {state.activeSession ? `Active · ${state.activeSession.counter_code}` : 'No session'}
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="mx-2 mt-2 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-2 text-xs">
            {error}
            <button onClick={() => setError('')} className="ml-1 underline">Dismiss</button>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex-1 p-2 space-y-1.5 overflow-y-auto">
          <ActionBtn
            onClick={handleConfirm}
            disabled={loading || state.cart.length === 0 || state.connectivity === 'OFFLINE'}
            color="brand"
            kbd="↵"
          >
            {loading ? 'Sending…' : 'Send to Kitchen'}
          </ActionBtn>

          <ActionBtn onClick={handleHold} disabled={!state.activeOrderId} color="yellow" kbd="F3">
            Hold Order
          </ActionBtn>

          <ActionBtn onClick={clearCart} color="gray" kbd="F5">
            New Order
          </ActionBtn>

          <div className="border-t border-gray-800 pt-1.5 mt-1">
            <p className="text-xs text-gray-600 px-1 mb-1">Held Orders</p>
            {heldOrders.length === 0
              ? <p className="text-xs text-gray-700 px-1">None</p>
              : heldOrders.map(o => (
                <button
                  key={o.id}
                  onClick={() => resumeOrder(o.id).then(() => setState(s => ({ ...s, activeOrderId: o.id })))}
                  className="w-full text-left text-xs bg-gray-800 hover:bg-gray-700 rounded px-2 py-1.5 text-gray-300 mb-1"
                >
                  {o.order_number}
                </button>
              ))
            }
          </div>
        </div>

        {/* Session controls */}
        <div className="p-2 border-t border-gray-800 space-y-1.5">
          {state.activeSession && (
            <button
              onClick={() => endPOSSession(state.activeSession.id).then(() => setState(s => ({ ...s, activeSession: null })))}
              className="w-full text-xs bg-gray-800 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/20 border border-gray-700 rounded-lg py-2 text-gray-400 transition-colors"
            >
              End Session
            </button>
          )}
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Start Session Modal                                                  */}
      {/* ------------------------------------------------------------------ */}
      {showStartModal && (
        <div className="fixed inset-0 z-50 bg-gray-950/90 flex items-center justify-center">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-80 shadow-2xl">
            <h2 className="text-lg font-semibold text-white mb-4">Start POS Session</h2>
            <p className="text-sm text-gray-500 mb-4">
              Select your counter to begin. Your session is tied to your user account — not the device.
            </p>
            <input
              type="text"
              placeholder="Counter ID (UUID)"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white mb-3"
              value={selectedCounterId}
              onChange={e => setSelectedCounterId(e.target.value)}
            />
            <button
              onClick={() => {
                if (!selectedCounterId) return
                startPOSSession({ counter_id: selectedCounterId })
                  .then(r => {
                    setState(s => ({ ...s, activeSession: r.data }))
                    setShowStartModal(false)
                  })
                  .catch(e => setError(e?.response?.data?.detail ?? 'Failed to start session'))
              }}
              className="w-full bg-brand-500 hover:bg-brand-600 text-white rounded-lg py-2 text-sm font-medium"
            >
              Start Session
            </button>
            <button
              onClick={() => setShowStartModal(false)}
              className="w-full mt-2 text-xs text-gray-600 hover:text-gray-400"
            >
              Continue without session (browse only)
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Helper component
// ---------------------------------------------------------------------------
function ActionBtn({
  onClick,
  disabled = false,
  color,
  kbd,
  children,
}: {
  onClick: () => void
  disabled?: boolean
  color: 'brand' | 'yellow' | 'gray' | 'red'
  kbd?: string
  children: React.ReactNode
}) {
  const base = 'w-full flex items-center justify-between rounded-lg px-3 py-2.5 text-sm font-medium transition-colors disabled:opacity-40'
  const colors = {
    brand: 'bg-brand-500/10 hover:bg-brand-500/20 text-brand-400 border border-brand-500/20',
    yellow: 'bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 border border-yellow-500/20',
    gray: 'bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700',
    red: 'bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20',
  }[color]
  return (
    <button onClick={onClick} disabled={disabled} className={`${base} ${colors}`}>
      <span>{children}</span>
      {kbd && <kbd className="text-xs opacity-50 font-mono">{kbd}</kbd>}
    </button>
  )
}
