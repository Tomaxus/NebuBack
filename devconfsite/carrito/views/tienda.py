from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Carrito, Pedido
from ..serializers.tienda import (
    AgregarItemSerializer,
    CambiarCantidadSerializer,
    CarritoSerializer,
    CheckoutSerializer,
    PedidoSerializer,
)
from ..servicios.carrito import agregar_al_carrito, cambiar_cantidad, carrito_activo, quitar_del_carrito
from ..servicios.pedidos import hacer_checkout


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
        return respuesta_carrito(carrito_activo(request.user))


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
        carrito = agregar_al_carrito(request.user, serializer.validated_data["slug"], serializer.validated_data["options"])
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
        return respuesta_carrito(cambiar_cantidad(request.user, pk, serializer.validated_data["quantity"]))

    def delete(self, request, pk):
        return respuesta_carrito(quitar_del_carrito(request.user, pk))


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
        pedido = hacer_checkout(
            request.user, serializer.validated_data["shipping_address"], serializer.validated_data["card_last4"]
        )
        pedido = Pedido.objects.prefetch_related("lines").get(pk=pedido.pk)
        return Response(PedidoSerializer(pedido).data, status=status.HTTP_201_CREATED)
