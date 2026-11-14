// =============================================================================
// RestaurantFlow — Application Routes
// Phase 7: Kitchen Display System added
// Phase 22: React.lazy route splitting for performance
// =============================================================================

import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/layouts/MainLayout'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { DashboardPage } from '@/pages/DashboardPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

// Phase 3 — Auth (eager — accessed on first visit)
import { LoginPage } from '@/pages/auth/LoginPage'
import { RegisterPage } from '@/pages/auth/RegisterPage'

// Phase 2 — Organizations (lazy)
const OrganizationsListPage = React.lazy(() => import('@/pages/organizations/OrganizationsListPage').then(m => ({ default: m.OrganizationsListPage })))
const OrganizationDetailPage = React.lazy(() => import('@/pages/organizations/OrganizationDetailPage').then(m => ({ default: m.OrganizationDetailPage })))
const RestaurantsListPage = React.lazy(() => import('@/pages/restaurants/RestaurantsListPage').then(m => ({ default: m.RestaurantsListPage })))
const RestaurantDetailPage = React.lazy(() => import('@/pages/restaurants/RestaurantDetailPage').then(m => ({ default: m.RestaurantDetailPage })))
const BranchesListPage = React.lazy(() => import('@/pages/branches/BranchesListPage').then(m => ({ default: m.BranchesListPage })))
const BranchDetailPage = React.lazy(() => import('@/pages/branches/BranchDetailPage').then(m => ({ default: m.BranchDetailPage })))

// Phase 3 — Users + Roles (lazy)
const UsersListPage = React.lazy(() => import('@/pages/users/UsersListPage').then(m => ({ default: m.UsersListPage })))
const UserDetailPage = React.lazy(() => import('@/pages/users/UserDetailPage').then(m => ({ default: m.UserDetailPage })))
const RolesListPage = React.lazy(() => import('@/pages/roles/RolesListPage').then(m => ({ default: m.RolesListPage })))

// Phase 4 — Counters (lazy)
const CountersListPage = React.lazy(() => import('@/pages/counters/CountersListPage').then(m => ({ default: m.CountersListPage })))
const CounterDetailPage = React.lazy(() => import('@/pages/counters/CounterDetailPage').then(m => ({ default: m.CounterDetailPage })))
const CounterSessionsPage = React.lazy(() => import('@/pages/counters/CounterSessionsPage').then(m => ({ default: m.CounterSessionsPage })))
const CounterDashboardPage = React.lazy(() => import('@/pages/counters/CounterDashboardPage').then(m => ({ default: m.CounterDashboardPage })))

// Phase 5 — Menu (lazy)
const MenuDashboard = React.lazy(() => import('@/pages/menu/MenuDashboard').then(m => ({ default: m.MenuDashboard })))
const Categories = React.lazy(() => import('@/pages/menu/Categories').then(m => ({ default: m.Categories })))
const MenuItems = React.lazy(() => import('@/pages/menu/MenuItems').then(m => ({ default: m.MenuItems })))
const Pricing = React.lazy(() => import('@/pages/menu/Pricing').then(m => ({ default: m.Pricing })))
const Availability = React.lazy(() => import('@/pages/menu/Availability').then(m => ({ default: m.Availability })))
const TaxRates = React.lazy(() => import('@/pages/menu/TaxRates').then(m => ({ default: m.TaxRates })))

// Phase 6 — Tables + Orders + POS (lazy)
const TablesDashboard = React.lazy(() => import('@/pages/tables/TablesDashboard').then(m => ({ default: m.TablesDashboard })))
const OrderListPage = React.lazy(() => import('@/pages/orders/OrderListPage').then(m => ({ default: m.OrderListPage })))
const OrderDetailPage = React.lazy(() => import('@/pages/orders/OrderDetailPage').then(m => ({ default: m.OrderDetailPage })))
const POSOrderScreen = React.lazy(() => import('@/pages/orders/POSOrderScreen').then(m => ({ default: m.POSOrderScreen })))

