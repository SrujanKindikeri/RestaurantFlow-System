// =============================================================================
// RestaurantFlow — Inventory API Service
// Phase 10
// =============================================================================

import { get, post, patch } from '@/services/api'
import type {
  InventoryCategory,
  InventoryItem,
  StorageLocation,
  StockBalance,
  StockMovement,
  Supplier,
  PurchaseOrder,
  PurchaseOrderSummary,
  PurchaseReceipt,
  StockTransfer,
  StockTransferSummary,
  StockWastage,
  StockAdjustment,
  InventoryDashboard,
  CreateInventoryCategoryPayload,
  CreateInventoryItemPayload,
  CreateStorageLocationPayload,
  CreateSupplierPayload,
  CreatePurchaseOrderPayload,
  ReceivePurchaseOrderPayload,
  CreateStockTransferPayload,
  CreateStockWastagePayload,
  CreateStockAdjustmentPayload,
} from '@/types'

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export const getInventoryDashboard = () =>
  get<InventoryDashboard>('/inventory/dashboard/')

// ---------------------------------------------------------------------------
// Categories
// ---------------------------------------------------------------------------

export const listCategories = (params?: Record<string, string>) =>
  get<InventoryCategory[]>('/inventory/categories/', { params })

export const createCategory = (data: CreateInventoryCategoryPayload) =>
  post<InventoryCategory>('/inventory/categories/', data)

export const getCategory = (id: string) =>
  get<InventoryCategory>(`/inventory/categories/${id}/`)

export const updateCategory = (id: string, data: Partial<CreateInventoryCategoryPayload> & { is_active?: boolean }) =>
  patch<InventoryCategory>(`/inventory/categories/${id}/`, data)

// ---------------------------------------------------------------------------
// Inventory Items
// ---------------------------------------------------------------------------

export const listInventoryItems = (params?: Record<string, string>) =>
  get<InventoryItem[]>('/inventory/items/', { params })

export const createInventoryItem = (data: CreateInventoryItemPayload) =>
  post<InventoryItem>('/inventory/items/', data)

export const getInventoryItem = (id: string) =>
  get<InventoryItem>(`/inventory/items/${id}/`)

export const updateInventoryItem = (id: string, data: Partial<CreateInventoryItemPayload> & { is_active?: boolean }) =>
  patch<InventoryItem>(`/inventory/items/${id}/`, data)

// ---------------------------------------------------------------------------
// Storage Locations
// ---------------------------------------------------------------------------

export const listStorageLocations = (params?: Record<string, string>) =>
  get<StorageLocation[]>('/inventory/locations/', { params })

export const createStorageLocation = (data: CreateStorageLocationPayload) =>
  post<StorageLocation>('/inventory/locations/', data)

export const getStorageLocation = (id: string) =>
  get<StorageLocation>(`/inventory/locations/${id}/`)

export const updateStorageLocation = (id: string, data: Partial<CreateStorageLocationPayload> & { is_active?: boolean }) =>
  patch<StorageLocation>(`/inventory/locations/${id}/`, data)

// ---------------------------------------------------------------------------
// Stock Balances
// ---------------------------------------------------------------------------

export const listStockBalances = (params?: Record<string, string>) =>
  get<StockBalance[]>('/inventory/stock/', { params })

export const getStockBalancesByItem = (itemId: string) =>
  get<StockBalance[]>(`/inventory/stock/${itemId}/`)

// ---------------------------------------------------------------------------
// Stock Movements
// ---------------------------------------------------------------------------

export const listStockMovements = (params?: Record<string, string>) =>
  get<StockMovement[]>('/inventory/movements/', { params })

// ---------------------------------------------------------------------------
// Suppliers
// ---------------------------------------------------------------------------

export const listSuppliers = (params?: Record<string, string>) =>
  get<Supplier[]>('/inventory/suppliers/', { params })

export const createSupplier = (data: CreateSupplierPayload) =>
  post<Supplier>('/inventory/suppliers/', data)

export const getSupplier = (id: string) =>
  get<Supplier>(`/inventory/suppliers/${id}/`)

export const updateSupplier = (id: string, data: Partial<CreateSupplierPayload> & { is_active?: boolean }) =>
  patch<Supplier>(`/inventory/suppliers/${id}/`, data)

// ---------------------------------------------------------------------------
// Purchase Orders
// ---------------------------------------------------------------------------

export const listPurchaseOrders = (params?: Record<string, string>) =>
  get<PurchaseOrderSummary[]>('/inventory/purchases/', { params })

export const createPurchaseOrder = (data: CreatePurchaseOrderPayload) =>
  post<PurchaseOrder>('/inventory/purchases/', data)

export const getPurchaseOrder = (id: string) =>
  get<PurchaseOrder>(`/inventory/purchases/${id}/`)

export const submitPurchaseOrder = (id: string) =>
  post<PurchaseOrder>(`/inventory/purchases/${id}/submit/`)

export const approvePurchaseOrder = (id: string) =>
  post<PurchaseOrder>(`/inventory/purchases/${id}/approve/`)

export const receivePurchaseOrder = (id: string, data: ReceivePurchaseOrderPayload) =>
  post<PurchaseReceipt>(`/inventory/purchases/${id}/receive/`, data)

export const cancelPurchaseOrder = (id: string, reason?: string) =>
  post<PurchaseOrder>(`/inventory/purchases/${id}/cancel/`, { reason })

// ---------------------------------------------------------------------------
// Stock Transfers
// ---------------------------------------------------------------------------

export const listStockTransfers = (params?: Record<string, string>) =>
  get<StockTransferSummary[]>('/inventory/transfers/', { params })

export const createStockTransfer = (data: CreateStockTransferPayload) =>
  post<StockTransfer>('/inventory/transfers/', data)

export const getStockTransfer = (id: string) =>
  get<StockTransfer>(`/inventory/transfers/${id}/`)

export const requestStockTransfer = (id: string) =>
  post<StockTransfer>(`/inventory/transfers/${id}/request/`)

export const approveStockTransfer = (id: string) =>
  post<StockTransfer>(`/inventory/transfers/${id}/approve/`)

export const completeStockTransfer = (id: string) =>
  post<StockTransfer>(`/inventory/transfers/${id}/complete/`)

export const cancelStockTransfer = (id: string) =>
  post<StockTransfer>(`/inventory/transfers/${id}/cancel/`)

// ---------------------------------------------------------------------------
// Wastage
// ---------------------------------------------------------------------------

export const listWastages = (params?: Record<string, string>) =>
  get<StockWastage[]>('/inventory/wastage/', { params })

export const createWastage = (data: CreateStockWastagePayload) =>
  post<StockWastage>('/inventory/wastage/', data)

export const getWastage = (id: string) =>
  get<StockWastage>(`/inventory/wastage/${id}/`)

export const approveWastage = (id: string) =>
  post<StockWastage>(`/inventory/wastage/${id}/approve/`)

export const rejectWastage = (id: string, rejection_reason: string) =>
  post<StockWastage>(`/inventory/wastage/${id}/reject/`, { rejection_reason })

// ---------------------------------------------------------------------------
// Adjustments
// ---------------------------------------------------------------------------

export const listAdjustments = (params?: Record<string, string>) =>
  get<StockAdjustment[]>('/inventory/adjustments/', { params })

export const createAdjustment = (data: CreateStockAdjustmentPayload) =>
  post<StockAdjustment>('/inventory/adjustments/', data)
