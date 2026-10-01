from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from devconfsite.catalogo.serializers import OpcionElegidaSerializer, ProductoSerializer
from devconfsite.comun import DineroField, SerializerBase

from .models import Carrito, ItemCarrito, LineaPedido, Pedido


@extend_schema_field(OpcionElegidaSerializer(many=True))
class OpcionesElegidasField(serializers.JSONField):
    pass


class ItemCarritoSerializer(SerializerBase):
    price = DineroField()
    options = OpcionesElegidasField()
    variant_id = serializers.IntegerField(read_only=True, allow_null=True)
    stock = serializers.SerializerMethodField()

    class Meta:
        model = ItemCarrito
        fields = ["id", "slug", "name", "price", "image", "options", "quantity", "variant_id", "stock"]

    def get_stock(self, item) -> int:
        return item.variant.stock if item.variant_id else item.product.stock


class CarritoSerializer(SerializerBase):
    items = ItemCarritoSerializer(many=True)
    subtotal = DineroField()
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=4, coerce_to_string=False)
    tax = DineroField()
    total = DineroField()

    class Meta:
        model = Carrito
        fields = ["items", "subtotal", "tax_rate", "tax", "total"]


class AgregarItemSerializer(serializers.Serializer):
    slug = serializers.CharField()
    options = OpcionesElegidasField(required=False, default=list)


class CambiarCantidadSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        min_value=0,
        error_messages={"min_value": "Enter a quantity of 0 or more.", "invalid": "Enter a whole number."},
    )


class DireccionSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=200, error_messages={"blank": "Enter your shipping address.", "required": "Enter your shipping address."})
    city = serializers.CharField(max_length=100, error_messages={"blank": "Enter your city.", "required": "Enter your city."})
    postal_code = serializers.CharField(max_length=20, error_messages={"blank": "Enter your postal code.", "required": "Enter your postal code."})
    country = serializers.CharField(max_length=100, error_messages={"blank": "Enter your country.", "required": "Enter your country."})


class CheckoutSerializer(serializers.Serializer):
    shipping_address = DireccionSerializer()
    card_last4 = serializers.RegexField(
        r"^\d{4}$",
        error_messages={"invalid": "Send the last 4 digits of the card.", "required": "Send the last 4 digits of the card."},
    )


class LineaPedidoSerializer(SerializerBase):
    product_id = serializers.IntegerField(read_only=True, allow_null=True)
    variant_id = serializers.IntegerField(read_only=True, allow_null=True)
    price = DineroField()
    options = OpcionesElegidasField()

    class Meta:
        model = LineaPedido
        fields = ["product_id", "variant_id", "slug", "name", "category", "image", "price", "quantity", "options"]


@extend_schema_field(DireccionSerializer)
class DireccionField(serializers.JSONField):
    pass


class PedidoSerializer(SerializerBase):
    customer_id = serializers.IntegerField(read_only=True, allow_null=True)
    lines = LineaPedidoSerializer(many=True, read_only=True)
    subtotal = DineroField(read_only=True)
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=4, coerce_to_string=False, read_only=True)
    tax = DineroField(read_only=True)
    total = DineroField(read_only=True)
    shipping_address = DireccionField(read_only=True)

    class Meta:
        model = Pedido
        fields = [
            "id", "number", "customer_id", "customer_name", "customer_email", "lines", "subtotal", "tax_rate",
            "tax", "total", "status", "shipping_address", "card_last4", "created_at", "updated_at",
        ]
        read_only_fields = fields


class PedidoAdminSerializer(PedidoSerializer):
    units = serializers.SerializerMethodField()

    class Meta(PedidoSerializer.Meta):
        fields = PedidoSerializer.Meta.fields[:-2] + ["units", "created_at", "updated_at"]
        read_only_fields = fields

    def get_units(self, pedido) -> int:
        total = getattr(pedido, "units_total", None)
        return total if total is not None else pedido.units


class CambiarEstadoSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Pedido.Status.choices)


class ResumenSerializer(serializers.Serializer):
    revenue = DineroField()
    orders = serializers.IntegerField()
    avg_order = DineroField()


class ConteoEstadosSerializer(serializers.Serializer):
    all = serializers.IntegerField()
    paid = serializers.IntegerField()
    shipped = serializers.IntegerField()
    delivered = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    refunded = serializers.IntegerField()


class ListaPedidosAdminSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    summary = ResumenSerializer()
    status_counts = ConteoEstadosSerializer()
    results = PedidoAdminSerializer(many=True)


class VariacionSerializer(serializers.Serializer):
    pct = serializers.FloatField(allow_null=True)


class PuntoSerieSerializer(serializers.Serializer):
    date = serializers.CharField()
    revenue = DineroField()
    orders = serializers.IntegerField()


class EstadoConteoSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()


class CategoriaVentasSerializer(serializers.Serializer):
    category = serializers.CharField()
    revenue = DineroField()
    units = serializers.IntegerField()


class TopProductoSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    image = serializers.CharField()
    units = serializers.IntegerField()
    revenue = DineroField()


class CatalogoConteoSerializer(serializers.Serializer):
    live = serializers.IntegerField()
    disabled = serializers.IntegerField()
    sold_out = serializers.IntegerField()


class TotalesSerializer(serializers.Serializer):
    customers = serializers.IntegerField()
    blocked = serializers.IntegerField()
    orders = serializers.IntegerField()


class DashboardSerializer(serializers.Serializer):
    days = serializers.IntegerField()
    revenue = DineroField()
    orders = serializers.IntegerField()
    avg_order = DineroField()
    new_customers = serializers.IntegerField()
    revenue_delta = VariacionSerializer()
    orders_delta = VariacionSerializer()
    avg_order_delta = VariacionSerializer()
    customers_delta = VariacionSerializer()
    series = PuntoSerieSerializer(many=True)
    by_status = EstadoConteoSerializer(many=True)
    by_category = CategoriaVentasSerializer(many=True)
    top_products = TopProductoSerializer(many=True)
    low_stock = ProductoSerializer(many=True)
    catalog = CatalogoConteoSerializer()
    totals = TotalesSerializer()
    recent = PedidoAdminSerializer(many=True)
