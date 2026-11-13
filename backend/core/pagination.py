import logging

from rest_framework.pagination import PageNumberPagination

logger = logging.getLogger("core")


class SafePageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_page_size(self, request):
        page_size = super().get_page_size(request)
        requested = request.query_params.get(self.page_size_query_param)
        if requested is not None:
            try:
                requested_int = int(requested)
                if requested_int > self.max_page_size:
                    logger.warning(
                        "Client requested page_size=%d which exceeds max_page_size=%d; "
                        "clamping to max.",
                        requested_int,
                        self.max_page_size,
                    )
            except (ValueError, TypeError):
                pass
        return page_size
