// =============================================================================
// RestaurantFlow — Recipes API Service
// Phase 11
// =============================================================================

import { get, post, patch, del } from '@/services/api'
import type {
  Recipe,
  RecipeDetail,
  RecipeCost,
  RecipeItem,
  ConsumptionBatch,
  ConsumptionBatchDetail,
  StockConsumption,
  BranchConsumptionConfig,
  CreateRecipePayload,
  UpdateRecipePayload,
  AddRecipeItemPayload,
  UpdateRecipeItemPayload,
  ManualConsumptionPayload,
  ReversalPayload,
  UpdateBranchConsumptionConfigPayload,
  RecipeListParams,
  ConsumptionListParams,
} from '@/types'

// ---------------------------------------------------------------------------
// Recipes
// ---------------------------------------------------------------------------

export const listRecipes = (params?: RecipeListParams) =>
  get<Recipe[]>('/recipes/', { params })

export const getRecipe = (id: string) =>
  get<RecipeDetail>(`/recipes/${id}/`)

export const createRecipe = (data: CreateRecipePayload) =>
  post<RecipeDetail>('/recipes/', data)

export const updateRecipe = (id: string, data: UpdateRecipePayload) =>
  patch<RecipeDetail>(`/recipes/${id}/`, data)

export const activateRecipe = (id: string) =>
  post<RecipeDetail>(`/recipes/${id}/activate/`)

export const archiveRecipe = (id: string) =>
  post<RecipeDetail>(`/recipes/${id}/archive/`)

export const getRecipeCost = (id: string) =>
  get<RecipeCost>(`/recipes/${id}/cost/`)

export const getRecipesByMenuItem = (menuItemId: string) =>
  get<Recipe[]>(`/recipes/menu-item/${menuItemId}/`)

// ---------------------------------------------------------------------------
// Recipe Ingredients
// ---------------------------------------------------------------------------

export const listRecipeIngredients = (recipeId: string) =>
  get<RecipeItem[]>(`/recipes/${recipeId}/ingredients/`)

export const addRecipeIngredient = (recipeId: string, data: AddRecipeItemPayload) =>
  post<RecipeItem>(`/recipes/${recipeId}/ingredients/`, data)

export const updateRecipeIngredient = (recipeId: string, itemId: string, data: UpdateRecipeItemPayload) =>
  patch<RecipeItem>(`/recipes/${recipeId}/ingredients/${itemId}/`, data)

export const removeRecipeIngredient = (recipeId: string, itemId: string) =>
  del<void>(`/recipes/${recipeId}/ingredients/${itemId}/`)

// ---------------------------------------------------------------------------
// Consumption Batches
// ---------------------------------------------------------------------------

export const listConsumptionBatches = (params?: ConsumptionListParams) =>
  get<ConsumptionBatch[]>('/consumption/', { params })

export const getConsumptionBatch = (id: string) =>
  get<ConsumptionBatchDetail>(`/consumption/${id}/`)

export const getConsumptionByOrder = (orderId: string) =>
  get<ConsumptionBatchDetail[]>(`/consumption/order/${orderId}/`)

export const manualConsume = (data: ManualConsumptionPayload) =>
  post<StockConsumption>('/consumption/manual/', data)

export const reverseConsumption = (batchId: string, data?: ReversalPayload) =>
  post<ConsumptionBatchDetail>(`/consumption/${batchId}/reverse/`, data ?? {})

// ---------------------------------------------------------------------------
// Branch Consumption Config
// ---------------------------------------------------------------------------

export const getBranchConsumptionConfig = (branchId: string) =>
  get<BranchConsumptionConfig>(`/consumption/config/${branchId}/`)

export const updateBranchConsumptionConfig = (data: UpdateBranchConsumptionConfigPayload) =>
  patch<BranchConsumptionConfig>('/consumption/config/', data)
