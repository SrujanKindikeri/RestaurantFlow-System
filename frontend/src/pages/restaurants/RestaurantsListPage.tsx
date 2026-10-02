// =============================================================================
// RestaurantFlow — Restaurants List Page (all restaurants, admin view)
// =============================================================================

import { useState } from 'react'
import type { Restaurant } from '@/types'
import {
  useAllRestaurants,
  useDisableRestaurant,
  useReactivateRestaurant,
} from '@/hooks/useRestaurants'
import { RestaurantCard } from '@/components/restaurant/RestaurantCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { ConfirmDialog } from '@/components/ui/Modal'
import { EmptyState } from '@/components/ui/EmptyState'
import { useToast } from '@/components/ui/Toast'

export function RestaurantsListPage() {
  const { data, isLoading, isError } = useAllRestaurants()
  const disableRestaurant = useDisableRestaurant()
  const reactivateRestaurant = useReactivateRestaurant()
  const { toast } = useToast()

  const [confirm, setConfirm] = useState<{
    r: Restaurant
    action: 'disable' | 'reactivate'
  } | null>(null)

  async function handleConfirm() {
    if (!confirm) return
    const { r, action } = confirm
    try {
      if (action === 'disable') {
        await disableRestaurant.mutateAsync(r.id)
        toast(`"${r.name}" disabled.`, 'warning')
      } else {
        await reactivateRestaurant.mutateAsync(r.id)
        toast(`"${r.name}" reactivated.`, 'success')
      }
    } catch {
      toast('Action failed. Please try again.', 'error')
    } finally {
      setConfirm(null)
    }
  }

  const restaurants = data?.results ?? []

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title="Restaurants"
        description="All restaurants across all organizations."
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Restaurants' }]}
        actions={
          <a
            href="/organizations"
            className="inline-flex items-center gap-1 rounded-lg border border-gray-700 bg-gray-800 hover:bg-gray-700 px-3 py-1.5 text-xs font-medium text-gray-300 transition-colors"
          >
            Manage by Organization →
          </a>
        }
      />

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="h-24 rounded-xl bg-gray-900/60 border border-gray-800 animate-pulse"
            />
          ))}
        </div>
      )}

      {isError && (
        <div
          className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400"
          role="alert"
        >
          Failed to load restaurants.
        </div>
      )}

      {!isLoading && !isError && restaurants.length === 0 && (
        <EmptyState
          title="No restaurants yet"
          description="Create restaurants from an organization page."
        />
      )}

      {!isLoading && !isError && restaurants.length > 0 && (
        <div className="space-y-3">
          {restaurants.map((r) => (
            <RestaurantCard
              key={r.id}
              restaurant={r}
              onDisable={(restaurant) =>
                setConfirm({ r: restaurant, action: 'disable' })
              }
              onReactivate={(restaurant) =>
                setConfirm({ r: restaurant, action: 'reactivate' })
              }
            />
          ))}
          <p className="text-xs text-gray-700 text-right pt-1">
            {data?.count} restaurant{data?.count !== 1 ? 's' : ''} total
          </p>
        </div>
      )}

      <ConfirmDialog
        open={!!confirm}
        onClose={() => setConfirm(null)}
        onConfirm={handleConfirm}
        title={
          confirm?.action === 'disable'
            ? `Disable "${confirm?.r.name}"?`
            : `Reactivate "${confirm?.r.name}"?`
        }
        message={
          confirm?.action === 'disable'
            ? 'Disabling prevents new branches from being created under this restaurant.'
            : 'This will reactivate the restaurant.'
        }
        confirmLabel={confirm?.action === 'disable' ? 'Disable' : 'Reactivate'}
        confirmVariant={confirm?.action === 'disable' ? 'danger' : 'success'}
        loading={disableRestaurant.isPending || reactivateRestaurant.isPending}
      />
    </div>
  )
}
