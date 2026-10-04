# =============================================================================
# RestaurantFlow — Reporting Exceptions
# Phase 14
# =============================================================================

from rest_framework.exceptions import APIException
from rest_framework import status


class ReportingException(APIException):
    """Base exception for all reporting errors."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A reporting error occurred."
    default_code = "reporting_error"


class InvalidDateRangeError(ReportingException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid date range. date_from must be before or equal to date_to."
    default_code = "invalid_date_range"


class InvalidFilterError(ReportingException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "One or more report filters are invalid."
    default_code = "invalid_filter"


class ReportScopeError(ReportingException):
    """Raised when the user requests data outside their authorized scope."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have access to the requested report scope."
    default_code = "report_scope_denied"


class ExportPermissionError(ReportingException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to export this report."
    default_code = "export_permission_denied"


class ExportGenerationError(ReportingException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Export generation failed. Please try again."
    default_code = "export_generation_error"


class DateRangeTooLargeError(ReportingException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Date range is too large. Please narrow your date range."
    default_code = "date_range_too_large"
