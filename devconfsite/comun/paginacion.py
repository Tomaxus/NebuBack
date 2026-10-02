from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination


class Paginacion(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class OrdenamientoEstable(OrderingFilter):
    def get_ordering(self, request, queryset, view):
        orden = super().get_ordering(request, queryset, view) or []
        alias = getattr(view, "ordering_aliases", {})
        traducido = []
        for campo in orden:
            signo = "-" if campo.startswith("-") else ""
            traducido.append(signo + alias.get(campo.lstrip("-"), campo.lstrip("-")))
        return traducido

    def filter_queryset(self, request, queryset, view):
        queryset = super().filter_queryset(request, queryset, view)
        orden = list(queryset.query.order_by or queryset.model._meta.ordering)
        if "id" not in orden and "-id" not in orden:
            queryset = queryset.order_by(*orden, "id")
        return queryset


def orden_param(valores, defecto):
    return OpenApiParameter(
        "ordering",
        OpenApiTypes.STR,
        enum=[v for campo in valores for v in (campo, f"-{campo}")],
        description=f"Orden de la lista. Por defecto {defecto}.",
    )