// Phase 7 — Kitchen Display System (lazy)
const KitchenDashboard = React.lazy(() => import('@/pages/kitchen/KitchenDashboard').then(m => ({ default: m.KitchenDashboard })))
const KitchenHistory = React.lazy(() => import('@/pages/kitchen/KitchenHistory').then(m => ({ default: m.KitchenHistory })))

// Phase 8 — Billing (lazy)
const BillingDashboard = React.lazy(() => import('@/pages/billing/BillingDashboard').then(m => ({ default: m.BillingDashboard })))
const BillListPage = React.lazy(() => import('@/pages/billing/BillListPage').then(m => ({ default: m.BillListPage })))
const BillDetailPage = React.lazy(() => import('@/pages/billing/BillDetailPage').then(m => ({ default: m.BillDetailPage })))
const BillReceiptPage = React.lazy(() => import('@/pages/billing/BillReceiptPage').then(m => ({ default: m.BillReceiptPage })))
const BillCorrectionsPage = React.lazy(() => import('@/pages/billing/BillCorrectionsPage').then(m => ({ default: m.BillCorrectionsPage })))

// Phase 9 — Payments (lazy)
const PaymentHistoryPage = React.lazy(() => import('@/pages/payments/PaymentHistoryPage').then(m => ({ default: m.PaymentHistoryPage })))

// Phase 10 — Inventory & Stock Management (lazy)
const InventoryDashboard = React.lazy(() => import('@/pages/inventory/InventoryDashboard').then(m => ({ default: m.InventoryDashboard })))
const InventoryItemsPage = React.lazy(() => import('@/pages/inventory/InventoryItemsPage').then(m => ({ default: m.InventoryItemsPage })))
const StockOverviewPage = React.lazy(() => import('@/pages/inventory/StockOverviewPage').then(m => ({ default: m.StockOverviewPage })))
const SuppliersPage = React.lazy(() => import('@/pages/inventory/SuppliersPage').then(m => ({ default: m.SuppliersPage })))
const PurchasesPage = React.lazy(() => import('@/pages/inventory/PurchasesPage').then(m => ({ default: m.PurchasesPage })))
const TransfersPage = React.lazy(() => import('@/pages/inventory/TransfersPage').then(m => ({ default: m.TransfersPage })))
const WastagePage = React.lazy(() => import('@/pages/inventory/WastagePage').then(m => ({ default: m.WastagePage })))
const AdjustmentsPage = React.lazy(() => import('@/pages/inventory/AdjustmentsPage').then(m => ({ default: m.AdjustmentsPage })))
const StockHistoryPage = React.lazy(() => import('@/pages/inventory/StockHistoryPage').then(m => ({ default: m.StockHistoryPage })))

// Phase 11 — Recipes & Consumption (lazy)
const RecipesPage = React.lazy(() => import('@/pages/recipes/RecipesPage').then(m => ({ default: m.RecipesPage })))
const RecipeDetailPage = React.lazy(() => import('@/pages/recipes/RecipeDetailPage').then(m => ({ default: m.RecipeDetailPage })))
const CreateRecipePage = React.lazy(() => import('@/pages/recipes/CreateRecipePage').then(m => ({ default: m.CreateRecipePage })))
const ConsumptionHistoryPage = React.lazy(() => import('@/pages/inventory/ConsumptionHistoryPage').then(m => ({ default: m.ConsumptionHistoryPage })))

// Phase 15 — Central Control Center (lazy)
const CentralControlDashboard = React.lazy(() => import('@/pages/central-control/CentralControlDashboard').then(m => ({ default: m.CentralControlDashboard })))
const AlertCenterPage = React.lazy(() => import('@/pages/central-control/AlertCenterPage').then(m => ({ default: m.AlertCenterPage })))
const IssueCenterPage = React.lazy(() => import('@/pages/central-control/IssueCenterPage').then(m => ({ default: m.IssueCenterPage })))
const RestaurantHealthPage = React.lazy(() => import('@/pages/central-control/RestaurantHealthPage').then(m => ({ default: m.RestaurantHealthPage })))
const SystemHealthPage = React.lazy(() => import('@/pages/central-control/SystemHealthPage').then(m => ({ default: m.SystemHealthPage })))
const EventTimelinePage = React.lazy(() => import('@/pages/central-control/EventTimelinePage').then(m => ({ default: m.EventTimelinePage })))

