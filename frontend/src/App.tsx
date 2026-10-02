// =============================================================================
// RestaurantFlow — Application Routes
// Phase 2: Organizations / Restaurants / Branches
// =============================================================================

import { Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/layouts/MainLayout'
import { DashboardPage } from '@/pages/DashboardPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

// Phase 2 pages
import { OrganizationsListPage } from '@/pages/organizations/OrganizationsListPage'
import { OrganizationDetailPage } from '@/pages/organizations/OrganizationDetailPage'
import { RestaurantsListPage } from '@/pages/restaurants/RestaurantsListPage'
import { RestaurantDetailPage } from '@/pages/restaurants/RestaurantDetailPage'
import { BranchesListPage } from '@/pages/branches/BranchesListPage'
import { BranchDetailPage } from '@/pages/branches/BranchDetailPage'

function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        {/* Dashboard */}
        <Route path="/" element={<DashboardPage />} />

        {/* Organizations */}
        <Route path="/organizations" element={<OrganizationsListPage />} />
        <Route path="/organizations/:id" element={<OrganizationDetailPage />} />

        {/* Restaurants */}
        <Route path="/restaurants" element={<RestaurantsListPage />} />
        <Route path="/restaurants/:id" element={<RestaurantDetailPage />} />

        {/* Branches */}
        <Route path="/branches" element={<BranchesListPage />} />
        <Route path="/branches/:id" element={<BranchDetailPage />} />
      </Route>

      <Route path="/404" element={<NotFoundPage />} />
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  )
}

export default App
