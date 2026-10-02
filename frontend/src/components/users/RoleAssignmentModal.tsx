// =============================================================================
// RestaurantFlow — Role Assignment Modal
// Phase 3
//
// Cascading dropdowns: Role → Organization → Restaurant → Branch
// Backend validates hierarchy; this UI guides the user.
// =============================================================================

import { useState, useEffect } from 'react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Input'
import { useAssignRole } from '@/hooks/useUsers'
import { useRoles } from '@/hooks/useRoles'
import { useToast } from '@/components/ui/Toast'
import { listOrganizations } from '@/services/organizations'
import type { Organization, Restaurant, Branch, Role } from '@/types'
import api from '@/services/api'

interface Props {
  userId: number
  open: boolean
  onClose: () => void
}

interface FormState {
  role_id: string
  organization_id: string
  restaurant_id: string
  branch_id: string
}

export function RoleAssignmentModal({ userId, open, onClose }: Props) {
  const { toast } = useToast()
  const assignRole = useAssignRole(userId)
  const { data: rolesData, isLoading: rolesLoading } = useRoles()

  const [form, setForm] = useState<FormState>({
    role_id: '',
    organization_id: '',
    restaurant_id: '',
    branch_id: '',
  })
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({})

  // Dependent data
  const [orgs, setOrgs] = useState<Organization[]>([])
  const [restaurants, setRestaurants] = useState<Restaurant[]>([])
  const [branches, setBranches] = useState<Branch[]>([])
  const [loading, setLoading] = useState(false)

  const selectedRole: Role | undefined = rolesData?.results.find((r) => r.id === form.role_id)

  // Load orgs when modal opens
  useEffect(() => {
    if (!open) return
    listOrganizations()
      .then((r) => setOrgs(r.results))
      .catch(() => setOrgs([]))
  }, [open])

  // Load restaurants when org changes
  useEffect(() => {
    if (!form.organization_id) {
      setRestaurants([])
      setForm((f) => ({ ...f, restaurant_id: '', branch_id: '' }))
      return
    }
    api
      .get<{ results: Restaurant[] }>(`/organizations/${form.organization_id}/restaurants/`)
      .then((r) => setRestaurants(r.data.results))
      .catch(() => setRestaurants([]))
  }, [form.organization_id])

  // Load branches when restaurant changes
  useEffect(() => {
    if (!form.restaurant_id) {
      setBranches([])
      setForm((f) => ({ ...f, branch_id: '' }))
      return
    }
    api
      .get<{ results: Branch[] }>(`/restaurants/${form.restaurant_id}/branches/`)
      .then((r) => setBranches(r.data.results))
      .catch(() => setBranches([]))
  }, [form.restaurant_id])

  function resetForm() {
    setForm({ role_id: '', organization_id: '', restaurant_id: '', branch_id: '' })
    setErrors({})
  }

  function handleClose() {
    resetForm()
    onClose()
  }

  function validate(): boolean {
    if (!form.role_id) {
      setErrors({ role_id: 'Please select a role.' })
      return false
    }
    if (!form.organization_id) {
      setErrors({ organization_id: 'Please select an organization.' })
      return false
    }
    if (selectedRole?.scope === 'restaurant' && !form.restaurant_id) {
      setErrors({ restaurant_id: 'Please select a restaurant for this role.' })
      return false
    }
    setErrors({})
    return true
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!validate()) return

    setLoading(true)
    try {
      await assignRole.mutateAsync({
        role: form.role_id,
        organization: form.organization_id || null,
        restaurant: form.restaurant_id || null,
        branch: form.branch_id || null,
      })
      toast('Role assigned successfully.', 'success')
      handleClose()
    } catch (err: unknown) {
      const data = (err as { response?: { data?: { message?: string; details?: Record<string, string[]> } } })
        ?.response?.data
      if (data?.details) {
        const fieldErrors: Partial<Record<keyof FormState, string>> = {}
        for (const [key, msgs] of Object.entries(data.details)) {
          const mapped = key === 'role' ? 'role_id'
            : key === 'organization' ? 'organization_id'
            : key === 'restaurant' ? 'restaurant_id'
            : key === 'branch' ? 'branch_id'
            : (key as keyof FormState)
          ;(fieldErrors as Record<string, string>)[mapped] = Array.isArray(msgs) ? msgs[0] : String(msgs)
        }
        setErrors(fieldErrors)
      } else {
        toast(data?.message ?? 'Assignment failed.', 'error')
      }
    } finally {
      setLoading(false)
    }
  }

  const roleOptions = [
    { value: '', label: '— Select role —' },
    ...(rolesData?.results.filter((r) => r.is_active).map((r) => ({
      value: r.id,
      label: `${r.name} (${r.scope})`,
    })) ?? []),
  ]

  const orgOptions = [
    { value: '', label: '— Select organization —' },
    ...orgs.map((o) => ({ value: o.id, label: o.name })),
  ]

  const restaurantOptions = [
    { value: '', label: '— Select restaurant —' },
    ...restaurants.map((r) => ({ value: r.id, label: r.name })),
  ]

  const branchOptions = [
    { value: '', label: '— Select branch (optional) —' },
    ...branches.map((b) => ({ value: b.id, label: b.name })),
  ]

  const needsRestaurant = selectedRole?.scope === 'restaurant' || selectedRole?.scope === 'branch'
  const needsBranch = selectedRole?.scope === 'branch'

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Assign Role"
      description="Select a role and set its access scope."
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {/* Role */}
        <Select
          label="Role"
          options={roleOptions}
          value={form.role_id}
          onChange={(e) => setForm((f) => ({ ...f, role_id: e.target.value }))}
          error={errors.role_id}
          disabled={rolesLoading || loading}
        />

        {/* Organization — always required */}
        <Select
          label="Organization"
          options={orgOptions}
          value={form.organization_id}
          onChange={(e) => setForm((f) => ({ ...f, organization_id: e.target.value }))}
          error={errors.organization_id}
          disabled={loading}
        />

        {/* Restaurant — required for restaurant/branch-scoped roles */}
        {needsRestaurant && (
          <Select
            label={`Restaurant${selectedRole?.scope === 'restaurant' ? ' *' : ''}`}
            options={restaurantOptions}
            value={form.restaurant_id}
            onChange={(e) => setForm((f) => ({ ...f, restaurant_id: e.target.value }))}
            error={errors.restaurant_id}
            disabled={!form.organization_id || loading}
          />
        )}

        {/* Branch — optional for branch-scoped roles */}
        {needsBranch && (
          <Select
            label="Branch (optional)"
            options={branchOptions}
            value={form.branch_id}
            onChange={(e) => setForm((f) => ({ ...f, branch_id: e.target.value }))}
            error={errors.branch_id}
            disabled={!form.restaurant_id || loading}
          />
        )}

        {/* Role scope hint */}
        {selectedRole && (
          <p className="text-xs text-gray-600">
            Scope: <span className="text-gray-400 font-medium">{selectedRole.scope}</span>
            {' '}— {selectedRole.description || selectedRole.name}
          </p>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="ghost" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={loading}>
            Assign Role
          </Button>
        </div>
      </form>
    </Modal>
  )
}
