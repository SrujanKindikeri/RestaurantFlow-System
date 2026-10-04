// =============================================================================
// RestaurantFlow — Application Routes
// Phase 7: Kitchen Display System added
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

// Phase 5 — Menu
import { MenuDashboard } from '@/pages/menu/MenuDashboard'
import { Categories } from '@/pages/menu/Categories'
import { MenuItems } from '@/pages/menu/MenuItems'
import { Pricing } from '@/pages/menu/Pricing'
import { Availability } from '@/pages/menu/Availability'
import { TaxRates } from '@/pages/menu/TaxRates'

// Phase 6 — Tables + Orders + POS
import { TablesDashboard } from '@/pages/tables/TablesDashboard'
import { OrderListPage } from '@/pages/orders/OrderListPage'
import { OrderDetailPage } from '@/pages/orders/OrderDetailPage'
import { POSOrderScreen } from '@/pages/orders/POSOrderScreen'

// Phase 7 — Kitchen Display System
import { KitchenDashboard } from '@/pages/kitchen/KitchenDashboard'
import { KitchenHistory } from '@/pages/kitchen/KitchenHistory'

// Phase 8 — Billing
import { BillingDashboard } from '@/pages/billing/BillingDashboard'
import { BillListPage } from '@/pages/billing/BillListPage'
import { BillDetailPage } from '@/pages/billing/BillDetailPage'
import { BillReceiptPage } from '@/pages/billing/BillReceiptPage'
import { BillCorrectionsPage } from '@/pages/billing/BillCorrectionsPage'

// Phase 9 — Payments
import { PaymentHistoryPage } from '@/pages/payments/PaymentHistoryPage'

// Phase 10 — Inventory & Stock Management
import { InventoryDashboard } from '@/pages/inventory/InventoryDashboard'
import { InventoryItemsPage } from '@/pages/inventory/InventoryItemsPage'
import { StockOverviewPage } from '@/pages/inventory/StockOverviewPage'
import { SuppliersPage } from '@/pages/inventory/SuppliersPage'
import { PurchasesPage } from '@/pages/inventory/PurchasesPage'
import { TransfersPage } from '@/pages/inventory/TransfersPage'
import { WastagePage } from '@/pages/inventory/WastagePage'
import { AdjustmentsPage } from '@/pages/inventory/AdjustmentsPage'
import { StockHistoryPage } from '@/pages/inventory/StockHistoryPage'

// Phase 11 — Recipes & Consumption
import { RecipesPage } from '@/pages/recipes/RecipesPage'
import { RecipeDetailPage } from '@/pages/recipes/RecipeDetailPage'
import { CreateRecipePage } from '@/pages/recipes/CreateRecipePage'
import { ConsumptionHistoryPage } from '@/pages/inventory/ConsumptionHistoryPage'

// Phase 15 — Central Control Center
import { CentralControlDashboard } from '@/pages/central-control/CentralControlDashboard'
import { AlertCenterPage } from '@/pages/central-control/AlertCenterPage'
import { IssueCenterPage } from '@/pages/central-control/IssueCenterPage'
import { RestaurantHealthPage } from '@/pages/central-control/RestaurantHealthPage'
import { SystemHealthPage } from '@/pages/central-control/SystemHealthPage'
import { EventTimelinePage } from '@/pages/central-control/EventTimelinePage'

// Phase 16 — Notifications
import { NotificationCenter } from '@/pages/notifications/NotificationCenter'
import { NotificationPreferences } from '@/pages/notifications/NotificationPreferences'

// Phase 14 — Reporting & Analytics
import { ReportingDashboard } from '@/pages/reports/ReportingDashboard'
import { SalesReportPage } from '@/pages/reports/SalesReportPage'
import { MenuReportPage } from '@/pages/reports/MenuReportPage'
import { PaymentsReportPage } from '@/pages/reports/PaymentsReportPage'
import { KitchenReportPage } from '@/pages/reports/KitchenReportPage'
import { InventoryReportPage } from '@/pages/reports/InventoryReportPage'
import { ExpensesReportPage } from '@/pages/reports/ExpensesReportPage'
import { BranchesReportPage } from '@/pages/reports/BranchesReportPage'

// Phase 13 — Accounting
import { AccountingDashboard } from '@/pages/accounting/AccountingDashboard'
import { ChartOfAccountsPage } from '@/pages/accounting/ChartOfAccountsPage'
import { JournalEntriesPage } from '@/pages/accounting/JournalEntriesPage'
import { GeneralLedgerPage } from '@/pages/accounting/GeneralLedgerPage'
import { TrialBalancePage } from '@/pages/accounting/TrialBalancePage'
import { ProfitLossPage } from '@/pages/accounting/ProfitLossPage'
import { BalanceSheetPage } from '@/pages/accounting/BalanceSheetPage'
import { AccountingPeriodsPage } from '@/pages/accounting/AccountingPeriodsPage'

// Phase 12 — Financial Operations
import { FinancialDashboard } from '@/pages/financials/FinancialDashboard'
import { ExpensesPage } from '@/pages/financials/ExpensesPage'
import { ExpenseDetailPage } from '@/pages/financials/ExpenseDetailPage'
import { CreateExpensePage } from '@/pages/financials/CreateExpensePage'
import { ExpenseCategoriesPage } from '@/pages/financials/ExpenseCategoriesPage'
import { SupplierInvoicesPage } from '@/pages/financials/SupplierInvoicesPage'
import { PayablesPage } from '@/pages/financials/PayablesPage'

