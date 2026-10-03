// =============================================================================
// RestaurantFlow — Main Layout
// Phase 3: Auth-aware sidebar with user info, dynamic nav, logout
// =============================================================================

import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { cn } from '@/utils/cn'
import { useAuth } from '@/contexts/AuthContext'

interface NavItem {
  label: string
  to: string
  permission?: string
  icon: React.ReactNode
}

const ICONS = {
  dashboard: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  ),
  organizations: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
    </svg>
  ),
  restaurants: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
    </svg>
  ),
  branches: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
      <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  users: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
      <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  roles: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  ),
  counters: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
    </svg>
  ),
  sessions: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  menu: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
    </svg>
  ),
  tables: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M3 14h18M10 10V4m0 16V14M14 10V4m0 16V14" />
    </svg>
  ),
  orders: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
    </svg>
  ),
  pos: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
    </svg>
  ),
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', to: '/', icon: ICONS.dashboard },
  { label: 'Organizations', to: '/organizations', permission: 'organization.view', icon: ICONS.organizations },
  { label: 'Restaurants', to: '/restaurants', permission: 'restaurant.view', icon: ICONS.restaurants },
  { label: 'Branches', to: '/branches', permission: 'branch.view', icon: ICONS.branches },
  { label: 'Users', to: '/users', permission: 'user.view', icon: ICONS.users },
  { label: 'Roles', to: '/roles', permission: 'role.view', icon: ICONS.roles },
  // Phase 4 — Counters
  { label: 'Counter Dashboard', to: '/counter-dashboard', permission: 'counter.view', icon: ICONS.sessions },
  { label: 'Counters', to: '/counters', permission: 'counter.view', icon: ICONS.counters },
  { label: 'Sessions', to: '/counter-sessions', permission: 'counter.session.view', icon: ICONS.sessions },
  // Phase 5 — Menu
  { label: 'Menu', to: '/menu', permission: 'menu.view', icon: ICONS.menu },
  { label: 'Categories', to: '/menu/categories', permission: 'category.view', icon: ICONS.menu },
  { label: 'Menu Items', to: '/menu/items', permission: 'menu.view', icon: ICONS.menu },
  { label: 'Pricing', to: '/menu/pricing', permission: 'menu.price.view', icon: ICONS.menu },
  { label: 'Availability', to: '/menu/availability', permission: 'menu.availability.view', icon: ICONS.menu },
  { label: 'Tax Rates', to: '/menu/tax-rates', permission: 'tax.view', icon: ICONS.menu },
  // Phase 6 — Tables + Orders
  { label: 'Tables', to: '/tables', permission: 'table.view', icon: ICONS.tables },
  { label: 'Orders', to: '/orders', permission: 'order.view.branch', icon: ICONS.orders },
  { label: 'POS', to: '/pos', permission: 'order.create.counter', icon: ICONS.pos },
]

const COUNTER_PERMS = new Set(['counter.view', 'counter.session.view'])
const MENU_PERMS = new Set(['menu.view', 'category.view', 'menu.price.view', 'menu.availability.view', 'tax.view'])
const ORDER_PERMS = new Set(['table.view', 'order.view.branch', 'order.create.dine_in', 'order.create.counter', 'order.create.takeaway'])

