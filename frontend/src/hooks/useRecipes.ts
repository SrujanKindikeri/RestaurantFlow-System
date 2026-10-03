// =============================================================================
// RestaurantFlow — Recipe Hooks
// Phase 11
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type {
  Recipe,
  RecipeDetail,
  RecipeCost,
  ConsumptionBatch,
  ConsumptionBatchDetail,
  RecipeListParams,
  ConsumptionListParams,
  CreateRecipePayload,
  UpdateRecipePayload,
  AddRecipeItemPayload,
  UpdateRecipeItemPayload,
  ManualConsumptionPayload,
  ReversalPayload,
  UpdateBranchConsumptionConfigPayload,
  BranchConsumptionConfig,
} from '@/types'
import {
  listRecipes,
  getRecipe,
  createRecipe,
  updateRecipe,
  activateRecipe,
  archiveRecipe,
  getRecipeCost,
  getRecipesByMenuItem,
  addRecipeIngredient,
  updateRecipeIngredient,
  removeRecipeIngredient,
  listConsumptionBatches,
  getConsumptionBatch,
  getConsumptionByOrder,
  manualConsume,
  reverseConsumption,
  getBranchConsumptionConfig,
  updateBranchConsumptionConfig,
} from '@/services/recipes'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const recipeKeys = {
  all: ['recipes'] as const,
  lists: () => [...recipeKeys.all, 'list'] as const,
  list: (params?: RecipeListParams) => [...recipeKeys.lists(), params] as const,
  details: () => [...recipeKeys.all, 'detail'] as const,
  detail: (id: string) => [...recipeKeys.details(), id] as const,
  byMenuItem: (menuItemId: string) => [...recipeKeys.all, 'menu-item', menuItemId] as const,
  cost: (id: string) => [...recipeKeys.all, 'cost', id] as const,
}

export const consumptionKeys = {
  all: ['consumption'] as const,
  lists: () => [...consumptionKeys.all, 'list'] as const,
  list: (params?: ConsumptionListParams) => [...consumptionKeys.lists(), params] as const,
  details: () => [...consumptionKeys.all, 'detail'] as const,
  detail: (id: string) => [...consumptionKeys.details(), id] as const,
  byOrder: (orderId: string) => [...consumptionKeys.all, 'order', orderId] as const,
  config: (branchId: string) => [...consumptionKeys.all, 'config', branchId] as const,
}

// ---------------------------------------------------------------------------
// Recipe hooks
// ---------------------------------------------------------------------------

export function useRecipes(params?: RecipeListParams) {
  return useQuery<Recipe[], Error>({
    queryKey: recipeKeys.list(params),
    queryFn: () => listRecipes(params).then(r => r.data),
  })
}

export function useRecipe(id: string) {
  return useQuery<RecipeDetail, Error>({
    queryKey: recipeKeys.detail(id),
    queryFn: () => getRecipe(id).then(r => r.data),
    enabled: !!id,
  })
}

export function useRecipesByMenuItem(menuItemId: string) {
  return useQuery<Recipe[], Error>({
    queryKey: recipeKeys.byMenuItem(menuItemId),
    queryFn: () => getRecipesByMenuItem(menuItemId).then(r => r.data),
    enabled: !!menuItemId,
  })
}

export function useRecipeCost(id: string, enabled = true) {
  return useQuery<RecipeCost, Error>({
    queryKey: recipeKeys.cost(id),
    queryFn: () => getRecipeCost(id).then(r => r.data),
    enabled: !!id && enabled,
  })
}

export function useCreateRecipe() {
  const qc = useQueryClient()
  return useMutation<RecipeDetail, Error, CreateRecipePayload>({
    mutationFn: (data) => createRecipe(data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: recipeKeys.lists() }),
  })
}