// Phase 16 — Notifications (lazy)
const NotificationCenter = React.lazy(() => import('@/pages/notifications/NotificationCenter').then(m => ({ default: m.NotificationCenter })))
const NotificationPreferences = React.lazy(() => import('@/pages/notifications/NotificationPreferences').then(m => ({ default: m.NotificationPreferences })))

// Phase 18 — Marketing, Promotions & Campaigns (lazy)
const MarketingDashboard = React.lazy(() => import('@/pages/marketing/MarketingDashboard').then(m => ({ default: m.MarketingDashboard })))
const CampaignsListPage = React.lazy(() => import('@/pages/marketing/CampaignsListPage').then(m => ({ default: m.CampaignsListPage })))
const CampaignDetailPage = React.lazy(() => import('@/pages/marketing/CampaignDetailPage').then(m => ({ default: m.CampaignDetailPage })))
const PromotionsPage = React.lazy(() => import('@/pages/marketing/PromotionsPage').then(m => ({ default: m.PromotionsPage })))
const MarketingAnalyticsPage = React.lazy(() => import('@/pages/marketing/MarketingAnalyticsPage').then(m => ({ default: m.MarketingAnalyticsPage })))

// Phase 19 — Advanced POS & Restaurant Operations (lazy)
const OperationsDashboard = React.lazy(() => import('@/pages/operations/OperationsDashboard').then(m => ({ default: m.OperationsDashboard })))
const POSPage = React.lazy(() => import('@/pages/operations/POSPage').then(m => ({ default: m.POSPage })))
const TablesPage = React.lazy(() => import('@/pages/operations/TablesPage').then(m => ({ default: m.TablesPage })))
const WaiterPage = React.lazy(() => import('@/pages/operations/WaiterPage').then(m => ({ default: m.WaiterPage })))
const CashierPage = React.lazy(() => import('@/pages/operations/CashierPage').then(m => ({ default: m.CashierPage })))
const ShiftsPage = React.lazy(() => import('@/pages/operations/ShiftsPage').then(m => ({ default: m.ShiftsPage })))
const ShiftDetailPage = React.lazy(() => import('@/pages/operations/ShiftDetailPage').then(m => ({ default: m.ShiftDetailPage })))

// Phase 20 — Multi-Branch Enterprise Operations & Configuration (lazy)
const EnterpriseDashboard = React.lazy(() => import('@/pages/enterprise/EnterpriseDashboard').then(m => ({ default: m.EnterpriseDashboard })))
const EnterpriseBranchesPage = React.lazy(() => import('@/pages/enterprise/EnterpriseBranchesPage').then(m => ({ default: m.EnterpriseBranchesPage })))
const EnterpriseBranchDetailPage = React.lazy(() => import('@/pages/enterprise/EnterpriseBranchDetailPage').then(m => ({ default: m.EnterpriseBranchDetailPage })))
const EnterpriseConfigurationPage = React.lazy(() => import('@/pages/enterprise/EnterpriseConfigurationPage').then(m => ({ default: m.EnterpriseConfigurationPage })))
const EnterpriseRolloutsPage = React.lazy(() => import('@/pages/enterprise/EnterpriseRolloutsPage').then(m => ({ default: m.EnterpriseRolloutsPage })))
const EnterpriseStaffPage = React.lazy(() => import('@/pages/enterprise/EnterpriseStaffPage').then(m => ({ default: m.EnterpriseStaffPage })))
const EnterpriseApprovalPoliciesPage = React.lazy(() => import('@/pages/enterprise/EnterpriseApprovalPoliciesPage').then(m => ({ default: m.EnterpriseApprovalPoliciesPage })))
const EnterpriseAuditPage = React.lazy(() => import('@/pages/enterprise/EnterpriseAuditPage').then(m => ({ default: m.EnterpriseAuditPage })))

