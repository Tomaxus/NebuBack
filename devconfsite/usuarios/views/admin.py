from django.db.models import Count, DecimalField, Max, Q, Sum, Value
from django.db.models.functions import Coalesce
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics

from devconfsite.comun.excepciones import ReglaDeNegocio
from devconfsite.comun.paginacion import OrdenamientoEstable
from devconfsite.comun.permisos import EsAdmin
from devconfsite.comun.texto import filtrar_por_palabras

from ..models import Usuario
from ..serializers import AdminSerializer, ClienteAdminSerializer


def clientes_con_estadisticas():
    from devconfsite.carrito.models import Pedido

    ingresos = Q(pedidos__status__in=Pedido.REVENUE_STATUSES)
    return Usuario.objects.filter(role=Usuario.Role.CLIENTE).annotate(
        orders_count=Count("pedidos", distinct=True),
        total_spent=Coalesce(
            Sum("pedidos__total", filter=ingresos), Value(0), output_field=DecimalField(max_digits=12, decimal_places=2)
        ),
        last_order_at=Max("pedidos__created_at"),
    )


class VistaAdmin:
    permission_classes = [EsAdmin]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]


@extend_schema_view(
    get=extend_schema(
        summary="Listar clientes",
        description="Solo usuarios con rol cliente, con ordersCount, totalSpent y lastOrderAt calculados. 10 por página.",
        parameters=[
            OpenApiParameter("search", OpenApiTypes.STR, description="Palabras contra nombre y email."),
            OpenApiParameter(
                "ordering",
                OpenApiTypes.STR,
                enum=[v for c in ["name", "status", "orders_count", "total_spent", "last_order_at", "created_at"] for v in (c, f"-{c}")],
                description="Por defecto -created_at.",
            ),
        ],
    ),
    post=extend_schema(summary="Crear cliente", description="Se crea sin contraseña. Cuando esa persona se registre con el mismo email, reclama la cuenta."),
)
@extend_schema(tags=["Admin · Clientes"])
class ClienteAdminListView(VistaAdmin, generics.ListCreateAPIView):
    serializer_class = ClienteAdminSerializer
    filterset_fields = ["status"]
    ordering_fields = ["name", "status", "orders_count", "total_spent", "last_order_at", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        clientes = clientes_con_estadisticas()
        buscar = self.request.query_params.get("search")
        if buscar:
            clientes = filtrar_por_palabras(clientes, buscar, ["name", "email"])
        return clientes

    def perform_create(self, serializer):
        serializer.instance = clientes_con_estadisticas().get(pk=serializer.save().pk)


@extend_schema_view(
    get=extend_schema(summary="Ver cliente"),
    patch=extend_schema(summary="Editar o bloquear cliente", description="Actualización parcial de name, email, notes o status."),
    delete=extend_schema(summary="Borrar cliente", description="Sus pedidos se conservan con el nombre y email copiados."),
)
@extend_schema(tags=["Admin · Clientes"])
class ClienteAdminDetailView(VistaAdmin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ClienteAdminSerializer

    def get_queryset(self):
        return clientes_con_estadisticas()

    def perform_update(self, serializer):
        serializer.instance = clientes_con_estadisticas().get(pk=serializer.save().pk)


@extend_schema_view(
    get=extend_schema(
        summary="Listar admins",
        parameters=[OpenApiParameter("ordering", OpenApiTypes.STR, enum=["created_at", "-created_at", "name", "-name"], description="Por defecto -created_at.")],
    ),
    post=extend_schema(summary="Crear admin", description="El admin que hace la petición queda registrado en createdBy."),
)
@extend_schema(tags=["Admin · Admins"])
class AdminListView(VistaAdmin, generics.ListCreateAPIView):
    serializer_class = AdminSerializer
    queryset = Usuario.objects.filter(role=Usuario.Role.ADMIN).select_related("created_by")
    filter_backends = [OrdenamientoEstable]
    ordering_fields = ["created_at", "name"]
    ordering = ["-created_at"]


@extend_schema(
    tags=["Admin · Admins"],
    summary="Borrar admin",
    description="No se puede borrar la propia cuenta ni dejar el sistema sin admins.",
)
class AdminDetailView(VistaAdmin, generics.DestroyAPIView):
    queryset = Usuario.objects.filter(role=Usuario.Role.ADMIN)
    serializer_class = AdminSerializer

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise ReglaDeNegocio("You cannot delete your own account.")
        if not Usuario.objects.filter(role=Usuario.Role.ADMIN).exclude(pk=instance.pk).exists():
            raise ReglaDeNegocio("There must be at least one admin.")
        instance.delete()
