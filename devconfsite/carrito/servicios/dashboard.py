from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, ExpressionWrapper, F, Max, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from devconfsite.catalogo.models import Producto
from devconfsite.usuarios.models import Usuario

from ..models import LineaPedido, Pedido, redondear
from .pedidos import DINERO, conteo_por_estado, resumen_pedidos

LOW_STOCK = 5


def variacion(actual, anterior):
    if not anterior:
        return {"pct": None}
    return {"pct": round(float((Decimal(actual) - Decimal(anterior)) / Decimal(anterior)), 4)}


def construir_dashboard(dias):
    zona = timezone.get_current_timezone()
    hoy = timezone.localdate()
    primer_dia = hoy - timedelta(days=dias - 1)
    inicio = timezone.make_aware(datetime.combine(primer_dia, time.min), zona)
    fin = timezone.make_aware(datetime.combine(hoy + timedelta(days=1), time.min), zona)
    inicio_anterior = inicio - timedelta(days=dias)

    periodo = Pedido.objects.filter(created_at__gte=inicio, created_at__lt=fin)
    anterior = Pedido.objects.filter(created_at__gte=inicio_anterior, created_at__lt=inicio)
    actual_resumen = resumen_pedidos(periodo)
    anterior_resumen = resumen_pedidos(anterior)
    clientes = Usuario.objects.filter(role=Usuario.Role.CLIENTE)
    nuevos = clientes.filter(created_at__gte=inicio, created_at__lt=fin).count()
    nuevos_antes = clientes.filter(created_at__gte=inicio_anterior, created_at__lt=inicio).count()

    ingresos = Q(status__in=Pedido.REVENUE_STATUSES)
    por_dia = {
        fila["dia"]: fila
        for fila in periodo.annotate(dia=TruncDate("created_at", tzinfo=zona))
        .values("dia")
        .annotate(revenue=Coalesce(Sum("total", filter=ingresos), Value(0), output_field=DINERO), orders=Count("id"))
    }
    serie = []
    for n in range(dias):
        dia = primer_dia + timedelta(days=n)
        fila = por_dia.get(dia, {"revenue": Decimal("0"), "orders": 0})
        serie.append({"date": dia.isoformat(), "revenue": redondear(fila["revenue"]), "orders": fila["orders"]})

    estados = conteo_por_estado(periodo)
    lineas = LineaPedido.objects.filter(order__in=periodo.filter(ingresos))
    importe = ExpressionWrapper(F("price") * F("quantity"), output_field=DINERO)
    por_categoria = [
        {"category": fila["category"], "revenue": redondear(fila["revenue"]), "units": fila["units"]}
        for fila in lineas.values("category").annotate(revenue=Sum(importe), units=Sum("quantity")).order_by("-revenue", "category")
    ]
    top = [
        {"slug": fila["slug"], "name": fila["nombre"], "image": fila["imagen"], "units": fila["units"], "revenue": redondear(fila["revenue"])}
        for fila in lineas.values("slug")
        .annotate(nombre=Max("name"), imagen=Max("image"), units=Sum("quantity"), revenue=Sum(importe))
        .order_by("-revenue", "slug")[:5]
    ]

    productos = Producto.objects.all()
    return {
        "days": dias,
        "revenue": actual_resumen["revenue"],
        "orders": actual_resumen["orders"],
        "avg_order": actual_resumen["avg_order"],
        "new_customers": nuevos,
        "revenue_delta": variacion(actual_resumen["revenue"], anterior_resumen["revenue"]),
        "orders_delta": variacion(actual_resumen["orders"], anterior_resumen["orders"]),
        "avg_order_delta": variacion(actual_resumen["avg_order"], anterior_resumen["avg_order"]),
        "customers_delta": variacion(nuevos, nuevos_antes),
        "series": serie,
        "by_status": [{"status": estado, "count": estados[estado]} for estado in Pedido.Status.values],
        "by_category": por_categoria,
        "top_products": top,
        "low_stock": productos.filter(status=Producto.Status.LIVE, stock__lte=LOW_STOCK).select_related("category").prefetch_related("variants").order_by("stock", "id"),
        "catalog": {
            "live": productos.filter(status=Producto.Status.LIVE).count(),
            "disabled": productos.filter(status=Producto.Status.DISABLED).count(),
            "sold_out": productos.filter(stock=0).count(),
        },
        "totals": {
            "customers": clientes.count(),
            "blocked": clientes.filter(status=Usuario.Status.BLOCKED).count(),
            "orders": Pedido.objects.count(),
        },
        "recent": Pedido.objects.prefetch_related("lines").order_by("-created_at", "-id")[:6],
    }
