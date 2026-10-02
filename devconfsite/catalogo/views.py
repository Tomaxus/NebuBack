from django.db.models import Count
from django.http import Http404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny

from devconfsite.comun import EsAdmin, Paginacion, ReglaDeNegocio, filtrar_por_palabras

from .filters import ProductoAdminFilter, ProductoFilter
from .models import Categoria, Producto
from .serializers import CategoriaAdminSerializer, CategoriaSerializer, ProductoSerializer


class PaginacionCatalogo(Paginacion):
    page_size = 9


class VistaPublica:
    permission_classes = [AllowAny]
    authentication_classes = []


def orden_param(valores, defecto):
    return OpenApiParameter(
        "ordering",
        OpenApiTypes.STR,
        enum=[v for campo in valores for v in (campo, f"-{campo}")],
        description=f"Orden de la lista. Por defecto {defecto}.",
    )


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


@extend_schema_view(
    get=extend_schema(
        summary="Listar productos (admin)",
        description="Todos los productos, visibles y desactivados. 10 por página.",
        parameters=[orden_param(["name", "status", "slug", "category", "price", "stock", "updated_at"], "-updated_at")],
    ),
    post=extend_schema(summary="Crear producto", description="Si slug viene vacío se genera desde el nombre."),
)
@extend_schema(tags=["Admin · Productos"])
class ProductoAdminListView(generics.ListCreateAPIView):
    permission_classes = [EsAdmin]
    queryset = Producto.objects.select_related("category").prefetch_related("variants")
    serializer_class = ProductoSerializer
    filterset_class = ProductoAdminFilter
    ordering_fields = ["name", "status", "slug", "category", "price", "stock", "updated_at"]
    ordering_aliases = {"category": "category__name"}
    ordering = ["-updated_at"]


@extend_schema_view(
    get=extend_schema(summary="Ver producto (admin)"),
    patch=extend_schema(summary="Editar producto", description="Actualización parcial: solo se cambian los campos enviados."),
    delete=extend_schema(summary="Borrar producto", description="Borrado definitivo. Los pedidos ya hechos conservan su copia del producto."),
)
@extend_schema(tags=["Admin · Productos"])
class ProductoAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [EsAdmin]
    queryset = Producto.objects.select_related("category").prefetch_related("variants")
    serializer_class = ProductoSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]


def categorias_con_conteo():
    return Categoria.objects.annotate(products_count=Count("productos"))


@extend_schema_view(
    get=extend_schema(
        summary="Listar categorías (admin)",
        description="Todas las categorías con productsCount (cuántos productos tiene cada una). 10 por página.",
        parameters=[
            OpenApiParameter("search", OpenApiTypes.STR, description="Palabras contra nombre y slug."),
            orden_param(["id", "name", "products_count"], "id"),
        ],
    ),
    post=extend_schema(summary="Crear categoría", description="Si slug viene vacío se genera desde el nombre. El nombre no se puede repetir."),
)
@extend_schema(tags=["Admin · Categorías"])
class CategoriaAdminListView(generics.ListCreateAPIView):
    permission_classes = [EsAdmin]
    serializer_class = CategoriaAdminSerializer
    ordering_fields = ["id", "name", "products_count"]
    ordering = ["id"]

    def get_queryset(self):
        categorias = categorias_con_conteo()
        buscar = self.request.query_params.get("search")
        if buscar:
            categorias = filtrar_por_palabras(categorias, buscar, ["name", "slug"])
        return categorias

    def perform_create(self, serializer):
        serializer.instance = categorias_con_conteo().get(pk=serializer.save().pk)


@extend_schema_view(
    get=extend_schema(summary="Ver categoría"),
    patch=extend_schema(
        summary="Editar categoría",
        description="Actualización parcial de name o slug. Los productos de la categoría quedan con el nombre nuevo.",
    ),
    delete=extend_schema(
        summary="Borrar categoría",
        description="Solo se puede borrar si no tiene productos; si tiene, responde 400 con detail.",
    ),
)
@extend_schema(tags=["Admin · Categorías"])
class CategoriaAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [EsAdmin]
    serializer_class = CategoriaAdminSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return categorias_con_conteo()

    def perform_update(self, serializer):
        serializer.instance = categorias_con_conteo().get(pk=serializer.save().pk)

    def perform_destroy(self, instance):
        if instance.productos.exists():
            raise ReglaDeNegocio("This category has products. Move them to another category or delete them first.")
        instance.delete()
