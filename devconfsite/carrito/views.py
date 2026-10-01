from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from devconfsite.comun import EsAdmin, OrdenamientoEstable, filtrar_por_palabras

from . import servicios
from .models import Carrito, Pedido
from .serializers import (
    AgregarItemSerializer,
    CambiarCantidadSerializer,
    CambiarEstadoSerializer,
    CarritoSerializer,
    CheckoutSerializer,
    DashboardSerializer,
    ListaPedidosAdminSerializer,
    PedidoAdminSerializer,
    PedidoSerializer,
)

DIAS_VALIDOS = {"7": 7, "30": 30, "90": 90}


def respuesta_carrito(carrito):
    carrito = Carrito.objects.prefetch_related("items__variant", "items__product").get(pk=carrito.pk)
    return Response(CarritoSerializer(carrito).data)


@extend_schema(
    tags=["Carrito"],
    summary="Ver mi carrito",
    description="Devuelve el carrito activo del usuario con subtotal, impuesto (8 %) y total ya calculados. Si no existe, lo crea vacío.",
    responses=CarritoSerializer,
)
class CarritoView(APIView):
    def get(self, request):
        return respuesta_carrito(servicios.carrito_activo(request.user))


@extend_schema(
    tags=["Carrito"],
    summary="Añadir al carrito",
    description=(
        "Suma 1 unidad del producto con las opciones elegidas. Deben venir todas las opciones del producto. "
        "Mismo producto con las mismas opciones suma a la línea existente. Devuelve el carrito completo."
    ),
    request=AgregarItemSerializer,
    responses=CarritoSerializer,
)
class ItemCarritoCreateView(APIView):
    def post(self, request):
        serializer = AgregarItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        carrito = servicios.agregar_al_carrito(request.user, serializer.validated_data["slug"], serializer.validated_data["options"])
        return respuesta_carrito(carrito)


@extend_schema_view(
    patch=extend_schema(
        summary="Cambiar cantidad",
        description="Recibe la cantidad final. 0 elimina la línea. Devuelve el carrito completo.",
        request=CambiarCantidadSerializer,
        responses=CarritoSerializer,
    ),
    delete=extend_schema(summary="Quitar del carrito", request=None, responses=CarritoSerializer),
)
@extend_schema(tags=["Carrito"])
class ItemCarritoDetailView(APIView):
    def patch(self, request, pk):
        serializer = CambiarCantidadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return respuesta_carrito(servicios.cambiar_cantidad(request.user, pk, serializer.validated_data["quantity"]))

    def delete(self, request, pk):
        return respuesta_carrito(servicios.quitar_del_carrito(request.user, pk))


@extend_schema(
    tags=["Pedidos"],
    summary="Hacer checkout",
    description=(
        "Crea el pedido con los productos del carrito del usuario, descuenta el stock y vacía el carrito. "
        "El pago es simulado: solo se reciben los 4 últimos dígitos de la tarjeta. "
        "Cliente bloqueado: 403. Carrito vacío: 400."
    ),
    request=CheckoutSerializer,
    responses={201: PedidoSerializer},
)
class CheckoutView(APIView):
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pedido = servicios.hacer_checkout(
            request.user, serializer.validated_data["shipping_address"], serializer.validated_data["card_last4"]
        )
        pedido = Pedido.objects.prefetch_related("lines").get(pk=pedido.pk)
        return Response(PedidoSerializer(pedido).data, status=status.HTTP_201_CREATED)


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
            "summary": servicios.resumen_pedidos(self.filtrados()),
            "status_counts": servicios.conteo_por_estado(pedidos_filtrados_por_rango(request.query_params)),
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
        servicios.cambiar_estado_pedido(pedido, serializer.validated_data["status"])
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
        return Response(DashboardSerializer(servicios.construir_dashboard(dias)).data)
