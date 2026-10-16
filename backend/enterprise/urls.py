# =============================================================================
# RestaurantFlow — Enterprise URLs
# Phase 20
#
# All endpoints mounted under /api/enterprise/ via config/urls.py.
# =============================================================================

from django.urls import path

from enterprise import views

app_name = "enterprise"

urlpatterns = [
    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------
    path(
        "enterprise/dashboard/",
        views.EnterpriseDashboardView.as_view(),
        name="dashboard",
    ),

    # -------------------------------------------------------------------------
    # Branch lifecycle
    # -------------------------------------------------------------------------
    path(
        "enterprise/branches/",
        views.BranchListView.as_view(),
        name="branch-list",
    ),
    path(
        "enterprise/branches/<uuid:pk>/",
        views.BranchDetailView.as_view(),
        name="branch-detail",
    ),
    path(
        "enterprise/branches/<uuid:pk>/status/",
        views.BranchSetStatusView.as_view(),
        name="branch-set-status",
    ),
    path(
        "enterprise/branches/<uuid:pk>/open/",
        views.BranchOpenView.as_view(),
        name="branch-open",
    ),
    path(
        "enterprise/branches/<uuid:pk>/close/",
        views.BranchCloseView.as_view(),
        name="branch-close",
    ),
    path(
        "enterprise/branches/<uuid:pk>/reopen/",
        views.BranchReopenView.as_view(),
        name="branch-reopen",
    ),
    path(
        "enterprise/branches/<uuid:pk>/opening-checklist/",
        views.BranchOpeningChecklistView.as_view(),
        name="branch-opening-checklist",
    ),

    # -------------------------------------------------------------------------
    # Operating schedules
    # -------------------------------------------------------------------------
    path(
        "enterprise/schedules/",
        views.ScheduleListView.as_view(),
        name="schedule-list",
    ),
    path(
        "enterprise/schedules/bulk/",
        views.ScheduleBulkView.as_view(),
        name="schedule-bulk",
    ),

    # -------------------------------------------------------------------------
    # Branch closures
    # -------------------------------------------------------------------------
    path(
        "enterprise/closures/",
        views.ClosureListCreateView.as_view(),
        name="closure-list-create",
    ),
    path(
        "enterprise/closures/<uuid:pk>/",
        views.ClosureDetailView.as_view(),
        name="closure-detail",
    ),
    path(
        "enterprise/closures/<uuid:pk>/approve/",
        views.ClosureApproveView.as_view(),
        name="closure-approve",
    ),
    path(
        "enterprise/closures/<uuid:pk>/reject/",
        views.ClosureRejectView.as_view(),
        name="closure-reject",
    ),
    path(
        "enterprise/closures/<uuid:pk>/cancel/",
        views.ClosureCancelView.as_view(),
        name="closure-cancel",
    ),

    # -------------------------------------------------------------------------
    # Configuration — order matters: specific paths before {id}
    # -------------------------------------------------------------------------
    path(
        "enterprise/configuration/",
        views.ConfigurationListCreateView.as_view(),
        name="configuration-list-create",
    ),
    path(
        "enterprise/configuration/bulk/",
        views.ConfigurationBulkView.as_view(),
        name="configuration-bulk",
    ),
    path(
        "enterprise/configuration/effective/",
        views.ConfigurationEffectiveView.as_view(),
        name="configuration-effective",
    ),
    path(
        "enterprise/configuration/history/",
        views.ConfigurationHistoryView.as_view(),
        name="configuration-history",
    ),
    path(
        "enterprise/configuration/<uuid:pk>/",
        views.ConfigurationDetailView.as_view(),
        name="configuration-detail",
    ),
    path(
        "enterprise/configuration/<uuid:pk>/rollback/",
        views.ConfigurationRollbackView.as_view(),
        name="configuration-rollback",
    ),

    # -------------------------------------------------------------------------
    # Menu / Price rollouts
    # -------------------------------------------------------------------------
    path(
        "enterprise/rollouts/",
        views.RolloutListCreateView.as_view(),
        name="rollout-list-create",
    ),
    path(
        "enterprise/rollouts/<uuid:pk>/",
        views.RolloutDetailView.as_view(),
        name="rollout-detail",
    ),
    path(
        "enterprise/rollouts/<uuid:pk>/preview/",
        views.RolloutPreviewView.as_view(),
        name="rollout-preview",
    ),
    path(
        "enterprise/rollouts/<uuid:pk>/approve/",
        views.RolloutApproveView.as_view(),
        name="rollout-approve",
    ),
    path(
        "enterprise/rollouts/<uuid:pk>/execute/",
        views.RolloutExecuteView.as_view(),
        name="rollout-execute",
    ),
    path(
        "enterprise/rollouts/<uuid:pk>/cancel/",
        views.RolloutCancelView.as_view(),
        name="rollout-cancel",
    ),

    # -------------------------------------------------------------------------
    # Staff assignments + transfers
    # -------------------------------------------------------------------------
    path(
        "enterprise/staff/",
        views.StaffOverviewView.as_view(),
        name="staff-overview",
    ),
    path(
        "enterprise/staff/assignments/",
        views.StaffAssignmentListView.as_view(),
        name="staff-assignment-list",
    ),
    path(
        "enterprise/staff/assign/",
        views.StaffAssignView.as_view(),
        name="staff-assign",
    ),
    path(
        "enterprise/staff/transfers/",
        views.StaffTransferListCreateView.as_view(),
        name="staff-transfer-list-create",
    ),
    path(
        "enterprise/staff/transfers/<uuid:pk>/",
        views.StaffTransferDetailView.as_view(),
        name="staff-transfer-detail",
    ),
    path(
        "enterprise/staff/transfers/<uuid:pk>/approve/",
        views.StaffTransferApproveView.as_view(),
        name="staff-transfer-approve",
    ),
    path(
        "enterprise/staff/transfers/<uuid:pk>/reject/",
        views.StaffTransferRejectView.as_view(),
        name="staff-transfer-reject",
    ),
    path(
        "enterprise/staff/transfers/<uuid:pk>/complete/",
        views.StaffTransferCompleteView.as_view(),
        name="staff-transfer-complete",
    ),
    path(
        "enterprise/staff/transfers/<uuid:pk>/cancel/",
        views.StaffTransferCancelView.as_view(),
        name="staff-transfer-cancel",
    ),

    # -------------------------------------------------------------------------
    # Approval policies
    # -------------------------------------------------------------------------
    path(
        "enterprise/approval-policies/",
        views.ApprovalPolicyListCreateView.as_view(),
        name="approval-policy-list-create",
    ),
    path(
        "enterprise/approval-policies/<uuid:pk>/",
        views.ApprovalPolicyDetailView.as_view(),
        name="approval-policy-detail",
    ),

    # -------------------------------------------------------------------------
    # Audit log
    # -------------------------------------------------------------------------
    path(
        "enterprise/audit/",
        views.AuditLogListView.as_view(),
        name="audit-list",
    ),
]