// Phase 17 — CRM, Loyalty & Feedback (lazy)
const CustomerListPage = React.lazy(() => import('@/pages/crm/CustomerListPage').then(m => ({ default: m.CustomerListPage })))
const CustomerDetailPage = React.lazy(() => import('@/pages/crm/CustomerDetailPage').then(m => ({ default: m.CustomerDetailPage })))
const CRMDashboard = React.lazy(() => import('@/pages/crm/CRMDashboard').then(m => ({ default: m.CRMDashboard })))
const CRMSegmentsPage = React.lazy(() => import('@/pages/crm/CRMSegmentsPage').then(m => ({ default: m.CRMSegmentsPage })))
const CRMRewardsPage = React.lazy(() => import('@/pages/crm/CRMRewardsPage').then(m => ({ default: m.CRMRewardsPage })))
const CRMLoyaltyPage = React.lazy(() => import('@/pages/crm/CRMLoyaltyPage').then(m => ({ default: m.CRMLoyaltyPage })))
const CRMFeedbackPage = React.lazy(() => import('@/pages/crm/CRMFeedbackPage').then(m => ({ default: m.CRMFeedbackPage })))

// Phase 14 — Reporting & Analytics (lazy)
const ReportingDashboard = React.lazy(() => import('@/pages/reports/ReportingDashboard').then(m => ({ default: m.ReportingDashboard })))
const SalesReportPage = React.lazy(() => import('@/pages/reports/SalesReportPage').then(m => ({ default: m.SalesReportPage })))
const MenuReportPage = React.lazy(() => import('@/pages/reports/MenuReportPage').then(m => ({ default: m.MenuReportPage })))
const PaymentsReportPage = React.lazy(() => import('@/pages/reports/PaymentsReportPage').then(m => ({ default: m.PaymentsReportPage })))
const KitchenReportPage = React.lazy(() => import('@/pages/reports/KitchenReportPage').then(m => ({ default: m.KitchenReportPage })))
const InventoryReportPage = React.lazy(() => import('@/pages/reports/InventoryReportPage').then(m => ({ default: m.InventoryReportPage })))
const ExpensesReportPage = React.lazy(() => import('@/pages/reports/ExpensesReportPage').then(m => ({ default: m.ExpensesReportPage })))
const BranchesReportPage = React.lazy(() => import('@/pages/reports/BranchesReportPage').then(m => ({ default: m.BranchesReportPage })))

// Phase 13 — Accounting (lazy)
const AccountingDashboard = React.lazy(() => import('@/pages/accounting/AccountingDashboard').then(m => ({ default: m.AccountingDashboard })))
const ChartOfAccountsPage = React.lazy(() => import('@/pages/accounting/ChartOfAccountsPage').then(m => ({ default: m.ChartOfAccountsPage })))
const JournalEntriesPage = React.lazy(() => import('@/pages/accounting/JournalEntriesPage').then(m => ({ default: m.JournalEntriesPage })))
const GeneralLedgerPage = React.lazy(() => import('@/pages/accounting/GeneralLedgerPage').then(m => ({ default: m.GeneralLedgerPage })))
const TrialBalancePage = React.lazy(() => import('@/pages/accounting/TrialBalancePage').then(m => ({ default: m.TrialBalancePage })))
const ProfitLossPage = React.lazy(() => import('@/pages/accounting/ProfitLossPage').then(m => ({ default: m.ProfitLossPage })))
const BalanceSheetPage = React.lazy(() => import('@/pages/accounting/BalanceSheetPage').then(m => ({ default: m.BalanceSheetPage })))
const AccountingPeriodsPage = React.lazy(() => import('@/pages/accounting/AccountingPeriodsPage').then(m => ({ default: m.AccountingPeriodsPage })))