function App() {
  return (
    <Routes>
      {/* ------------------------------------------------------------------ */}
      {/* Public routes (no auth required)                                    */}
      {/* ------------------------------------------------------------------ */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* ------------------------------------------------------------------ */}
      {/* POS route — full-screen, bypasses MainLayout sidebar                */}
      {/* ------------------------------------------------------------------ */}
      <Route element={<ProtectedRoute />}>
        <Route path="/pos" element={<POSOrderScreen />} />
      </Route>

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

          {/* Phase 5 — Menu */}
          <Route path="/menu" element={<MenuDashboard />} />
          <Route path="/menu/categories" element={<Categories />} />
          <Route path="/menu/items" element={<MenuItems />} />
          <Route path="/menu/pricing" element={<Pricing />} />
          <Route path="/menu/availability" element={<Availability />} />
          <Route path="/menu/tax-rates" element={<TaxRates />} />

          {/* Phase 6 — Tables */}
          <Route path="/tables" element={<TablesDashboard />} />

          {/* Phase 6 — Orders */}
          <Route path="/orders" element={<OrderListPage />} />
          <Route path="/orders/:id" element={<OrderDetailPage />} />
          <Route path="/orders/new" element={<POSOrderScreen />} />

          {/* Phase 7 — Kitchen Display System */}
          <Route path="/kitchen" element={<KitchenDashboard />} />
          <Route path="/kitchen/history" element={<KitchenHistory />} />

          {/* Phase 8 — Billing */}
          <Route path="/billing" element={<BillingDashboard />} />
          <Route path="/billing/bills" element={<BillListPage />} />
          <Route path="/billing/bills/:id" element={<BillDetailPage />} />
          <Route path="/billing/bills/:id/receipt" element={<BillReceiptPage />} />
          <Route path="/billing/corrections" element={<BillCorrectionsPage />} />

          {/* Phase 9 — Payments */}
          <Route path="/payments" element={<PaymentHistoryPage />} />

          {/* Phase 10 — Inventory & Stock Management */}
          <Route path="/inventory" element={<InventoryDashboard />} />
          <Route path="/inventory/items" element={<InventoryItemsPage />} />
          <Route path="/inventory/stock" element={<StockOverviewPage />} />
          <Route path="/inventory/suppliers" element={<SuppliersPage />} />
          <Route path="/inventory/purchases" element={<PurchasesPage />} />
          <Route path="/inventory/transfers" element={<TransfersPage />} />
          <Route path="/inventory/wastage" element={<WastagePage />} />
          <Route path="/inventory/adjustments" element={<AdjustmentsPage />} />
          <Route path="/inventory/movements" element={<StockHistoryPage />} />

          {/* Phase 11 — Recipes & Consumption */}
          <Route path="/recipes" element={<RecipesPage />} />
          <Route path="/recipes/new" element={<CreateRecipePage />} />
          <Route path="/recipes/:id" element={<RecipeDetailPage />} />
          <Route path="/inventory/consumption" element={<ConsumptionHistoryPage />} />

          {/* Phase 12 — Financial Operations */}
          <Route path="/financials" element={<FinancialDashboard />} />
          <Route path="/financials/expenses" element={<ExpensesPage />} />
          <Route path="/financials/expenses/new" element={<CreateExpensePage />} />
          <Route path="/financials/expenses/:id" element={<ExpenseDetailPage />} />
          <Route path="/financials/categories" element={<ExpenseCategoriesPage />} />
          <Route path="/financials/supplier-invoices" element={<SupplierInvoicesPage />} />
          <Route path="/financials/payables" element={<PayablesPage />} />

          {/* Phase 13 — Accounting */}
          <Route path="/accounting" element={<AccountingDashboard />} />
          <Route path="/accounting/accounts" element={<ChartOfAccountsPage />} />
          <Route path="/accounting/journals" element={<JournalEntriesPage />} />
          <Route path="/accounting/general-ledger" element={<GeneralLedgerPage />} />
          <Route path="/accounting/trial-balance" element={<TrialBalancePage />} />
          <Route path="/accounting/profit-loss" element={<ProfitLossPage />} />
          <Route path="/accounting/balance-sheet" element={<BalanceSheetPage />} />
          <Route path="/accounting/periods" element={<AccountingPeriodsPage />} />

          {/* Phase 14 — Reporting & Analytics */}
          <Route path="/reports" element={<ReportingDashboard />} />
          <Route path="/reports/sales" element={<SalesReportPage />} />
          <Route path="/reports/menu" element={<MenuReportPage />} />
          <Route path="/reports/payments" element={<PaymentsReportPage />} />
          <Route path="/reports/kitchen" element={<KitchenReportPage />} />
          <Route path="/reports/inventory" element={<InventoryReportPage />} />
          <Route path="/reports/expenses" element={<ExpensesReportPage />} />
          <Route path="/reports/branches" element={<BranchesReportPage />} />

          {/* Phase 15 — Central Control Center */}
          <Route path="/central-control" element={<CentralControlDashboard />} />
          <Route path="/central-control/alerts" element={<AlertCenterPage />} />
          <Route path="/central-control/issues" element={<IssueCenterPage />} />
          <Route path="/central-control/restaurants/health" element={<RestaurantHealthPage />} />
          <Route path="/central-control/system-health" element={<SystemHealthPage />} />
          <Route path="/central-control/events" element={<EventTimelinePage />} />

          {/* Phase 16 — Notifications */}
          <Route path="/notifications" element={<NotificationCenter />} />
          <Route path="/settings/notifications" element={<NotificationPreferences />} />
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
