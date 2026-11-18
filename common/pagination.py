from rest_framework.pagination import PageNumberPagination


class DynamicPageNumberPagination(PageNumberPagination):
    """
    Paginación estándar del proyecto, pero desactivable por query param
    cuando el mismo endpoint también se usa como catálogo (ej. llenar un
    <select>) y no se quiere perder datos detrás de otra página.

    Por default pagina igual que siempre (no rompe nada existente). Para
    traer todo de una vez: ?pagination=false (también acepta 0/no).
    """

    def paginate_queryset(self, queryset, request, view=None):
        sin_paginar = request.query_params.get("pagination", "").lower() in ("false", "0", "no")
        if sin_paginar:
            return None
        return super().paginate_queryset(queryset, request, view)
