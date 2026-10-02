// =============================================================================
// RestaurantFlow — Organization Create / Edit Form
// =============================================================================

import { useState } from 'react'
import type { Organization, OrganizationCreatePayload } from '@/types'
import { Input, Textarea, Select } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'

const CURRENCY_OPTIONS = [
  { value: 'INR', label: 'INR — Indian Rupee' },
  { value: 'USD', label: 'USD — US Dollar' },
  { value: 'EUR', label: 'EUR — Euro' },
  { value: 'GBP', label: 'GBP — British Pound' },
  { value: 'AED', label: 'AED — UAE Dirham' },
  { value: 'SGD', label: 'SGD — Singapore Dollar' },
]

const TIMEZONE_OPTIONS = [
  { value: 'Asia/Kolkata', label: 'Asia/Kolkata (IST)' },
  { value: 'UTC', label: 'UTC' },
  { value: 'America/New_York', label: 'America/New_York (EST)' },
  { value: 'America/Los_Angeles', label: 'America/Los_Angeles (PST)' },
  { value: 'Europe/London', label: 'Europe/London (GMT)' },
  { value: 'Asia/Dubai', label: 'Asia/Dubai (GST)' },
  { value: 'Asia/Singapore', label: 'Asia/Singapore (SGT)' },
]

interface OrganizationFormProps {
  initial?: Partial<Organization>
  onSubmit: (data: OrganizationCreatePayload) => Promise<void>
  onCancel: () => void
  submitLabel?: string
}

interface FormErrors {
  name?: string
  email?: string
  [key: string]: string | undefined
}

export function OrganizationForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel = 'Save',
}: OrganizationFormProps) {
  const [fields, setFields] = useState({
    name: initial?.name ?? '',
    legal_name: initial?.legal_name ?? '',
    email: initial?.email ?? '',
    phone: initial?.phone ?? '',
    address: initial?.address ?? '',
    city: initial?.city ?? '',
    state: initial?.state ?? '',
    country: initial?.country ?? 'India',
    postal_code: initial?.postal_code ?? '',
    tax_id: initial?.tax_id ?? '',
    currency: initial?.currency ?? 'INR',
    timezone: initial?.timezone ?? 'Asia/Kolkata',
  })
  const [errors, setErrors] = useState<FormErrors>({})
  const [loading, setLoading] = useState(false)

  function set(key: string, value: string) {
    setFields((f) => ({ ...f, [key]: value }))
    if (errors[key]) setErrors((e) => ({ ...e, [key]: undefined }))
  }

  function validate(): boolean {
    const newErrors: FormErrors = {}
    if (!fields.name.trim()) newErrors.name = 'Organization name is required.'
    if (fields.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fields.email)) {
      newErrors.email = 'Enter a valid email address.'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    try {
      await onSubmit(fields)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="space-y-5">
        {/* Identity */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Organization Name *"
            value={fields.name}
            onChange={(e) => set('name', e.target.value)}
            placeholder="RestaurantFlow Foods"
            error={errors.name}
          />
          <Input
            label="Legal Name"
            value={fields.legal_name}
            onChange={(e) => set('legal_name', e.target.value)}
            placeholder="RestaurantFlow Foods Pvt Ltd"
          />
        </div>

        {/* Contact */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Email"
            type="email"
            value={fields.email}
            onChange={(e) => set('email', e.target.value)}
            placeholder="admin@company.com"
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

        {/* Address */}
        <Textarea
          label="Address"
          value={fields.address}
          onChange={(e) => set('address', e.target.value)}
          placeholder="12 Tech Park, Sector 5"
        />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Input
            label="City"
            value={fields.city}
            onChange={(e) => set('city', e.target.value)}
            placeholder="Bangalore"
          />
          <Input
            label="State"
            value={fields.state}
            onChange={(e) => set('state', e.target.value)}
            placeholder="Karnataka"
          />
          <Input
            label="Country"
            value={fields.country}
            onChange={(e) => set('country', e.target.value)}
            placeholder="India"
          />
          <Input
            label="Postal Code"
            value={fields.postal_code}
            onChange={(e) => set('postal_code', e.target.value)}
            placeholder="560001"
          />
        </div>

        {/* Business */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Input
            label="Tax ID / GST"
            value={fields.tax_id}
            onChange={(e) => set('tax_id', e.target.value)}
            placeholder="29AABCT1332L1ZD"
          />
          <Select
            label="Currency"
            value={fields.currency}
            onChange={(e) => set('currency', e.target.value)}
            options={CURRENCY_OPTIONS}
          />
          <Select
            label="Timezone"
            value={fields.timezone}
            onChange={(e) => set('timezone', e.target.value)}
            options={TIMEZONE_OPTIONS}
          />
        </div>
      </div>

      {/* Footer */}
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
