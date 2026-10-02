// =============================================================================
// RestaurantFlow — Application Routes
// Phase 4: Counters + Sessions + Dashboard
// =============================================================================

import { Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/layouts/MainLayout'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { DashboardPage } from '@/pages/DashboardPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

// Phase 3 — Auth
import { LoginPage } from '@/pages/auth/LoginPage'
import { RegisterPage } from '@/pages/auth/RegisterPage'

// Phase 2 — Organizations
import { OrganizationsListPage } from '@/pages/organizations/OrganizationsListPage'
import { OrganizationDetailPage } from '@/pages/organizations/OrganizationDetailPage'
import { RestaurantsListPage } from '@/pages/restaurants/RestaurantsListPage'
import { RestaurantDetailPage } from '@/pages/restaurants/RestaurantDetailPage'
import { BranchesListPage } from '@/pages/branches/BranchesListPage'
import { BranchDetailPage } from '@/pages/branches/BranchDetailPage'

// Phase 3 — Users + Roles
import { UsersListPage } from '@/pages/users/UsersListPage'
import { UserDetailPage } from '@/pages/users/UserDetailPage'
import { RolesListPage } from '@/pages/roles/RolesListPage'

// Phase 4 — Counters
import { CountersListPage } from '@/pages/counters/CountersListPage'
import { CounterDetailPage } from '@/pages/counters/CounterDetailPage'
import { CounterSessionsPage } from '@/pages/counters/CounterSessionsPage'
import { CounterDashboardPage } from '@/pages/counters/CounterDashboardPage'

function App() {
  return (
    <Routes>
      {/* ------------------------------------------------------------------ */}
      {/* Public routes (no auth required)                                    */}
      {/* ------------------------------------------------------------------ */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* ------------------------------------------------------------------ */}
      {/* Protected routes (auth required)                                    */}
      {/* ------------------------------------------------------------------ */}
      <Route element={<ProtectedRoute />}>
        <Route element={<MainLayout />}>
          {/* Dashboard */}
          <Route path="/" element={<DashboardPage />} />

          {/* Phase 2 — Organizations */}
          <Route path="/organizations" element={<OrganizationsListPage />} />
          <Route path="/organizations/:id" element={<OrganizationDetailPage />} />

          {/* Phase 2 — Restaurants */}
          <Route path="/restaurants" element={<RestaurantsListPage />} />
          <Route path="/restaurants/:id" element={<RestaurantDetailPage />} />

          {/* Phase 2 — Branches */}
          <Route path="/branches" element={<BranchesListPage />} />
          <Route path="/branches/:id" element={<BranchDetailPage />} />

          {/* Phase 3 — Users */}
          <Route path="/users" element={<UsersListPage />} />
          <Route path="/users/:id" element={<UserDetailPage />} />

          {/* Phase 3 — Roles */}
          <Route path="/roles" element={<RolesListPage />} />

          {/* Phase 4 — Counters */}
          <Route path="/counters" element={<CountersListPage />} />
          <Route path="/counters/:id" element={<CounterDetailPage />} />
          <Route path="/counter-sessions" element={<CounterSessionsPage />} />
          <Route path="/counter-dashboard" element={<CounterDashboardPage />} />
        </Route>
      </Route>

      {/* ------------------------------------------------------------------ */}
      {/* Fallback                                                             */}
      {/* ------------------------------------------------------------------ */}
      <Route path="/404" element={<NotFoundPage />} />
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  )
}

export default App