// Phase 12 — Financial Operations (lazy)
const FinancialDashboard = React.lazy(() => import('@/pages/financials/FinancialDashboard').then(m => ({ default: m.FinancialDashboard })))
const ExpensesPage = React.lazy(() => import('@/pages/financials/ExpensesPage').then(m => ({ default: m.ExpensesPage })))
const ExpenseDetailPage = React.lazy(() => import('@/pages/financials/ExpenseDetailPage').then(m => ({ default: m.ExpenseDetailPage })))
const CreateExpensePage = React.lazy(() => import('@/pages/financials/CreateExpensePage').then(m => ({ default: m.CreateExpensePage })))
const ExpenseCategoriesPage = React.lazy(() => import('@/pages/financials/ExpenseCategoriesPage').then(m => ({ default: m.ExpenseCategoriesPage })))
const SupplierInvoicesPage = React.lazy(() => import('@/pages/financials/SupplierInvoicesPage').then(m => ({ default: m.SupplierInvoicesPage })))
const PayablesPage = React.lazy(() => import('@/pages/financials/PayablesPage').then(m => ({ default: m.PayablesPage })))

function RouteLoadingSkeleton() {
  return (
    <div className="flex items-center justify-center h-screen bg-gray-950">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" aria-hidden="true" />
        <div className="space-y-2">
          <div className="h-2 w-32 rounded bg-gray-800 animate-pulse" />
          <div className="h-2 w-24 rounded bg-gray-800 animate-pulse mx-auto" />
        </div>
      </div>
    </div>
  )
}

function App() {
  return (
    <React.Suspense fallback={<RouteLoadingSkeleton />}>
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

            {/* Phase 17 — CRM */}
            <Route path="/crm" element={<CRMDashboard />} />
            <Route path="/customers" element={<CustomerListPage />} />
            <Route path="/customers/:id" element={<CustomerDetailPage />} />
            <Route path="/crm/segments" element={<CRMSegmentsPage />} />
            <Route path="/crm/rewards" element={<CRMRewardsPage />} />
            <Route path="/crm/loyalty" element={<CRMLoyaltyPage />} />
            <Route path="/crm/feedback" element={<CRMFeedbackPage />} />

            {/* Phase 18 — Marketing, Promotions & Campaigns */}
            <Route path="/marketing" element={<MarketingDashboard />} />
            <Route path="/marketing/campaigns" element={<CampaignsListPage />} />
            <Route path="/marketing/campaigns/new" element={<CampaignsListPage />} />
            <Route path="/marketing/campaigns/:id" element={<CampaignDetailPage />} />
            <Route path="/marketing/promotions" element={<PromotionsPage />} />
            <Route path="/marketing/promotions/new" element={<PromotionsPage />} />
            <Route path="/marketing/analytics" element={<MarketingAnalyticsPage />} />
            {/* Phase 19 — Operations */}
            <Route path="/operations" element={<OperationsDashboard />} />
            <Route path="/operations/pos" element={<POSPage />} />
            <Route path="/operations/tables" element={<TablesPage />} />
            <Route path="/operations/waiter" element={<WaiterPage />} />
            <Route path="/operations/cashier" element={<CashierPage />} />
            <Route path="/operations/shifts" element={<ShiftsPage />} />
            <Route path="/operations/shifts/:id" element={<ShiftDetailPage />} />

            {/* Phase 20 — Enterprise Operations */}
            <Route path="/enterprise" element={<EnterpriseDashboard />} />
            <Route path="/enterprise/branches" element={<EnterpriseBranchesPage />} />
            <Route path="/enterprise/branches/:id" element={<EnterpriseBranchDetailPage />} />
            <Route path="/enterprise/configuration" element={<EnterpriseConfigurationPage />} />
            <Route path="/enterprise/rollouts" element={<EnterpriseRolloutsPage />} />
            <Route path="/enterprise/staff" element={<EnterpriseStaffPage />} />
            <Route path="/enterprise/approval-policies" element={<EnterpriseApprovalPoliciesPage />} />
            <Route path="/enterprise/audit" element={<EnterpriseAuditPage />} />
          </Route>
        </Route>

        {/* ------------------------------------------------------------------ */}
        {/* Fallback                                                             */}
        {/* ------------------------------------------------------------------ */}
        <Route path="/404" element={<NotFoundPage />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </React.Suspense>
  )
}

export default App
