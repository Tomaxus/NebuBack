from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from devconfsite.comun.paginacion import OrdenamientoEstable
from devconfsite.comun.permisos import EsAdmin
from devconfsite.comun.texto import filtrar_por_palabras

from ..models import Pedido
from ..serializers.admin import (
    CambiarEstadoSerializer,
    DashboardSerializer,
    ListaPedidosAdminSerializer,
    PedidoAdminSerializer,
)
from ..servicios.dashboard import construir_dashboard
from ..servicios.pedidos import cambiar_estado_pedido, conteo_por_estado, resumen_pedidos

DIAS_VALIDOS = {"7": 7, "30": 30, "90": 90}


def pedidos_filtrados_por_rango(params):
    pedidos = Pedido.objects.all()
    dias = DIAS_VALIDOS.get(params.get("days", ""))
    if dias:
        pedidos = pedidos.filter(created_at__gte=timezone.now() - timedelta(days=dias))
    cliente = params.get("customer", "")
    if cliente.isdigit():
        pedidos = pedidos.filter(customer_id=int(cliente))
    return pedidos


@extend_schema(
    tags=["Admin · Pedidos"],
    summary="Listar pedidos (admin)",
    description=(
        "Lista paginada (10 por página) con dos objetos extra: summary (sobre todo el conjunto filtrado) "
        "y statusCounts (solo con days y customer aplicados)."
    ),
    parameters=[
        OpenApiParameter("search", OpenApiTypes.STR, description="Palabras contra número, nombre y email del cliente y nombres de productos."),
        OpenApiParameter("status", OpenApiTypes.STR, enum=Pedido.Status.values),
        OpenApiParameter("days", OpenApiTypes.INT, enum=[7, 30, 90], description="Pedidos de los últimos N días. Sin parámetro: todos."),
        OpenApiParameter("customer", OpenApiTypes.INT, description="Id del cliente (historial)."),
        OpenApiParameter(
            "ordering",
            OpenApiTypes.STR,
            enum=[v for c in ["number", "created_at", "customer_name", "units", "total", "status"] for v in (c, f"-{c}")],
            description="Por defecto -created_at.",
        ),
    ],
    responses=ListaPedidosAdminSerializer,
)
class PedidoAdminListView(generics.ListAPIView):
    permission_classes = [EsAdmin]
    serializer_class = PedidoAdminSerializer
    filter_backends = [OrdenamientoEstable]
    ordering_fields = ["number", "created_at", "customer_name", "units", "total", "status"]
    ordering_aliases = {"number": "id", "units": "units_total"}
    ordering = ["-created_at"]

    def filtrados(self):
        pedidos = pedidos_filtrados_por_rango(self.request.query_params)
        estado = self.request.query_params.get("status")
        if estado:
            pedidos = pedidos.filter(status=estado)
        buscar = self.request.query_params.get("search")
        if buscar:
            ids = filtrar_por_palabras(
                Pedido.objects.all(), buscar, ["number", "customer_name", "customer_email", "lines__name"]
            ).values("pk")
            pedidos = pedidos.filter(pk__in=ids)
        return pedidos

    def get_queryset(self):
        return self.filtrados().annotate(units_total=Sum("lines__quantity")).prefetch_related("lines")

    def list(self, request, *args, **kwargs):
        pagina = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        respuesta = self.get_paginated_response(self.get_serializer(pagina, many=True).data)
        datos = respuesta.data
        respuesta.data = {
            "count": datos["count"],
            "next": datos["next"],
            "previous": datos["previous"],
            "summary": resumen_pedidos(self.filtrados()),
            "status_counts": conteo_por_estado(pedidos_filtrados_por_rango(request.query_params)),
            "results": datos["results"],
        }
        return respuesta


@extend_schema_view(
    get=extend_schema(summary="Ver pedido (admin)"),
    patch=extend_schema(
        summary="Cambiar estado del pedido",
        description="Pasar a cancelled o refunded devuelve el stock; salir de esos estados lo vuelve a descontar.",
        request=CambiarEstadoSerializer,
        responses=PedidoAdminSerializer,
    ),
)
@extend_schema(tags=["Admin · Pedidos"])
class PedidoAdminDetailView(generics.RetrieveAPIView):
    permission_classes = [EsAdmin]
    serializer_class = PedidoAdminSerializer
    queryset = Pedido.objects.prefetch_related("lines")
    http_method_names = ["get", "patch", "head", "options"]

    def patch(self, request, pk):
        pedido = self.get_object()
        serializer = CambiarEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cambiar_estado_pedido(pedido, serializer.validated_data["status"])
        return Response(PedidoAdminSerializer(self.get_queryset().get(pk=pedido.pk)).data)


@extend_schema(
    tags=["Admin · Dashboard"],
    summary="Métricas del dashboard",
    description="Período de N días que termina hoy (zona America/Bogota) comparado con los N días anteriores.",
    parameters=[OpenApiParameter("days", OpenApiTypes.INT, enum=[7, 30, 90], description="Por defecto 30.")],
    responses=DashboardSerializer,
)
class DashboardView(APIView):
    permission_classes = [EsAdmin]

    def get(self, request):
        dias = DIAS_VALIDOS.get(request.query_params.get("days", ""), 30)
        return Response(DashboardSerializer(construir_dashboard(dias)).data)