export function MainLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user, logout, hasPermission } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  // Filter nav items to those the user has permission for
  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.permission || hasPermission(item.permission) || user?.is_staff || user?.scope?.is_superuser,
  )

  // Primary role label for the header
  const primaryRole = user?.scope?.roles?.[0]?.role_name ?? 'User'

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex">

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-gray-950/80 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-60 flex flex-col bg-gray-900 border-r border-gray-800',
          'transform transition-transform duration-200 ease-in-out',
          'lg:static lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
        aria-label="Sidebar navigation"
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 h-14 border-b border-gray-800 flex-shrink-0">
          <div className="w-7 h-7 rounded-lg bg-brand-500 flex items-center justify-center flex-shrink-0">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 text-white" aria-hidden="true">
              <path d="M3 11l19-9-9 19-2-8-8-2z" />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-white text-sm tracking-tight truncate">RestaurantFlow</p>
            <p className="text-[10px] text-gray-600 font-mono">Phase 6</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto" aria-label="Main navigation">
          <p className="px-2 mb-2 text-[10px] font-semibold text-gray-700 uppercase tracking-widest">
            Management
          </p>
          <ul className="space-y-0.5" role="list">
            {visibleItems.filter(i => !COUNTER_PERMS.has(i.permission ?? '') && !MENU_PERMS.has(i.permission ?? '')).map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === '/'}
                  onClick={() => setSidebarOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                      isActive
                        ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20'
                        : 'text-gray-500 hover:text-gray-200 hover:bg-gray-800/60 border border-transparent',
                    )
                  }
                >
                  {item.icon}
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>

          {/* Phase 4 — Counters section */}
          {visibleItems.some(i => COUNTER_PERMS.has(i.permission ?? '')) && (
            <>
              <p className="px-2 mt-4 mb-2 text-[10px] font-semibold text-gray-700 uppercase tracking-widest">
                Counters & POS
              </p>
              <ul className="space-y-0.5" role="list">
                {visibleItems.filter(i => COUNTER_PERMS.has(i.permission ?? '')).map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.to === '/'}
                      onClick={() => setSidebarOpen(false)}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                          isActive
                            ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20'
                            : 'text-gray-500 hover:text-gray-200 hover:bg-gray-800/60 border border-transparent',
                        )
                      }
                    >
                      {item.icon}
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </>
          )}

          {/* Phase 5 — Menu section */}
          {visibleItems.some(i => MENU_PERMS.has(i.permission ?? '')) && (
            <>
              <p className="px-2 mt-4 mb-2 text-[10px] font-semibold text-gray-700 uppercase tracking-widest">
                Menu
              </p>
              <ul className="space-y-0.5" role="list">
                {visibleItems.filter(i => MENU_PERMS.has(i.permission ?? '')).map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.to === '/menu'}
                      onClick={() => setSidebarOpen(false)}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                          isActive
                            ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20'
                            : 'text-gray-500 hover:text-gray-200 hover:bg-gray-800/60 border border-transparent',
                        )
                      }
                    >
                      {item.icon}
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </>
          )}

          {/* Phase 6 — Tables & Orders section */}
          {visibleItems.some(i => ORDER_PERMS.has(i.permission ?? '')) && (
            <>
              <p className="px-2 mt-4 mb-2 text-[10px] font-semibold text-gray-700 uppercase tracking-widest">
                Tables & Orders
              </p>
              <ul className="space-y-0.5" role="list">
                {visibleItems.filter(i => ORDER_PERMS.has(i.permission ?? '')).map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.to === '/tables' || item.to === '/orders'}
                      onClick={() => setSidebarOpen(false)}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                          isActive
                            ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20'
                            : 'text-gray-500 hover:text-gray-200 hover:bg-gray-800/60 border border-transparent',
                        )
                      }
                    >
                      {item.icon}
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </>
          )}
        </nav>

        {/* User info + logout */}
        <div className="px-4 py-4 border-t border-gray-800 flex-shrink-0">
          {user && (
            <div className="flex items-center gap-3 mb-3">
              <div className="w-7 h-7 rounded-full bg-gray-700 flex items-center justify-center text-xs font-semibold text-gray-300 flex-shrink-0">
                {(user.first_name?.[0] ?? user.email[0]).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-gray-200 truncate">{user.full_name}</p>
                <p className="text-[10px] text-gray-600 truncate">{primaryRole}</p>
              </div>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 rounded-lg px-3 py-2 text-xs text-gray-500 hover:text-red-400 hover:bg-red-500/5 border border-transparent transition-colors"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Sign out
          </button>
          <p className="text-[10px] text-gray-800 mt-2">
            RestaurantFlow &copy; {new Date().getFullYear()}
          </p>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="sticky top-0 z-30 h-14 flex items-center gap-4 px-4 sm:px-6 bg-gray-900/80 backdrop-blur-sm border-b border-gray-800 flex-shrink-0">
          <button
            className="lg:hidden p-1.5 rounded-md text-gray-500 hover:text-gray-200 hover:bg-gray-800 transition-colors"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation menu"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          <div className="flex-1" />

          {/* User info in header (desktop) */}
          {user && (
            <div className="hidden sm:flex items-center gap-2">
              <span className="text-xs text-gray-600">{user.email}</span>
              <span className="text-gray-700">·</span>
              <span className="text-xs text-gray-600 font-mono">Phase 6</span>
            </div>
          )}
        </header>

        <main className="flex-1 overflow-y-auto" id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
