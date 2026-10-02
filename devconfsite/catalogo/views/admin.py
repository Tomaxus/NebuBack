from django.db.models import Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics

from devconfsite.comun.excepciones import ReglaDeNegocio
from devconfsite.comun.paginacion import orden_param
from devconfsite.comun.permisos import EsAdmin
from devconfsite.comun.texto import filtrar_por_palabras

from ..filters import ProductoAdminFilter
from ..models import Categoria, Producto
from ..serializers import CategoriaAdminSerializer, ProductoSerializer


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
