// =============================================================================
// RestaurantFlow — Restaurant Create / Edit Form
// =============================================================================

import { useState } from 'react'
import type { Restaurant, RestaurantCreatePayload } from '@/types'
import { Input, Textarea } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'

interface RestaurantFormProps {
  initial?: Partial<Restaurant>
  onSubmit: (data: RestaurantCreatePayload) => Promise<void>
  onCancel: () => void
  submitLabel?: string
}

interface FormErrors {
  name?: string
  code?: string
  email?: string
  [key: string]: string | undefined
}

export function RestaurantForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel = 'Save',
}: RestaurantFormProps) {
  const [fields, setFields] = useState({
    name: initial?.name ?? '',
    code: initial?.code ?? '',
    description: initial?.description ?? '',
    email: initial?.email ?? '',
    phone: initial?.phone ?? '',
    address: initial?.address ?? '',
    city: initial?.city ?? '',
    state: initial?.state ?? '',
    country: initial?.country ?? '',
    postal_code: initial?.postal_code ?? '',
  })
  const [errors, setErrors] = useState<FormErrors>({})
  const [loading, setLoading] = useState(false)

  function set(key: string, value: string) {
    setFields((f) => ({ ...f, [key]: value }))
    if (errors[key]) setErrors((e) => ({ ...e, [key]: undefined }))
  }

  function validate(): boolean {
    const newErrors: FormErrors = {}
    if (!fields.name.trim()) newErrors.name = 'Restaurant name is required.'
    if (!fields.code.trim()) newErrors.code = 'Restaurant code is required.'
    else if (!/^[A-Z0-9-]+$/i.test(fields.code.trim()))
      newErrors.code = 'Code must contain only letters, numbers, and hyphens.'
    if (fields.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fields.email))
      newErrors.email = 'Enter a valid email address.'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    try {
      await onSubmit({ ...fields, code: fields.code.toUpperCase() })
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Restaurant Name *"
            value={fields.name}
            onChange={(e) => set('name', e.target.value)}
            placeholder="Spice Garden"
            error={errors.name}
          />
          <Input
            label="Restaurant Code *"
            value={fields.code}
            onChange={(e) => set('code', e.target.value.toUpperCase())}
            placeholder="SPICE-001"
            error={errors.code}
            hint="Unique identifier within your organization"
          />
        </div>

        <Textarea
          label="Description"
          value={fields.description}
          onChange={(e) => set('description', e.target.value)}
          placeholder="Brief description of the restaurant..."
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Email"
            type="email"
            value={fields.email}
            onChange={(e) => set('email', e.target.value)}
            placeholder="restaurant@company.com"
            error={errors.email}
          />
          <Input
            label="Phone"
            type="tel"
            value={fields.phone}
            onChange={(e) => set('phone', e.target.value)}
            placeholder="+91 9000000000"
          />
        </div>

        <Textarea
          label="Address"
          value={fields.address}
          onChange={(e) => set('address', e.target.value)}
          placeholder="Restaurant address..."
        />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Input
            label="City"
            value={fields.city}
            onChange={(e) => set('city', e.target.value)}
          />
          <Input
            label="State"
            value={fields.state}
            onChange={(e) => set('state', e.target.value)}
          />
          <Input
            label="Country"
            value={fields.country}
            onChange={(e) => set('country', e.target.value)}
          />
          <Input
            label="Postal Code"
            value={fields.postal_code}
            onChange={(e) => set('postal_code', e.target.value)}
          />
        </div>
      </div>

      <div className="mt-6 flex justify-end gap-3">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={loading}>
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}
