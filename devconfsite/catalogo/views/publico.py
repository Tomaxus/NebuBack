from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny

from devconfsite.comun.paginacion import Paginacion, orden_param

from ..filters import ProductoFilter
from ..models import Categoria, Producto
from ..serializers import CategoriaSerializer, ProductoSerializer


class PaginacionCatalogo(Paginacion):
    page_size = 9


class VistaPublica:
    permission_classes = [AllowAny]
    authentication_classes = []


@extend_schema(tags=["Catálogo"], summary="Listar categorías", description="Devuelve todas las categorías de la tienda. No está paginado.")
class CategoriaListView(VistaPublica, generics.ListAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    pagination_class = None
    filter_backends = []


@extend_schema(
    tags=["Catálogo"],
    summary="Listar productos",
    description=(
        "Devuelve solo productos visibles (status = live), 9 por página. "
        "Por defecto ordena del más nuevo al más antiguo. "
        "Una página que no existe devuelve 404 con {\"detail\": \"Invalid page.\"}."
    ),
    parameters=[orden_param(["created_at", "price", "name"], "-created_at")],
)
class ProductoListView(VistaPublica, generics.ListAPIView):
    queryset = Producto.objects.filter(status=Producto.Status.LIVE).select_related("category").prefetch_related("variants")
    serializer_class = ProductoSerializer
    pagination_class = PaginacionCatalogo
    filterset_class = ProductoFilter
    ordering_fields = ["created_at", "price", "name"]
    ordering = ["-created_at"]


@extend_schema(
    tags=["Catálogo"],
    summary="Detalle de un producto",
    description="Busca el producto por su slug. Devuelve 404 si no existe o está desactivado.",
)
class ProductoDetailView(VistaPublica, generics.RetrieveAPIView):
    queryset = Producto.objects.filter(status=Producto.Status.LIVE).select_related("category").prefetch_related("variants")
    serializer_class = ProductoSerializer
    lookup_field = "slug"
    filter_backends = []

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise NotFound()