export function useUpdateRecipe(id: string) {
  const qc = useQueryClient()
  return useMutation<RecipeDetail, Error, UpdateRecipePayload>({
    mutationFn: (data) => updateRecipe(id, data).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: recipeKeys.detail(id) })
      qc.invalidateQueries({ queryKey: recipeKeys.lists() })
    },
  })
}

export function useActivateRecipe() {
  const qc = useQueryClient()
  return useMutation<RecipeDetail, Error, string>({
    mutationFn: (id) => activateRecipe(id).then(r => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: recipeKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: recipeKeys.lists() })
      qc.invalidateQueries({ queryKey: recipeKeys.byMenuItem(data.menu_item) })
    },
  })
}

export function useArchiveRecipe() {
  const qc = useQueryClient()
  return useMutation<RecipeDetail, Error, string>({
    mutationFn: (id) => archiveRecipe(id).then(r => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: recipeKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: recipeKeys.lists() })
      qc.invalidateQueries({ queryKey: recipeKeys.byMenuItem(data.menu_item) })
    },
  })
}

export function useAddRecipeIngredient(recipeId: string) {
  const qc = useQueryClient()
  return useMutation<unknown, Error, AddRecipeItemPayload>({
    mutationFn: (data) => addRecipeIngredient(recipeId, data).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: recipeKeys.detail(recipeId) })
    },
  })
}

export function useUpdateRecipeIngredient(recipeId: string, itemId: string) {
  const qc = useQueryClient()
  return useMutation<unknown, Error, UpdateRecipeItemPayload>({
    mutationFn: (data) => updateRecipeIngredient(recipeId, itemId, data).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: recipeKeys.detail(recipeId) })
    },
  })
}

export function useRemoveRecipeIngredient(recipeId: string) {
  const qc = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (itemId) => removeRecipeIngredient(recipeId, itemId).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: recipeKeys.detail(recipeId) })
    },
  })
}

// ---------------------------------------------------------------------------
// Consumption hooks
// ---------------------------------------------------------------------------

export function useConsumptionBatches(params?: ConsumptionListParams) {
  return useQuery<ConsumptionBatch[], Error>({
    queryKey: consumptionKeys.list(params),
    queryFn: () => listConsumptionBatches(params).then(r => r.data),
  })
}

export function useConsumptionBatch(id: string) {
  return useQuery<ConsumptionBatchDetail, Error>({
    queryKey: consumptionKeys.detail(id),
    queryFn: () => getConsumptionBatch(id).then(r => r.data),
    enabled: !!id,
  })
}

export function useConsumptionByOrder(orderId: string) {
  return useQuery<ConsumptionBatchDetail[], Error>({
    queryKey: consumptionKeys.byOrder(orderId),
    queryFn: () => getConsumptionByOrder(orderId).then(r => r.data),
    enabled: !!orderId,
  })
}

export function useManualConsume() {
  const qc = useQueryClient()
  return useMutation<unknown, Error, ManualConsumptionPayload>({
    mutationFn: (data) => manualConsume(data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: consumptionKeys.lists() }),
  })
}

export function useReverseConsumption() {
  const qc = useQueryClient()
  return useMutation<ConsumptionBatchDetail, Error, { id: string; reason?: string }>({
    mutationFn: ({ id, reason }) => reverseConsumption(id, { reason }).then(r => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: consumptionKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: consumptionKeys.lists() })
    },
  })
}

export function useBranchConsumptionConfig(branchId: string) {
  return useQuery<BranchConsumptionConfig, Error>({
    queryKey: consumptionKeys.config(branchId),
    queryFn: () => getBranchConsumptionConfig(branchId).then(r => r.data),
    enabled: !!branchId,
  })
}

export function useUpdateBranchConsumptionConfig() {
  const qc = useQueryClient()
  return useMutation<BranchConsumptionConfig, Error, UpdateBranchConsumptionConfigPayload>({
    mutationFn: (data) => updateBranchConsumptionConfig(data).then(r => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: consumptionKeys.config(data.branch) })
    },
  })
}
