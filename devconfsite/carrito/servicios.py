from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Max, Q, Sum, Value
from django.db.models.functions import Coalesce, Greatest, TruncDate
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.serializers import ValidationError

from devconfsite.catalogo.models import Producto, Variante, clave_variante
from devconfsite.comun import ReglaDeNegocio
from devconfsite.usuarios.models import Usuario

from .models import Carrito, ItemCarrito, LineaPedido, Pedido, calcular_impuesto, redondear

DINERO = DecimalField(max_digits=14, decimal_places=2)
LOW_STOCK = 5


def mensaje_stock(stock):
    return "This product is sold out." if stock == 0 else f"Only {stock} left in stock."


def carrito_activo(usuario):
    try:
        with transaction.atomic():
            carrito, _ = Carrito.objects.get_or_create(user=usuario, status=Carrito.Status.ACTIVE)
    except IntegrityError:
        carrito = Carrito.objects.get(user=usuario, status=Carrito.Status.ACTIVE)
    return carrito


def normalizar_opciones(producto, elegidas):
    mensaje = "Choose a valid value for every attribute of this product."
    if not isinstance(elegidas, list):
        raise ValidationError({"options": [mensaje]})
    por_nombre = {}
    for opcion in elegidas:
        if not isinstance(opcion, dict) or not isinstance(opcion.get("name"), str) or not isinstance(opcion.get("value"), str):
            raise ValidationError({"options": [mensaje]})
        if opcion["name"] in por_nombre:
            raise ValidationError({"options": [mensaje]})
        por_nombre[opcion["name"]] = opcion["value"]
    nombres_producto = [opcion["name"] for opcion in producto.options]
    if set(por_nombre) != set(nombres_producto):
        raise ValidationError({"options": [mensaje]})
    normalizadas = []
    for opcion in producto.options:
        valor = por_nombre[opcion["name"]]
        if valor not in opcion["values"]:
            raise ValidationError({"options": [mensaje]})
        normalizadas.append({"name": opcion["name"], "value": valor})
    return normalizadas


def variante_de(producto, opciones, bloquear=False):
    variantes = Variante.objects.filter(product=producto, options_key=clave_variante(opciones))
    if bloquear:
        variantes = variantes.select_for_update()
    return variantes.first()


@transaction.atomic
def agregar_al_carrito(usuario, slug, opciones):
    producto = Producto.objects.select_for_update().filter(slug=slug, status=Producto.Status.LIVE).first()
    if producto is None:
        raise ValidationError({"slug": ["This product is not available."]})
    opciones = normalizar_opciones(producto, opciones)
    variante = None
    if producto.variants.exists():
        variante = variante_de(producto, opciones, bloquear=True)
        if variante is None:
            raise ReglaDeNegocio("That combination is not available.")
        if variante.stock <= 0:
            raise ReglaDeNegocio("Sold out.")
    carrito = carrito_activo(usuario)
    item = ItemCarrito.objects.filter(cart=carrito, product=producto, options=opciones).first()
    nueva_cantidad = (item.quantity if item else 0) + 1
    if variante is not None:
        if nueva_cantidad > variante.stock:
            raise ReglaDeNegocio(f"Only {variante.stock} left in stock.")
    elif nueva_cantidad > producto.stock:
        raise ValidationError({"quantity": [mensaje_stock(producto.stock)]})
    if item:
        item.quantity = nueva_cantidad
        item.variant = variante
        item.save(update_fields=["quantity", "variant"])
    else:
        ItemCarrito.objects.create(
            cart=carrito,
            product=producto,
            variant=variante,
            slug=producto.slug,
            name=producto.name,
            price=variante.price if variante else producto.price,
            image=producto.image,
            options=opciones,
            quantity=1,
        )
    return carrito


def stock_de_linea(item):
    if item.variant_id is not None:
        return item.variant.stock
    if item.product.variants.exists():
        variante = variante_de(item.product, item.options)
        return variante.stock if variante else 0
    return item.product.stock


def item_del_usuario(usuario, item_id):
    item = (
        ItemCarrito.objects.select_related("product", "variant", "cart")
        .filter(pk=item_id, cart__user=usuario, cart__status=Carrito.Status.ACTIVE)
        .first()
    )
    if item is None:
        raise NotFound()
    return item


@transaction.atomic
def cambiar_cantidad(usuario, item_id, cantidad):
    item = item_del_usuario(usuario, item_id)
    if cantidad == 0:
        item.delete()
        return item.cart
    disponible = stock_de_linea(item)
    if cantidad > disponible:
        raise ValidationError({"quantity": [mensaje_stock(disponible)]})
    item.quantity = cantidad
    item.save(update_fields=["quantity"])
    return item.cart


@transaction.atomic
def quitar_del_carrito(usuario, item_id):
    item = item_del_usuario(usuario, item_id)
    item.delete()
    return item.cart


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
