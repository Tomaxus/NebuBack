from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce, Greatest
from rest_framework.exceptions import PermissionDenied

from devconfsite.catalogo.models import Producto, Variante, clave_variante
from devconfsite.comun.excepciones import ReglaDeNegocio

from ..models import Carrito, LineaPedido, Pedido, calcular_impuesto, redondear
from .carrito import variante_de

DINERO = DecimalField(max_digits=14, decimal_places=2)


@transaction.atomic
def hacer_checkout(usuario, direccion, ultimos4):
    if usuario.is_blocked:
        raise PermissionDenied("This account can't place orders. Contact support.")
    carrito = Carrito.objects.select_for_update().filter(user=usuario, status=Carrito.Status.ACTIVE).first()
    items = list(carrito.items.select_related("product__category").order_by("id")) if carrito else []
    if not items:
        raise ReglaDeNegocio("Your bag is empty.")

    productos = {
        p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=[i.product_id for i in items])
    }
    con_variantes = set(
        Variante.objects.filter(product_id__in=productos).values_list("product_id", flat=True).distinct()
    )
    variantes = {
        (v.product_id, v.options_key): v
        for v in Variante.objects.select_for_update().filter(product_id__in=con_variantes)
    }
    variante_de_item = {}
    no_disponibles = []
    for item in items:
        if productos[item.product_id].status != Producto.Status.LIVE:
            no_disponibles.append(str(item.pk))
        elif item.product_id in con_variantes:
            variante = variantes.get((item.product_id, clave_variante(item.options)))
            if variante is None:
                no_disponibles.append(str(item.pk))
            variante_de_item[item.pk] = variante
    if no_disponibles:
        raise ReglaDeNegocio({"detail": "Some items are no longer available.", "items": no_disponibles})
    origen = {}
    for item in items:
        variante = variante_de_item.get(item.pk)
        origen[item.pk] = (("v", variante.pk), variante.stock) if variante else (("p", item.product_id), productos[item.product_id].stock)
    pedidas = {}
    for item in items:
        clave = origen[item.pk][0]
        pedidas[clave] = pedidas.get(clave, 0) + item.quantity
    sin_stock = [str(i.pk) for i in items if pedidas[origen[i.pk][0]] > origen[i.pk][1]]
    if sin_stock:
        raise ReglaDeNegocio({"detail": "Some items don't have enough stock.", "items": sin_stock})

    subtotal = redondear(sum((i.price * i.quantity for i in items), start=Decimal("0")))
    tasa = settings.IMPUESTO_TASA
    impuesto = calcular_impuesto(subtotal, tasa)
    pedido = Pedido.objects.create(
        cart=carrito,
        customer=usuario,
        customer_name=usuario.name,
        customer_email=usuario.email,
        subtotal=subtotal,
        tax_rate=tasa,
        tax=impuesto,
        total=redondear(subtotal + impuesto),
        status=Pedido.Status.PAID,
        shipping_address=direccion,
        card_last4=ultimos4,
    )
    LineaPedido.objects.bulk_create(
        LineaPedido(
            order=pedido,
            product=item.product,
            variant=variante_de_item.get(item.pk),
            slug=item.slug,
            name=item.name,
            category=item.product.category.name,
            image=item.image,
            price=item.price,
            quantity=item.quantity,
            options=item.options,
        )
        for item in items
    )
    for (tipo, clave), cantidad in pedidas.items():
        modelo = Variante if tipo == "v" else Producto
        modelo.objects.filter(pk=clave).update(stock=F("stock") - cantidad)
    for producto_id in con_variantes:
        productos[producto_id].recalcular_desde_variantes()
    carrito.status = Carrito.Status.CONVERTED
    carrito.save(update_fields=["status"])
    return pedido


@transaction.atomic
def cambiar_estado_pedido(pedido, nuevo_estado):
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    antes_repone = pedido.status in Pedido.RESTOCK_STATUSES
    despues_repone = nuevo_estado in Pedido.RESTOCK_STATUSES
    if antes_repone != despues_repone:
        recalcular = set()
        for linea in pedido.lines.exclude(product=None).select_related("product"):
            if despues_repone:
                cambio = F("stock") + linea.quantity
            else:
                cambio = Greatest(F("stock") - linea.quantity, Value(0))
            variante_id = linea.variant_id
            if variante_id is None and linea.product.variants.exists():
                variante = variante_de(linea.product, linea.options)
                variante_id = variante.pk if variante else None
            if variante_id is not None:
                Variante.objects.filter(pk=variante_id).update(stock=cambio)
                recalcular.add(linea.product)
            elif not linea.product.variants.exists():
                Producto.objects.filter(pk=linea.product_id).update(stock=cambio)
        for producto in recalcular:
            producto.recalcular_desde_variantes()
    pedido.status = nuevo_estado
    pedido.save(update_fields=["status", "updated_at"])
    return pedido


def resumen_pedidos(pedidos):
    ingresos = Q(status__in=Pedido.REVENUE_STATUSES)
    datos = pedidos.aggregate(
        revenue=Coalesce(Sum("total", filter=ingresos), Value(0), output_field=DINERO),
        orders=Count("id"),
        revenue_orders=Count("id", filter=ingresos),
    )
    promedio = redondear(datos["revenue"] / datos["revenue_orders"]) if datos["revenue_orders"] else Decimal("0")
    return {"revenue": redondear(datos["revenue"]), "orders": datos["orders"], "avg_order": promedio}


def conteo_por_estado(pedidos):
    conteos = dict(pedidos.values_list("status").annotate(n=Count("id")))
    resultado = {"all": sum(conteos.values())}
    for estado in Pedido.Status.values:
        resultado[estado] = conteos.get(estado, 0)
    return resultado
