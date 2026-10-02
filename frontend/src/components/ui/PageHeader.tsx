// =============================================================================
// RestaurantFlow — Page Header
// =============================================================================

import { Breadcrumbs, type Crumb } from '@/components/ui/Breadcrumbs'

interface PageHeaderProps {
  title: string
  description?: string
  crumbs?: Crumb[]
  actions?: React.ReactNode
}

export function PageHeader({ title, description, crumbs, actions }: PageHeaderProps) {
  return (
    <div className="mb-8">
      {crumbs && crumbs.length > 0 && (
        <Breadcrumbs crumbs={crumbs} className="mb-3" />
      )}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-white">{title}</h1>
          {description && (
            <p className="mt-1 text-sm text-gray-500">{description}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </div>
    </div>
  )
}
