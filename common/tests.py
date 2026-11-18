from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from common.pagination import DynamicPageNumberPagination


class DynamicPageNumberPaginationTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.paginator = DynamicPageNumberPagination()
        self.queryset = list(range(30))

    def _request(self, path):
        # El paginador espera un Request de DRF (con .query_params), no el
        # WSGIRequest plano que devuelve directamente APIRequestFactory.get().
        return Request(self.factory.get(path))

    def test_sin_query_param_pagina_normalmente(self):
        page = self.paginator.paginate_queryset(self.queryset, self._request('/algo/'))
        self.assertIsNotNone(page)
        self.assertLess(len(page), len(self.queryset))

    def test_pagination_false_desactiva_la_paginacion(self):
        page = self.paginator.paginate_queryset(self.queryset, self._request('/algo/?pagination=false'))
        self.assertIsNone(page)

    def test_pagination_0_tambien_desactiva(self):
        page = self.paginator.paginate_queryset(self.queryset, self._request('/algo/?pagination=0'))
        self.assertIsNone(page)

    def test_pagination_no_tambien_desactiva(self):
        page = self.paginator.paginate_queryset(self.queryset, self._request('/algo/?pagination=no'))
        self.assertIsNone(page)

    def test_pagination_true_no_desactiva(self):
        page = self.paginator.paginate_queryset(self.queryset, self._request('/algo/?pagination=true'))
        self.assertIsNotNone(page)

    def test_valor_no_reconocido_pagina_normalmente(self):
        page = self.paginator.paginate_queryset(self.queryset, self._request('/algo/?pagination=algo-random'))
        self.assertIsNotNone(page)
