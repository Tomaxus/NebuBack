from rest_framework import serializers

from devconfsite.catalogo.serializers import ProductoSerializer
from devconfsite.comun.campos import DineroField

from ..models import Pedido
from .tienda import PedidoSerializer


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
