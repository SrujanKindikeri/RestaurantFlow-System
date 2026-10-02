// =============================================================================
// RestaurantFlow — Branch Create / Edit Form
// =============================================================================

import { useState } from 'react'
import type { Branch, BranchCreatePayload } from '@/types'
import { Input, Textarea } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'

interface BranchFormProps {
  initial?: Partial<Branch>
  onSubmit: (data: BranchCreatePayload) => Promise<void>
  onCancel: () => void
  submitLabel?: string
}

interface FormErrors {
  name?: string
  code?: string
  email?: string
  [key: string]: string | undefined
}

export function BranchForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel = 'Save',
}: BranchFormProps) {
  const [fields, setFields] = useState({
    name: initial?.name ?? '',
    code: initial?.code ?? '',
    address: initial?.address ?? '',
    city: initial?.city ?? '',
    state: initial?.state ?? '',
    country: initial?.country ?? '',
    postal_code: initial?.postal_code ?? '',
    phone: initial?.phone ?? '',
    email: initial?.email ?? '',
    latitude: initial?.latitude ?? '',
    longitude: initial?.longitude ?? '',
  })
  const [errors, setErrors] = useState<FormErrors>({})
  const [loading, setLoading] = useState(false)

  function set(key: string, value: string) {
    setFields((f) => ({ ...f, [key]: value }))
    if (errors[key]) setErrors((e) => ({ ...e, [key]: undefined }))
  }

  function validate(): boolean {
    const newErrors: FormErrors = {}
    if (!fields.name.trim()) newErrors.name = 'Branch name is required.'
    if (!fields.code.trim()) newErrors.code = 'Branch code is required.'
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
      const payload: BranchCreatePayload = {
        ...fields,
        code: fields.code.toUpperCase(),
        latitude: fields.latitude || undefined,
        longitude: fields.longitude || undefined,
      }
      await onSubmit(payload)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Branch Name *"
            value={fields.name}
            onChange={(e) => set('name', e.target.value)}
            placeholder="LPU Campus"
            error={errors.name}
          />
          <Input
            label="Branch Code *"
            value={fields.code}
            onChange={(e) => set('code', e.target.value.toUpperCase())}
            placeholder="SG-LPU"
            error={errors.code}
            hint="Unique identifier within the restaurant"
          />
        </div>

        <Textarea
          label="Address"
          value={fields.address}
          onChange={(e) => set('address', e.target.value)}
          placeholder="Branch address..."
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

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Phone"
            type="tel"
            value={fields.phone}
            onChange={(e) => set('phone', e.target.value)}
            placeholder="+91 9000000000"
          />
          <Input
            label="Email"
            type="email"
            value={fields.email}
            onChange={(e) => set('email', e.target.value)}
            placeholder="branch@company.com"
            error={errors.email}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Latitude"
            type="number"
            step="any"
            value={fields.latitude ?? ''}
            onChange={(e) => set('latitude', e.target.value)}
            placeholder="12.9716"
            hint="Optional geolocation"
          />
          <Input
            label="Longitude"
            type="number"
            step="any"
            value={fields.longitude ?? ''}
            onChange={(e) => set('longitude', e.target.value)}
            placeholder="77.5946"
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
